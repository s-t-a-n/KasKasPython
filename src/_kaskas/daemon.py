from typing import *
from pathlib import Path
import Pyro5.api
import Pyro5.nameserver

from _kaskas.streamlit_launcher import StreamlitLauncher
from _kaskas.datacollector import TimeSeriesCollector
from _kaskas.kaskas_api import KasKasAPI
from _kaskas.pyro_server import PyroServer
from _kaskas.datalink_serial import Datalink as DatalinkSerial


class Daemon:
    """ Daemon who serves to run the various KasKas components """

    _root_dir: Path

    _pyro_server: PyroServer

    _api_address: str
    _datalink: Optional[DatalinkSerial] = None
    _webapp: Optional[StreamlitLauncher] = None
    _collector: Optional[TimeSeriesCollector] = None

    def __init__(self, root: Path) -> None:
        self._root_dir = root
        self._pyro_server = PyroServer()

    def launch_api(self, remote: bool = False, remote_host: Optional[str] = None) -> None:

        if not remote:
            if not self._pyro_server.is_started:
                self._pyro_server.start()
            self._datalink = DatalinkSerial(root=self._root_dir)
            self._pyro_server.serve_object(KasKasAPI(datalink=self._datalink), KasKasAPI.cannonical_name())

        self._api_address = f"PYRONAME:{KasKasAPI.cannonical_name()}"

        if remote_host:
            self._api_address += f"@{remote_host}"

    def launch_webapp(self):
        self._webapp = StreamlitLauncher(root=self._root_dir, api=self.api)
        self._webapp.start()

    def launch_collector(self, sampling_interval: int = 10):
        self._collector = TimeSeriesCollector(root=self._root_dir, api=self.api, sampling_interval=sampling_interval)
        self._collector.start()

    def wait(self) -> None:
        # self._pyro_server.wait()
        if self._datalink:
            self._datalink.wait()
        if self._collector:
            self._collector.wait()
        if self._webapp:
            self._webapp.wait()

    def shutdown(self, wait: bool = True) -> None:
        if self._datalink:
            self._datalink.stop()
        if self._webapp:
            self._webapp.stop()
        if self._collector:
            self._collector.stop()
        if wait:
            self.wait()
        self._pyro_server.stop(blocking=wait)

    @property
    def api(self) -> KasKasAPI | Pyro5.api.Proxy:
        assert self._pyro_server, "Pyro server is not initialized"
        assert self._api_address, "Api is not initialized"
        return self._pyro_server.proxy_for(self._api_address)

    @property
    def root_dir(self) -> Path:
        return self._root_dir
