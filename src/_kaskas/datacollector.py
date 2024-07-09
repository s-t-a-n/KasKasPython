import time
from datetime import datetime
import numpy as np
import os
import csv
from typing import Optional
from pathlib import Path
from enum import Enum
import pandas as pd  # read csv, df manipulation
import errno
from multiprocessing.synchronize import Lock as LockType
from multiprocessing import Lock

from _jasjas.jasjas_api import JasJasGrowbed
from _jasjas.datalink.serial import open_next_available_serial

#########################################

# ########################################


# def epoch(dt64) -> int:
#     return dt64.astype("datetime64[s]").astype("int")


# epoch_start = epoch(np.datetime64("now"))

""" Find available serial ports """

sampling_interval = 10


def is_float(string: str) -> bool:
    return string.replace(".", "").isnumeric()


def collect_to(metrics: list[str], csv_writer) -> None:
    if len(metrics) > 0 and all([is_float(s) for s in metrics]):
        csv_writer.writerow([datetime.now()] + metrics)
        print(f"{datetime.now()}: {metrics}")
    else:
        print(f"Invalid row: {metrics}")


def do_datacollection(
        growbed: JasJasGrowbed, output_fname: Path, sampling_interval: int
):
    with open(output_filename, "a+", newline="") as file:

        print("loading csv file")
        writer = csv.writer(file)

        # serial_request("MTC!stopDatadump\r")

        # if not api.request(module="MTC", function="setDatadumpIntervalS", arguments=[f"{sampling_interval}"]):
        #     print("failed to set datadump interval")
        #     return

        # if not api.request(module="MTC", function="startDatadump"):
        #     print("failed to start datadump")
        #     return

        print("setting up datacollection")
        fields_response = growbed.request(module="MTC", function="getFields")
        if not fields_response or not all(
                [
                    str.isalpha(s) and str.isupper(s)
                    for s in [s.replace("_", "") for s in fields_response.arguments]
                ]
        ):
            print("failed to read fields")
            return

        if os.stat(output_filename).st_size == 0:
            # this is the first line in a new file; write headers
            fields = ["TIMESTAMP"] + fields_response.arguments
            print(f"writing fields to new file: {fields}")
            writer.writerow(fields)
        else:
            # this file contains data
            df = pd.read_csv(output_fname, low_memory=True)
            existing_columns = set(df.columns)
            incoming_columns = set(["TIMESTAMP"] + fields_response.arguments)
            if incoming_columns != existing_columns:
                print(f"{output_fname} has columns {existing_columns}")
                print(f"api provides the following fields {incoming_columns}")
                print("the existing and incoming columns do no match")
                return

        print("starting datacollection loop")
        while metrics_response := growbed.request(module="MTC", function="getMetrics"):
            # print("hello?")
            collect_to(metrics_response.arguments, writer)
            file.flush()
            print(f"sleeping for  {sampling_interval}s")
            time.sleep(sampling_interval)
    print("datacollection came to a halt")


class MetricCollector:
    """_summary_"""

    def __init__(self) -> None:
        pass

# from pizco import Server
#
# address = "tcp://127.0.0.1:8000"
# # api = JasJasAPI(ser)
# # server = Server(api, address)
# api_proxy = Server.serve_in_process(
#     JasJasGrowbed, (), {"io": open_next_available_serial()}, address
# )  # ,verbose=args.verbose, gui=args.gui
#
# output_filename = Path("/mnt/USB/jasjas_data.csv")
#
# while True:
#     do_datacollection(api, output_filename, sampling_interval)
#     time.sleep(5)
