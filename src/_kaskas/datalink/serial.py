import glob
from typing import List
from serial import Serial
from serial import SerialTimeoutException


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


def open_next_available_serial(baudrate: int = 115200, timeout: float = 1.5) -> Serial:
    ports = find_serial_ports()
    assert len(ports) > 0, "No serial ports available"
    for port in ports:
        try:
            ser = Serial(port, baudrate, timeout=timeout)
            if ser.is_open:
                return ser
        except SerialTimeoutException:
            pass
    raise RuntimeError("Unable to open serial port")
