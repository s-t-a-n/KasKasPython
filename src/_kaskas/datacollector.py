from _kaskas.log import log
import time
from datetime import datetime
import os
import csv
from typing import Optional
from pathlib import Path
import pandas as pd  # read csv, df manipulation
import errno
from threading import Thread, Event

import Pyro5.api
import Pyro5.nameserver

from _kaskas.kaskas_api import KasKasAPI
from _kaskas.utils.filelock import FileLock

from rich.progress import open as rich_open


class TimeSeriesCollector:
    """_summary_"""

    timeseries_filename: str = "kaskas_timeseries.csv"
    timeseries_lock_filename: str = timeseries_filename + ".lock"

    _flag_shutdown: Event
    _flag_up_and_running: Event

    _thread: Thread
    _pyrodaemon: Pyro5.api.Daemon
    _nameserver: Pyro5.nameserver.NameServerDaemon

    _root: Path
    _api: KasKasAPI | Pyro5.api.Proxy

    _output_filepath: Path
    _output_lock: FileLock
    _sampling_interval: int = 10

    def __init__(self, root: Path, api: KasKasAPI | Pyro5.api.Proxy, sampling_interval: int = 10) -> None:
        self._flag_shutdown = Event()
        self._flag_up_and_running = Event()
        self._thread = Thread(target=self._runner)
        self._root = root
        self._sampling_interval = sampling_interval
        self._api = api
        self._output_filepath = self._root / Path(TimeSeriesCollector.timeseries_filename)
        self._output_lock = FileLock(self._root / Path(TimeSeriesCollector.timeseries_lock_filename))

    @property
    def is_started(self) -> bool:
        return self._thread.is_alive()

    @property
    def is_up_and_running(self) -> bool:
        return self._flag_up_and_running.is_set()

    def wait(self):
        if self.is_started:
            self._thread.join()

    def start(self, wait: bool = True) -> None:
        if not self.is_started:
            self._thread.start()
        if wait:
            self._flag_up_and_running.wait()

    def stop(self, blocking: bool = False) -> None:
        self._flag_shutdown.set()
        if blocking:
            self.wait()

    def _collect_data(self, output_filename: Path):
        def is_float(string: str) -> bool:
            return string.replace(".", "").isnumeric()

        def collect_to(timeseries: list[str], csv_writer) -> None:
            if len(timeseries) > 0 and all([is_float(s) for s in timeseries]):
                try:
                    with self._output_lock:
                        csv_writer.writerow([datetime.now()] + timeseries)
                except Exception as e:
                    log.warning(f"Failed to write to csv file with error : {e}")
                log.info(f"{datetime.now()}: {timeseries}")
            else:
                log.error(
                    f"Invalid timeseries: {timeseries}, likely because growbed is not ready or a communication failure occured.")

        with open(output_filename, mode="+a", newline="") as file:
            with self._output_lock:
                writer = csv.writer(file)

            log.debug("Setting up timeseries collection")
            columns_response = self._api.request(module="DAQ", command="getTimeSeriesColumns")
            if not columns_response or not all(
                    [
                        str.isalpha(s) and str.isupper(s)
                        for s in [s.replace("_", "") for s in columns_response.arguments]
                    ]
            ):
                log.error("Failed to read timeseries columns from API")
                return

            if os.stat(output_filename).st_size == 0:
                # this is the first line in a new file; write headers
                fields = ["TIMESTAMP"] + columns_response.arguments
                log.debug(f"Writing column headers to {output_filename}: {fields}")
                with self._output_lock:
                    writer.writerow(fields)
            else:
                # the file exists, make sure it's columns match the incoming columns
                with self._output_lock:
                    df = pd.read_csv(output_filename, low_memory=True)
                existing_columns = set(df.columns)
                incoming_columns = set(["TIMESTAMP"] + columns_response.arguments)
                if incoming_columns != existing_columns:
                    log.error(
                        f"Output file {output_filename} has columns {existing_columns}. API provides the following fields {incoming_columns}. The existing and incoming columns do no match")
                    return

            log.debug("Starting timeseries collection loop")
            while timeseries_response := self._api.request(module="DAQ", command="getTimeSeries"):
                collect_to(timeseries_response.arguments, writer)
                file.flush()
                time.sleep(self._sampling_interval)
        log.debug("Timeseries collection came to a halt")

    def _runner(self):
        self._api._pyroClaimOwnership()  # https://pyro5.readthedocs.io/en/latest/clientcode.html#proxy-sharing-between-threads

        while not self._flag_shutdown.is_set():
            self._flag_up_and_running.set()
            self._collect_data(self._output_filepath)
            time.sleep(5)
