from pathlib import Path
from typing import *

from filelock import BaseFileLock
from filelock import FileLock as FileLockImp
from filelock import Timeout


class FileLock:
    _lock: BaseFileLock = None

    _level: int = 0

    def __init__(self, lock_file: Path):
        self._lock_file = lock_file
        self._lock = FileLockImp(lock_file=self._lock_file)

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def acquire(self, timeout: Optional[float] = None, blocking: bool = True) -> bool:
        self._level += 1
        if self._level > 1:
            return True
        try:
            self._lock.acquire(timeout=timeout, blocking=blocking)
            return True
        except Timeout:
            return False

    def release(self):
        self._level -= 1
        if self._level > 1:
            return
        self._lock.release()

    @property
    def is_locked(self) -> bool:
        return self._lock.is_locked


# def file_locked():
#     def decorator(f):
#         def wrapper(file_name: str, *args, **kwargs):
#             print(f"filename: {file_name}")
#
#             lockfile = FileLock(file_name + ".lock")
#
#             print("waiting for lock")
#             with lockfile:
#                 print("unlocked")
#                 ret = f(*args, **kwargs)
#             return ret
#
#         return wrapper
#
#     return decorator
#
#
# @file_locked()
# def funky(foo):
#     import time
#
#     time.sleep(4)
#     print(foo)

# funky(file_name="test", foo="bar")
# exit(0)
