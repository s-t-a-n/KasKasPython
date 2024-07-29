import string

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
from queue import Empty as QueueEmpty
from threading import Thread, Event
from io import RawIOBase
from typing import TextIO
import Pyro5.api

from _kaskas.utils.io_serial import open_next_available_serial
from _kaskas.utils.filelock import FileLock
from _kaskas.datalink_serial import Datalink as DatalinkSerial
from _kaskas.dialect import Dialect


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


@Pyro5.api.expose
class KasKasAPI:
    """_summary_"""

    _response_timeout: float
    _dl: DatalinkSerial

    def __init__(self, datalink: DatalinkSerial, response_timeout: float = 3.0) -> None:

        self._response_timeout = response_timeout
        self._dl = datalink
        self._dl.start()

    @staticmethod
    def cannonical_name() -> str:
        return "kaskas.api"

    def request(
            self, module: str, function: Optional[str], args: Optional[list[str]] = None
    ) -> Optional[Response]:
        if not self._dl.is_connected:
            return Response(Response.Status.COMMUNICATION_ERROR, ["Not connected"])

        request_line = None
        if module == "?":  # this is a request to print usage
            request_line = f"{Dialect.Operator.REQUEST_PRINT_USAGE.value}\n"
        else:
            argument_substring = ":" + "|".join(args) if args else ""
            request_line = f"{module}{str(Dialect.Operator.REQUEST.value)}{function}{argument_substring}\n"  # \r\n ?
        # print(f"writing request line {request_line}")
        self._dl.write_line(request_line)
        return self._read_response_for(module)

    def _read_response_for(self, module: str) -> Response:
        raw_line = self._dl.next_api_line(timeout=self._response_timeout)
        # assert raw_line and len(raw_line) > 0, f"datalink gave illegal response: {raw_line}"

        if not raw_line:
            return Response(Response.Status.TIMEOUT)

        correct_reply_header = f"{module}{Dialect.Operator.RESPONSE.value}"
        if not raw_line.startswith(correct_reply_header):
            log.error(
                f"API: Request for {module} failed, ill conceived reply: {raw_line}, (correct header: {correct_reply_header})")
            return Response(Response.Status.BAD_RESPONSE)

        remainder = raw_line[len(correct_reply_header):]
        remainder_splitted = remainder.split(":")

        try:
            return_status = Response.Status[remainder_splitted[0]]
        except KeyError:
            raise ValueError(f"Unknown status: {return_status}")

        remainder = remainder[len(remainder_splitted[0]) + 1:]  # skip return code and seperator

        if module == "?":  # this is a request for usage
            values = ["".join(remainder)]  # without statuscode
        else:  # this is a reply to an api request
            remainder_splitted = remainder.split("|")
            values = remainder_splitted if len(remainder_splitted) > 1 else [remainder]

            # print(f"_read_response_for: returning values: {values}")
        return Response(
            status=Response.Status(return_status), arguments=values
        )

    # def _print_debug_line(self, line: str) -> None:
    #     line = line.strip().replace("\r", "").replace("\n", "")
    #     if len(line) > 0:
    #         # log.info(f"DBG: {line}")
    #         self._log_file.write(f"{datetime.now()}: {line}\n")
    #         # self._log_file.flush()


def response_dict_to_response(response, d):
    return Response(d["status"], d["arguments"])


Pyro5.api.register_dict_to_class("_kaskas.kaskas_api.Response", response_dict_to_response)
