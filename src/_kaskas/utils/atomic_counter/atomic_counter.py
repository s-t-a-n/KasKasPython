# from typing import *
# from threading import Event
# from threading import RLock
# from time import time
#
# from functools import total_ordering
#
# @total_ordering
# class AtomicCounter:
#     _value: int
#     _default_value: int
#     _lock: RLock
#     _event: Event
#
#     def __init__(self, value: int | SupportsInt = 0):
#         self._value = int(value)
#         self._default_value = int(value)
#         self._lock = RLock()
#         self._event = Event()
#
#     def _signal(self):
#         self._event.set()
#         self._event.clear()
#
#     def _wait(self, op: str, d: int, timeout: float) -> bool:
#         start = time()
#         while timeout is None or timeout > 0:
#             if any(
#                 [
#                     op == "=" and self.value == d,
#                     op == ">" and self.value > d,
#                     op == "<" and self.value < d,
#                 ]
#             ):
#                 return True
#             timeout = timeout - (time() - start) if timeout else None
#             self._event.wait(timeout)
#         return False
#
#     def inc(self, d: int = 1) -> int:
#         with self._lock:
#             self._value += d
#             self._signal()
#             return self._value
#
#     def dec(self, d: int = 1) -> int:
#         return self.inc(-d)
#
#     def reset(self):
#         with self._lock:
#             self._value = self._default_value
#
#     @property
#     def value(self) -> int:
#         with self._lock:
#             return self._value
#
#     def wait_equal(self, d: int, timeout: float = None) -> bool:
#         return self._wait(d=d, op="=", timeout=timeout)
#
#     def wait_below(self, d: int, timeout: float = None):
#         return self._wait(d=d, op="<", timeout=timeout)
#
#     def wait_above(self, d: int, timeout: float = None):
#         return self._wait(d=d, op=">", timeout=timeout)
#
#     def __eq__(self, other):
#         return self.value == int(other)
#
#     def __lt__(self, other):
#         return int(self.value) < int(other)
#
#     def __int__(self):
#         return int(self.value)
#
#     def __enter__(self):
#         self._lock.acquire()
#
#     def __exit__(self, etype, value, traceback):
#         self._lock.release()
#
#
# class AtomicInteger(AtomicCounter):
#     def __init__(self, d: int | SupportsInt = 0):
#         super().__init__(d)
#
#     def set_value(self, d: int | SupportsInt = 0):
#         with self._lock:
#             self._value = int(d)
