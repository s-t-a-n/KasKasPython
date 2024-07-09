from .atomic_counter import AtomicCounter


class CPULock:
    """Context manager for locking maximum number of busy processes"""

    ctr: AtomicCounter
    cpu_count: int

    def __init__(self):
        self.ctr = AtomicCounter()

        from os import cpu_count

        self.cpu_count = cpu_count()

    def __enter__(self):
        self.lock()

    def __exit__(self, etype, value, traceback):
        self.release()

    def wait(self, timeout: int = None) -> bool:
        """Wait until enough CPU cores are available or when timeout expires"""
        return self.ctr.wait_below(self.cpu_count, timeout=timeout)

    def lock(self):
        """Lock CPU resource until enough cores are available"""
        self.ctr.wait_below(self.cpu_count)
        self.ctr.inc()

    def release(self):
        """Release CPU resource lock."""
        self.ctr.dec()
