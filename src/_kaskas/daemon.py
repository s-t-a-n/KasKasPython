from typing import *
from pathlib import Path

from _kaskas.streamlit_launcher import StreamlitLauncher
from _kaskas.datacollector import MetricCollector
from _kaskas.kaskas_api import KasKasAPI
from _kaskas.pyro_server import PyroServer

import Pyro5.api
import Pyro5.nameserver


# import logging
#
# logging.basicConfig()  # or your own sophisticated setup
# logging.getLogger("Pyro5").setLevel(logging.DEBUG)
# logging.getLogger("Pyro5.core").setLevel(logging.DEBUG)


# @Pyro5.expose
# @Pyro5.behavior(instance_mode="single")
class Daemon:
    """ Daemon who serves to run the various KasKas components """

    _root_dir: Path

    _pyro_server: PyroServer

    # _api: Optional[Pyro5.api.Proxy] = None
    _api_address: str
    _webapp: Optional[StreamlitLauncher]
    _collector: Optional[MetricCollector]

    def __init__(self, root: Path) -> None:
        self._root_dir = root
        self._pyro_server = PyroServer()

    def launch_api(self, remote: bool = False, remote_host: Optional[str] = None) -> None:

        if not remote:
            if not self._pyro_server.is_started:
                self._pyro_server.start()
            self._pyro_server.serve_object(KasKasAPI(log_filename=self._root_dir / Path("kaskas.log")),
                                           KasKasAPI.cannonical_name())

        self._api_address = f"PYRONAME:{KasKasAPI.cannonical_name()}"

        if remote_host:
            self._api_address += f"@{remote_host}"
        # self._api = Server.serve_in_process(
        #     KasKasAPI, args=(), kwargs={}, rep_endpoint=f"tcp://127.0.0.1:{api_port}",
        #     gui=False, verbose=True)

    def launch_webapp(self):
        self._webapp = StreamlitLauncher(root=self._root_dir, api=self.api)
        self._webapp.start()

    def launch_collector(self, sampling_interval: int = 10):
        self._collector = MetricCollector(root=self._root_dir, api=self.api, sampling_interval=sampling_interval)
        self._collector.start()

    def wait(self) -> None:
        # self._pyro_server.wait()
        # if self.api:
        #     self.api.wait()
        if self._collector:
            self._collector.wait()
        if self._webapp:
            self._webapp.wait()

    def shutdown(self, wait: bool = True) -> None:
        if self._webapp:
            self._webapp.stop()
        if self._collector:
            self._collector.stop()
        self._pyro_server.stop()
        if wait:
            self.wait()

    @property
    def api(self) -> KasKasAPI | Pyro5.api.Proxy:
        assert self._pyro_server, "Pyro server is not initialized"
        assert self._api_address, "Api is not initialized"
        return self._pyro_server.proxy_for(self._api_address)

    @property
    def root_dir(self) -> Path:
        return self._root_dir
