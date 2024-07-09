""" Thread condition for guaranteed readiness of data and guaranteed receive of signal """

from threading import Condition
from threading import Event
from threading import Lock
from typing import *


class LockedEvent:
    lock: Lock
    event: Event

    def __init__(self, lock: Lock, event: Event):
        self.lock = lock
        self.event = event


class Beacon:
    _signal: Condition
    _unicast: LockedEvent
    _my_broadcast: LockedEvent
    _all_broadcasts: List[LockedEvent]

    def __init__(
        self,
        signal: Condition,
        unicast: LockedEvent,
        my_broadcast: LockedEvent,
        all_broadcast: List[LockedEvent],
    ):
        self._signal = signal
        self._unicast = unicast
        self._my_broadcast = my_broadcast
        self._all_broadcasts = all_broadcast

    def is_set(self) -> bool:
        return self._unicast.event.is_set() or self._my_broadcast.event.is_set()

    def wait(self):
        while True:
            # with self._my_broadcast.lock:
            if self._my_broadcast.event.is_set():
                print("broadcast unlock")
                self._my_broadcast.event.clear()
                return

            # problem: order of waiting

            if self._unicast.event.is_set():
                if self._unicast.lock.acquire(blocking=False):
                    print("unicast unlock")
                    self._unicast.event.clear()
                    self._unicast.lock.release()
                    return

            with self._signal:
                self._signal.wait()

    def notify_all(self):
        for broadcast in self._all_broadcasts:
            with broadcast.lock:
                broadcast.event.set()

        with self._signal:
            self._signal.notify_all()

    def notify(self):
        with self._unicast.lock:
            self._unicast.event.set()

        with self._signal:
            self._signal.notify_all()


class Factory:
    _signal: Condition
    _unicast: LockedEvent
    _broadcasts: List[LockedEvent]

    def __init__(self):
        self._signal = Condition()
        self._unicast = LockedEvent(lock=Lock(), event=Event())
        self._broadcasts = []

    def beacon(self) -> Beacon:
        new = LockedEvent(lock=Lock(), event=Event())
        self._broadcasts.append(new)
        return Beacon(
            signal=self._signal,
            unicast=self._unicast,
            my_broadcast=new,
            all_broadcast=self._broadcasts,
        )


factory = Factory()


# b1.notify()
#
# print(b2.is_set())
# b2.wait()
# print(b2.is_set())
#
# b1.notify_all()
# print(b1.is_set())
# print(b2.is_set())
#
# b1.wait()
# b2.wait()
#
# b2.notify_all()
#
# b1.wait()
# b2.wait()
#
# b1.notify()
# b1.wait()


from threading import Thread
from time import sleep


def producer(beacon: Beacon):
    while True:
        beacon.notify_all()
        sleep(1)


from _kapstok.utils.atomic_counter import AtomicCounter


g_ctr = AtomicCounter()


def consumer(beacon: Beacon, ctr: AtomicCounter):
    while True:
        beacon.wait()
        print(f"received {ctr.inc()}")


def spinup_consumers(amount: int):
    ts = []

    for _ in range(amount):
        t = Thread(target=consumer, args=[factory.beacon(), g_ctr])
        t.start()
        ts.append(t)
    return ts


def spinup_producers(amount: int):
    ts = []

    for _ in range(amount):
        t = Thread(target=producer, args=[factory.beacon()])
        t.start()
        ts.append(t)
    return ts


consumers = spinup_consumers(amount=1000)
producers = spinup_producers(amount=1)

# prod_thread1 = Thread(target=producer, args=[factory.beacon()])
# prod_thread1.start()
# prod_thread2 = Thread(target=producer, args=[factory.beacon()])
# prod_thread2.start()
# cons_thread1 = Thread(target=consumer, args=[factory.beacon(), g_ctr])
# cons_thread1.start()
# cons_thread2 = Thread(target=consumer, args=[factory.beacon(), g_ctr])
# cons_thread2.start()
