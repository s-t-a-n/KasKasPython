from _kaskas.log import log
import time
from datetime import datetime
import os
from typing import Optional
from pathlib import Path
import errno
from threading import Thread, Event

import Pyro5.api
import Pyro5.nameserver

from _kaskas.kaskas_api import KasKasAPI

from rich.progress import open as rich_open


# from streamlit.web import cli


class StreamlitLauncher:
    """_summary_"""

    _flag_shutdown: Event
    _flag_up_and_running: Event

    _thread: Thread
    _pyrodaemon: Pyro5.api.Daemon
    _nameserver: Pyro5.nameserver.NameServerDaemon

    _root: Path
    _api: KasKasAPI | Pyro5.api.Proxy

    def __init__(self, root: Path, api: KasKasAPI | Pyro5.api.Proxy) -> None:
        self._flag_shutdown = Event()
        self._flag_up_and_running = Event()
        self._thread = Thread(target=self._runner)
        self._root = root
        self._api = api

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

    def _runner(self):

        import os
        script_dir = Path(os.path.dirname(os.path.realpath(__file__)))
        memory_guard_filepath = script_dir / "streamlit_memory_guard.sh"
        app_filepath = script_dir / "streamlit_app.py"

        log.debug(
            f"Streamlit launcher; starting memory_guard and executing: 'python {str(self._root)} {str(app_filepath)} {str(self._root)} {KasKasAPI.cannonical_name()}'")

        from subprocess import Popen, PIPE, STDOUT
        streamlit_memoryguard = Popen(["bash", str(memory_guard_filepath)],
                                      stdout=PIPE, stderr=STDOUT, encoding='utf-8')
        streamlit = Popen(
            ["streamlit", "run", "--browser.gatherUsageStats", "false", "--server.headless", "true", str(app_filepath),
             str(self._root),
             KasKasAPI.cannonical_name()],
            stdout=PIPE, stderr=STDOUT, encoding='utf-8')
        self._flag_up_and_running.set()

        def log_line(title: str, line: str):

            loglevel = line.split(":")[0]
            line = "".join(line.split(":")[1:])
            line = line.replace("\n", "")
            if len(line.strip()) <= 1:
                return

            line = f"{title}: {line}"

            match loglevel:
                case "INFO":
                    log.info(line)
                case "CRITICAL":
                    log.critical(line)
                case "WARNING":
                    log.warning(line)
                case _:
                    log.debug(line)

        while not self._flag_shutdown.is_set() and self._thread.is_alive():
            for line in streamlit.stdout:
                log_line("Streamlit", line)
            for line in streamlit_memoryguard.stdout:
                log_line("Streamlit memoryguard", line)
            time.sleep(0.1)

        streamlit_exitcode = streamlit.wait()
        streamlit_memoryguard.kill()
        log.debug(f"Streamlit closed down with exitcode {streamlit_exitcode}")

        # cli.main_run([str(app_file), str(self._root), KasKasAPI.cannonical_name()])

        # no auth
        # cli.main_run(str(app_file), [str(self._root), KasKasAPI.cannonical_name()])

        # cli.main_run(str(app_file), api_id=KasKasAPI.cannonical_name(), auth_file=self._root / Path("auth.yml"))
