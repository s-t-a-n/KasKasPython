from _kaskas.log import log

import os
from threading import Thread, Event

from typing import *
from pathlib import Path

import socket
import Pyro5.socketutil
import Pyro5.api
import Pyro5.nameserver

Pyro5.config.SERVERTYPE = "multiplex"
Pyro5.config.POLLTIMEOUT = 3


# import logging
#
# logging.basicConfig()  # or your own sophisticated setup
# logging.getLogger("Pyro5").setLevel(logging.DEBUG)
# logging.getLogger("Pyro5.core").setLevel(logging.DEBUG)


class PyroServer:
    _flag_shutdown: Event
    _flag_up_and_running: Event

    _thread: Thread
    _pyrodaemon: Pyro5.api.Daemon
    _nameserver: Pyro5.nameserver.NameServerDaemon

    Proxy = Pyro5.api.Proxy

    def __init__(self):
        self._flag_shutdown = Event()
        self._flag_up_and_running = Event()

        self._thread = Thread(target=self._runner)

        hostname = socket.gethostname()
        # print(f"starting Pyro server on {hostname}")
        self._pyrodaemon = Pyro5.api.Daemon(host=hostname)

    def serve_object(self, obj: object, name: str) -> str:
        if not self.is_started:
            self.start()

        server_uri = self._pyrodaemon.register(obj)
        log.debug(f"Serving object {name}, uri: {server_uri}")

        # register it with the embedded nameserver
        self._nameserver.nameserver.register(name, server_uri)
        return server_uri

    def wait(self):
        # assert self.is_started, "Cannot wait fpr pyro server which is not started"
        if self.is_started:
            self._thread.join()

    @staticmethod
    def proxy_for(name: str) -> Pyro5.api.Proxy:
        # print(f"proxy for: {name}")
        return Pyro5.api.Proxy(name)

    @property
    def is_started(self) -> bool:
        return self._thread.is_alive()

    @property
    def is_up_and_running(self) -> bool:
        return self._flag_up_and_running.is_set()

    def start(self, wait: bool = True) -> None:
        if not self.is_started:
            self._thread.start()
        if wait:
            self._flag_up_and_running.wait()

    def stop(self, blocking: bool = False) -> None:
        self._flag_shutdown.set()
        if blocking:
            self.wait()

    def _runner(self):
        # start a name server with broadcast server
        my_ip = Pyro5.socketutil.get_ip_address(None, workaround127=True)
        log.debug(f"Pyro provides ip {my_ip}")
        nameserver_uri, nameserver_daemon, broadcast_server = Pyro5.api.start_ns(host=my_ip, enableBroadcast=True)
        assert broadcast_server is not None, "expect a broadcast server to be created"
        log.debug("Pyro provides nameserver: uri=%s" % nameserver_uri)

        self._nameserver = nameserver_daemon

        self._pyrodaemon.combine(nameserver_daemon)
        self._pyrodaemon.combine(broadcast_server)

        def _loop():
            return not self._flag_shutdown.is_set()

        self._flag_up_and_running.set()
        log.debug("Pyro is up and running")
        self._pyrodaemon.requestLoop(_loop)
        self._flag_up_and_running.clear()

        # cleanup
        log.debug("PyroServer: stopping nameserver..")
        nameserver_daemon.close()
        log.debug("PyroServer: stopping broadcast server..")
        broadcast_server.close()
        log.debug("PyroServer: stopping daemon..")
        self._pyrodaemon.close()
        log.debug("PyroServer shut down")
