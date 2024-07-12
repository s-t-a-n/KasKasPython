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

from rich.progress import open as rich_open


class MetricCollector:
    """_summary_"""

    metrics_filename: str = "kaskas_metrics.csv"

    _flag_shutdown: Event
    _flag_up_and_running: Event

    _thread: Thread
    _pyrodaemon: Pyro5.api.Daemon
    _nameserver: Pyro5.nameserver.NameServerDaemon

    _root: Path
    _api: KasKasAPI | Pyro5.api.Proxy

    _output_filepath: Path
    _sampling_interval: int = 10

    def __init__(self, root: Path, api: KasKasAPI | Pyro5.api.Proxy, sampling_interval: int = 10) -> None:
        self._flag_shutdown = Event()
        self._flag_up_and_running = Event()
        self._thread = Thread(target=self._runner)
        self._root = root
        self._sampling_interval = sampling_interval
        self._api = api
        self._output_filepath = self._root / Path(MetricCollector.metrics_filename)

    @property
    def is_started(self) -> bool:
        return self._thread.is_alive()

    @property
    def is_up_and_running(self) -> bool:
        return self._flag_up_and_running.is_set()

    def wait(self):
        self._thread.join()

    def start(self, wait: bool = True) -> None:
        if not self.is_started:
            self._thread.start()
        if wait:
            self._flag_up_and_running.wait()

    def stop(self, blocking: bool = False) -> None:
        self._flag_shutdown.set()
        if blocking:
            self._thread.join()

    def _collect_data(self, output_filename: Path):
        def is_float(string: str) -> bool:
            return string.replace(".", "").isnumeric()

        def collect_to(metrics: list[str], csv_writer) -> None:
            if len(metrics) > 0 and all([is_float(s) for s in metrics]):
                csv_writer.writerow([datetime.now()] + metrics)
                log.info(f"{datetime.now()}: {metrics}")
            else:
                log.error(f"Invalid row: {metrics}")

        with open(output_filename, mode="+a", newline="") as file:
            writer = csv.writer(file)

            log.debug("setting up datacollection")
            fields_response = self._api.request(module="MTC", function="getFields")
            if not fields_response or not all(
                    [
                        str.isalpha(s) and str.isupper(s)
                        for s in [s.replace("_", "") for s in fields_response.arguments]
                    ]
            ):
                log.error("failed to read fields")
                return

            if os.stat(output_filename).st_size == 0:
                # this is the first line in a new file; write headers
                fields = ["TIMESTAMP"] + fields_response.arguments
                log.debug(f"Writing column headers to {output_filename}: {fields}")
                writer.writerow(fields)
            else:
                df = pd.read_csv(output_filename, low_memory=True)
                existing_columns = set(df.columns)
                incoming_columns = set(["TIMESTAMP"] + fields_response.arguments)
                if incoming_columns != existing_columns:
                    log.error(
                        f"Output file {output_filename} has columns {existing_columns}. API provides the following fields {incoming_columns}. The existing and incoming columns do no match")
                    return

            log.debug("starting datacollection loop")
            while metrics_response := self._api.request(module="MTC", function="getMetrics"):
                collect_to(metrics_response.arguments, writer)
                file.flush()
                time.sleep(self._sampling_interval)
        log.debug("datacollection came to a halt")

    def _runner(self):
        self._api._pyroClaimOwnership()  # https://pyro5.readthedocs.io/en/latest/clientcode.html#proxy-sharing-between-threads

        while not self._flag_shutdown.is_set():
            self._flag_up_and_running.set()
            self._collect_data(self._output_filepath)
            time.sleep(5)
