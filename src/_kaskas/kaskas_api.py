from _kaskas.log import log
from serial import SerialTimeoutException
from serial import SerialException
from datetime import datetime
from typing import Optional
from pathlib import Path
from enum import Enum, Flag, auto
from multiprocessing.synchronize import Lock
from multiprocessing import Lock as createLock
from multiprocessing import Queue

from threading import Thread, Event

from io import RawIOBase
from typing import TextIO

from _kaskas.utils.io_serial import open_next_available_serial

import Pyro5.api


class Datalink:
    """ Responsible for untangling log from api information passing over serial"""

    _flag_shutdown: Event
    _flag_up_and_running: Event

    _thread: Thread

    _io: RawIOBase
    _outgoing: Queue[bytes]
    _log: Queue[str]
    _api: Queue[str]

    def __init__(self, io: RawIOBase):
        self._flag_shutdown = Event()
        self._flag_up_and_running = Event()
        self._thread = Thread(target=self._runner)
        self._io = io
        self._outgoing = Queue()
        self._log = Queue()
        self._api = Queue()

        import os
        os.set_blocking(io.fileno(), False)

    def write_line(self, line: str):
        self._outgoing.put(line.encode("utf-8"))

    def next_log_line(self, block: bool = False) -> Optional[str]:
        return self._log.get(block=block)

    def next_api_line(self, block: bool = False) -> Optional[str]:
        return self._api.get(block=block)

    def _runner(self):
        while not self._flag_shutdown.is_set():
            while outgoing := self._outgoing.get(block=False):
                self._io.write(outgoing)
            for line in [l.decode("utf-8").replace("\r", "").replace("\n", "") for l in self._io.readlines() if
                         len(l) > 0]:
                if line.startswith("!"):
                    self._log.put(line)
                else:
                    self._api.put(line)


class Response:
    class Status(Flag):
        OK = auto()
        BAD_INPUT = auto()
        BAD_RESULT = auto()
        BAD_RESPONSE = auto()
        COMMUNICATION_ERROR = auto()
        TIMEOUT = auto()
        UNKNOWN_ERROR = auto()

    status: Status
    arguments: Optional[list[str]]

    def __init__(
            self, status: Status, arguments: Optional[list[str]] = None
    ) -> None:
        self.status = self.Status(status)
        self.arguments = arguments

    def __bool__(self) -> bool:
        return bool(self.status & (self.Status.OK | self.Status.BAD_INPUT | self.Status.BAD_RESULT))

    def __str__(self) -> str:
        status = f"[bold green]{self.status.name}[/bold green]" if self.status == self.Status.OK else f"[bold red]{self.status.name}[/bold red]"
        return f"{status}: {self.arguments} "


class Operator(Enum):
    REQUEST = ":"
    RESPONSE = "<"


@Pyro5.api.expose
class KasKasAPI:
    """_summary_"""

    _log_file: TextIO
    _io: Optional[RawIOBase]
    _lock: Lock

    def __init__(self, log_filename: Path, io: RawIOBase = None) -> None:
        self._log_file = open(log_filename, mode="a+")
        self._io = io
        self._lock = createLock()

    @staticmethod
    def cannonical_name() -> str:
        return "kaskas.api"

    @property
    def io(self) -> Optional[RawIOBase]:
        if self._io is None:
            try:
                self._io = open_next_available_serial(baudrate=115200, timeout=1.5)
            except SerialException:
                pass
                log.info("Failed to open serial port")
        return self._io

    @property
    def is_connected(self) -> bool:
        return bool(self.io)

    def request(
            self, module: str, function: str, args: Optional[list[str]] = None
    ) -> Optional[Response]:
        with self._lock:
            if not self.is_connected:
                return Response(Response.Status.COMMUNICATION_ERROR, "Not connected")

            self._flush()

            argument_substring = ":" + "|".join(args) if args else ""
            request_line = f"{module}{str(self.Operator.REQUEST.value)}{function}{argument_substring}\r"
            # print(f"writing request line {request_line}")
            self.io.write(bytearray(request_line, "ascii"))
            self.io.flush()
            return self._read_response_for(module)

    def _read_response_for(self, module: str, max_skipable_lines: int = 32) -> Response:
        while max_skipable_lines > 0:
            try:
                raw_line = (
                    self.io.readline()
                    .decode("utf-8")
                    .replace("\r", "")
                    .replace("\n", "")
                )
                # print(f"_read_response_for: {raw_line}")
            except SerialTimeoutException:
                return Response(Response.Status.TIMEOUT)

            correct_reply_header = module + str(Operator.RESPONSE.value)
            if raw_line.startswith(correct_reply_header):
                line_reply_header_stripped = raw_line[len(correct_reply_header):]
                remainder = line_reply_header_stripped.split(":")

                if len(remainder) < 2:
                    log.error(f"couldnt find return value for reply: {raw_line}")
                    continue

                return_status = int(remainder[0])
                values_line = "".join(remainder[1:])

                values = values_line.split("|")[:-1]
                # print(f"Response: {raw_line} for values_line {values_line}")
                # print(f"found values {values}")
                return Response(
                    status=Response.Status(return_status), arguments=values
                )
            else:
                self._print_debug_line(raw_line)
                max_skipable_lines -= 1

        log.error(
            f"Request for {module} failed, couldnt find a respons in {max_skipable_lines} times"
        )
        return Response(Response.Status.BAD_RESPONSE)

    def _flush(self) -> None:
        # print("flush")
        while self.io.in_waiting > 0:
            try:
                # print(f"stuck reading got bytes: {self._serial.in_waiting}")
                line = (
                    self.io.readline()
                    .decode("utf-8")
                    .replace("\r", "")
                    .replace("\n", "")
                )
                # print("unstuck reading")
            except SerialTimeoutException:
                line = self.io.read_all()
            self._print_debug_line(line + "\n")

    def _print_debug_line(self, line: str) -> None:
        line = line.strip().replace("\r", "").replace("\n", "")
        if len(line) > 0:
            # log.info(f"DBG: {line}")
            self._log_file.write(f"{datetime.now()}: {line}\n")
            self._log_file.flush()


def response_dict_to_response(response, d):
    return Response(d["status"], d["arguments"])


Pyro5.api.register_dict_to_class("_kaskas.kaskas_api.Response", response_dict_to_response)
