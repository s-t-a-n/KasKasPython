import streamlit as st
import streamlit_authenticator as stauth
import numpy as np
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import cv2
from pathlib import Path
import typer
import yaml
from yaml.loader import SafeLoader
from typing import Optional
from _kaskas.pyro_server import PyroServer
from _kaskas.utils.filelock import FileLock
from _kaskas.datacollector import TimeSeriesCollector

st.set_page_config(page_title="KasKas !", page_icon="🌱", layout="wide")

# Initialize session state for authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def show_login_form(auth_file: Path):
    """Display the login form and handle authentication."""
    try:
        with open(auth_file, "r") as f:
            auth_config = yaml.load(f, Loader=SafeLoader)
        authenticator = stauth.Authenticate(
            auth_config["credentials"],
            auth_config["cookie"]["name"],
            auth_config["cookie"]["key"],
            auth_config["cookie"]["expiry_days"],
            auth_config["pre-authorized"],
        )

        if not st.session_state["authentication_status"]:
            Logger.debug("Authenticating to Streamlit...")
            name, authentication_status, username = authenticator.login()
        else:
            Logger.debug("User was already authenticated")
    except Exception as e:
        st.error(f"Error reading authentication file: {e}")


class Logger:
    def __init__(self):
        pass

    @staticmethod
    def critical(msg):
        print(f"CRITICAL:{msg}")

    @staticmethod
    def debug(msg):
        print(f"DEBUG:{msg}")

    @staticmethod
    def info(msg):
        print(f"INFO:{msg}")

    @staticmethod
    def warning(msg):
        print(f"WARNING:{msg}")


class Camera:
    def capture_array(self) -> np.ndarray:
        mock_frame = np.empty((1920, 1080))
        mock_frame.fill(5)
        return mock_frame

    def started(self) -> bool:
        return False


@st.cache_resource
def get_camera() -> Camera:
    return Camera()


@st.cache_resource(ttl=timedelta(seconds=10))
def get_next_frame() -> np.ndarray:
    next_frame = get_camera().capture_array()
    date_time = str(datetime.now())
    font = cv2.FONT_HERSHEY_SIMPLEX
    x = next_frame.shape[1]
    y = next_frame.shape[0]
    origin = (x - len(date_time) * 10, 20)
    fontscale = 0.5
    color_bgr = (0, 51, 153)
    thickness = 1
    next_frame = cv2.putText(
        next_frame, date_time, origin, font, fontscale, color_bgr, thickness, cv2.LINE_4
    )
    return next_frame


@st.cache_resource(ttl=timedelta(seconds=1))
def get_next_dataframe(csv_path: Path, csv_lock_path: Path) -> pd.DataFrame:
    lock = FileLock(csv_lock_path)
    with lock:
        return pd.read_csv(csv_path, low_memory=True)


def filter_data(df: pd.DataFrame, hours: int) -> pd.DataFrame:
    """Filter the DataFrame based on the number of hours."""
    if hours == 'all':
        return df
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    return df[df["TIMESTAMP"] >= start_time.strftime("%Y-%m-%d %H:%M:%S.%f")]


def display_kpi(title: str, current_value: float, avg_value: float, y_data: list, df: pd.DataFrame, ylabel: str,
                panel_id: str, time_range: str):
    """Display a KPI panel with a title, current reading, and a graph."""
    with st.container(border=True):
        # KPI display
        st.markdown(f"### {title}")
        kpi_col1, kpi_col2 = st.columns([1, 3])
        with kpi_col1:
            st.metric(label=title, value=round(current_value, 2), delta=round(current_value - avg_value, 2))

        hours_map = {
            "All Data": 'all',
            "Last 24 Hours": 24,
            "Last 6 Hours": 6,
            "Last 1 Hour": 1
        }

        hours = hours_map[time_range]
        filtered_df = filter_data(df, hours)

        try:
            fig = px.line(data_frame=filtered_df, y=y_data, x="TIMESTAMP", labels={"TIMESTAMP": "Time", ylabel: ylabel})
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            Logger.debug(f"Error creating plot: {e}")
            st.error("Failed to create plot.")


def load_page(root: Path, api: PyroServer | PyroServer.Proxy):
    """Load and display the main page with real-time updates."""
    placeholder = st.empty()

    # Fetch the dataframe once for the whole page
    df_lock_path = root / TimeSeriesCollector.timeseries_lock_filename
    df = get_next_dataframe(root / TimeSeriesCollector.timeseries_filename, df_lock_path)

    if df.empty:
        st.warning("No data available.")
        return

    # Create sidebar with time range selector
    st.sidebar.header("Time Range Selector")
    time_range = st.sidebar.radio(
        "Select time range:",
        ["All Data", "Last 24 Hours", "Last 6 Hours", "Last 1 Hour"],
        key="time_range_selector"
    )

    # Calculate KPIs
    element_surface_temp = np.mean(df["HEATING_SURFACE_TEMP"].iloc[-2:])
    avg_element_surface_temp = np.mean(df["HEATING_SURFACE_TEMP"].iloc[-20:])

    climate_temp = np.mean(df["CLIMATE_TEMP"].iloc[-2:])
    avg_climate_temp = np.mean(df["CLIMATE_TEMP"].iloc[-20:])

    climate_humidity = np.mean(df["CLIMATE_HUMIDITY"].iloc[-2:])
    avg_climate_humidity = np.mean(df["CLIMATE_HUMIDITY"].iloc[-20:])

    soil_moisture = np.mean(df["SOIL_MOISTURE"].iloc[-2:])
    avg_soil_moisture = np.mean(df["SOIL_MOISTURE"].iloc[-20:])

    fluid_injected = np.mean(df["FLUID_INJECTED"].iloc[-2:])
    avg_fluid_injected = np.mean(df["FLUID_INJECTED"].iloc[-20:])

    cumulative_fluid_injected = np.mean(df["FLUID_INJECTED_CUMULATIVE"].iloc[-2:])
    avg_cumulative_fluid_injected = np.mean(df["FLUID_INJECTED_CUMULATIVE"].iloc[-20:])

    with placeholder.container():
        time_since_last_sample = datetime.now() - datetime.strptime(df["TIMESTAMP"].iloc[-1], "%Y-%m-%d %H:%M:%S.%f")
        if time_since_last_sample.total_seconds() > 60:
            st.warning("Datacollection failure. You are watching outdated data.")

        left_image, webcam_col, water_panel = st.columns(3)
        with webcam_col:
            if get_camera().started():
                last_frame = get_next_frame()
                st.image(last_frame, caption="Livefeed")
            else:
                st.warning("Camera not started or malfunctioning.")
        with left_image:
            st.image(str(root / "Nietzsche_metPistool.jpg"), width=420, caption="Nature or notsure")
        with water_panel:
            pass  # Water panel code can go here

        # Create tabs for different panels
        tab_labels = ["Element Surface Temperature", "Climate Temperature", "Climate Humidity", "Soil Moisture",
                      "Fluids"]
        tabs = st.tabs(tab_labels)

        # Display content based on selected tab
        with tabs[0]:
            display_kpi(
                title="Element Surface Temperature",
                current_value=element_surface_temp,
                avg_value=avg_element_surface_temp,
                y_data=["HEATING_SURFACE_TEMP"],
                df=df,
                ylabel="Element Surface Temperature",
                panel_id="element_surface_temp",
                time_range=time_range
            )
        with tabs[1]:
            display_kpi(
                title="Climate Temperature",
                current_value=climate_temp,
                avg_value=avg_climate_temp,
                y_data=["CLIMATE_TEMP", "HEATING_SETPOINT", "AMBIENT_TEMP"],
                df=df,
                ylabel="Climate Temperature",
                panel_id="climate_temp",
                time_range=time_range
            )
        with tabs[2]:
            display_kpi(
                title="Climate Humidity",
                current_value=climate_humidity,
                avg_value=avg_climate_humidity,
                y_data=["CLIMATE_HUMIDITY", "CLIMATE_FAN", "CLIMATE_HUMIDITY_SETPOINT"],
                df=df,
                ylabel="Climate Humidity",
                panel_id="climate_humidity",
                time_range=time_range
            )
        with tabs[3]:
            display_kpi(
                title="Soil Moisture",
                current_value=soil_moisture,
                avg_value=avg_soil_moisture,
                y_data=["SOIL_MOISTURE", "SOIL_MOISTURE_SETPOINT"],
                df=df,
                ylabel="Soil Moisture",
                panel_id="soil_moisture",
                time_range=time_range
            )
        with tabs[4]:
            display_kpi(
                title="Fluids",
                current_value=fluid_injected,
                avg_value=avg_fluid_injected,
                y_data=["FLUID_INJECTED", "FLUID_INJECTED_CUMULATIVE", "FLUID_EFFECT"],
                df=df,
                ylabel="Fluid injected",
                panel_id="fluids",
                time_range=time_range
            )

        # Detailed data view at the bottom
        with st.expander("Detailed Data View", expanded=False):
            st.dataframe(df, use_container_width=True)


def do_streamlit_session(root: Path, api_id: str):
    """Run the Streamlit session."""

    Logger.debug("Client connected")

    auth_file: Optional[Path] = root / "auth.yml" if (root / "auth.yml").exists() else None

    if auth_file:
        Logger.debug(f"Loading authorization file {auth_file}")

        show_login_form(auth_file)

        if st.session_state["authentication_status"]:
            Logger.debug("Session authenticated.")
            api = PyroServer.proxy_for(f"PYRONAME:{api_id}")
            load_page(root, api)
    else:
        # Initialize API with provided api_id
        Logger.debug("No authentication: no authorization file was provided.")
        api = PyroServer.proxy_for(f"PYRONAME:{api_id}")
        load_page(root, api)


if __name__ == "__main__":
    typer.run(do_streamlit_session)
