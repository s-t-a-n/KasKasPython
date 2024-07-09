from serial import Serial
from serial import SerialTimeoutException
import time
from datetime import datetime
import numpy as np
import os
import glob
import csv
from typing import Optional
from pathlib import Path
from enum import Enum, Flag, auto
from multiprocessing.synchronize import Lock as LockType
from multiprocessing import Lock

from io import RawIOBase

from _jasjas.datalink.serial import open_next_available_serial


# from _jasjas.


class JasJasGrowbed:
    """_summary_"""

    _io: RawIOBase
    _lock: LockType

    def __init__(self, io: RawIOBase = None) -> None:
        self._io = io

        self._lock = Lock()

    class Response:
        class Status(Flag):
            OK = auto()
            BAD_INPUT = auto()
            BAD_RESULT = auto()
            TIMEOUT = auto()
            BAD_RESPONSE = auto()
            UNKNOWN_ERROR = auto()

        status: Status
        arguments: Optional[list[str]]

        def __init__(
                self, status: Status, arguments: Optional[list[str]] = None
        ) -> None:
            self.status = status
            self.arguments = arguments

        def __bool__(self) -> bool:
            return self.status & (self.Status.OK | self.Status.BAD_INPUT | self.Status.BAD_RESULT)

        def __str__(self) -> str:
            status = f"[bold green]{self.status}" if self.status == self.Status.OK else f"[bold red]{self.status}"
            return f"{status}: {self.arguments} "

    class OP(Enum):
        FUNCTION_CALL = "!"
        ASSIGNMENT = "="
        ACCESS = "?"
        RESPONSE = "<"

    @property
    def io(self):
        if self._io is None:
            self._io = open_next_available_serial(baudrate=115200, timeout=1.5)
        return self._io

    def request(
            self, module: str, function: str, arguments: Optional[list[str]] = None
    ) -> Response:
        with self._lock:
            self._flush()
            # print("hello rrr")

            argument_substring = ":" + "|".join(arguments) if arguments else ""
            request_line = f"{module}!{function}{argument_substring}\r"
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
                return self.Response(self.Response.Status.TIMEOUT)

            correct_reply_header = module + str(self.OP.RESPONSE.value)
            if raw_line.startswith(correct_reply_header):
                line_reply_header_stripped = raw_line[len(correct_reply_header):]
                remainder = line_reply_header_stripped.split(":")

                if len(remainder) < 2:
                    print(f"couldnt find return value for reply: {raw_line}")
                    continue

                return_status = int(remainder[0])
                values_line = "".join(remainder[1:])

                values = values_line.split("|")[:-1]
                # print(f"Response: {raw_line} for values_line {values_line}")
                # print(f"found values {values}")
                return self.Response(
                    status=self.Response.Status(return_status), arguments=values
                )
            else:
                self._print_debug_line(raw_line)
                max_skipable_lines -= 1

        print(
            f"Request for {module} failed, couldnt find a respons in {max_skipable_lines} times"
        )
        return self.Response(self.Response.Status.BAD_RESPONSE)

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
            print(f"DBG: {line}")
