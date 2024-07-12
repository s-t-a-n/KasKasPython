import glob
from typing import List
from serial import Serial
from serial import SerialTimeoutException
from serial import SerialException


def find_serial_ports() -> List[str]:
    ports = glob.glob("/dev/ttyACM[0-9]*")
    res = []
    for port in ports:
        try:
            s = Serial(port)
            s.close()
            res.append(port)
        except:
            pass
    return res


def has_available_serial_ports() -> bool:
    return len(find_serial_ports()) > 0


def open_next_available_serial(baudrate: int = 115200, timeout: float = 1.5) -> Serial:
    for port in find_serial_ports():
        try:
            ser = Serial(port, baudrate, timeout=timeout)
            if ser.is_open:
                return ser
        except SerialTimeoutException:
            pass
    raise SerialException("No serial ports available")
