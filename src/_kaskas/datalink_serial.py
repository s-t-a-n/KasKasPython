import logging
import os
import time
from datetime import datetime
from enum import Enum, Flag, auto
from io import RawIOBase
from multiprocessing import Lock as createLock, Queue
from multiprocessing.synchronize import Lock
from pathlib import Path
from queue import Empty as QueueEmpty
from threading import Event, Thread
from typing import Optional, TextIO

from serial import SerialException, SerialTimeoutException

from _kaskas.dialect import Dialect
from _kaskas.log import log
from _kaskas.utils.filelock import FileLock
from _kaskas.utils.io_serial import open_next_available_serial


class Datalink:
    """ Responsible for untangling log from API information passing over serial"""

    _flag_shutdown: Event
    _flag_up_and_running: Event
    _thread: Thread

    _io_handle: RawIOBase

    _outgoing: Queue
    _incoming_api: Queue
    _incoming_api_remainder: Optional[list[str]]

    _log_file: TextIO

    _filelock: FileLock

    def __init__(self, root: Path, io: RawIOBase = None, io_timeout: float = 0.1):
        self._flag_shutdown = Event()
        self._flag_up_and_running = Event()
        self._thread = Thread(target=self._runner)
        self._io_handle = io
        self._io_timeout = io_timeout
        self._outgoing = Queue()
        self._incoming_api = Queue()
        self._incoming_api_remainder = None
        self._log_file = open(root / "kaskas.log", mode="a+")
        self._filelock = FileLock(root / "kaskas.lock")

        if not self._filelock.acquire(timeout=0.1):
            raise RuntimeError("KasKas API was already locked!")

        self._lock = createLock()
        os.set_blocking(self._io.fileno(), False)  # Ensure IO is non-blocking

    # def __del__(self):
    #     self._filelock.release()

    def write_line(self, line: str):
        with self._lock:
            self._outgoing.put(line.encode("utf-8"))

    def next_api_line(self, timeout: float = None) -> Optional[str]:
        try:
            return self._incoming_api.get(timeout=timeout)
        except QueueEmpty:
            return None

    @property
    def is_connected(self) -> bool:
        return self._io is not None

    def _runner(self):
        self._flag_up_and_running.set()
        while not self._flag_shutdown.is_set():
            try:
                self._process_incoming()
                self._process_outgoing()
            except SerialTimeoutException:
                log.exception("Serial timeout occurred")

    def _process_outgoing(self):
        if self._incoming_api_remainder:
            return  # Wait until the remainder has been fully read

        try:
            while outgoing := self._outgoing.get(block=False):
                self._io.write(outgoing)
                self._io.flush()
                time.sleep(self._io_timeout)
        except QueueEmpty:
            pass

    def _process_incoming(self):
        for line in self._read_lines():
            if line.startswith(Dialect.HEADER_LOG):
                self._handle_log_line(line[1:])
            elif line.startswith(Dialect.HEADER_API):
                self._handle_api_line(line[1:])
            elif line.startswith(Dialect.HEADER_DEBUG):
                self._handle_debug_line(line[1:])
            else:
                self._handle_unknown_line(line)

    def _read_lines(self) -> list[str]:
        try:
            lines = self._io.readlines()
            lines = [l.decode("utf-8").strip() for l in lines]  # decode to utf
            lines = [l for l in lines if l]  # no empty strings
            return lines;
        except Exception as e:
            log.warning("Exception while reading incoming data: %s", e)
            return []

    def _handle_log_line(self, line):
        log.info(line)
        self._log_file.write(f"{datetime.now()}: {line}\n")
        self._log_file.flush()

    def _handle_api_line(self, line):
        if line.endswith(Dialect.Operator.RESPONSE_FOOTER.value):
            complete_line = self._combine_with_remainder(line[:-1].strip())
            self._incoming_api.put(complete_line)
        else:
            if self._incoming_api_remainder is None:
                self._incoming_api_remainder = []
            self._incoming_api_remainder.append(line)

    def _handle_debug_line(self, line):
        log.debug(line)
        if log.level == logging.DEBUG:
            self._log_file.write(f"{datetime.now()}: {line}\n")

    def _handle_unknown_line(self, line):
        if self._incoming_api_remainder is not None:
            self._incoming_api_remainder.append(line)
            if line.endswith(Dialect.Operator.RESPONSE_FOOTER.value):
                complete_line = self._combine_with_remainder(line[:-1].strip())
                self._incoming_api.put(complete_line)
        else:
            log.warning(f"Datalink: received line without header: {line}")

    def _combine_with_remainder(self, line):
        if self._incoming_api_remainder:
            self._incoming_api_remainder.append(line)
            complete_line = "\n".join(self._incoming_api_remainder)
            self._incoming_api_remainder = None
            return complete_line
        return line

    @property
    def is_started(self) -> bool:
        return self._thread.is_alive()

    @property
    def is_up_and_running(self) -> bool:
        return self._flag_up_and_running.is_set()

    def wait(self):
        if self.is_started:
            self._thread.join()

    def start(self, wait: bool = True):
        if not self.is_started:
            self._thread.start()
        if wait:
            self._flag_up_and_running.wait()

    def stop(self, blocking: bool = False):
        self._flag_shutdown.set()
        if blocking:
            self.wait()

    @property
    def _io(self) -> Optional[RawIOBase]:
        if self._io_handle is None:
            try:
                self._io_handle = open_next_available_serial(baudrate=115200, timeout=self._io_timeout)
            except SerialException:
                log.error("Failed to open serial port")
        return self._io_handle
