# """Test cases for the api module."""
# import typing
# from threading import Thread
# from time import sleep
#
# import pytest
#
# from _kapstok.utils.atomic_counter.atomic_counter import AtomicCounter
#
#
# def test_atomic_counter_basics():
#     ctr = AtomicCounter()
#
#     assert ctr.value == 0
#     ctr.inc()
#     assert ctr.value == 1
#     ctr.dec()
#     assert ctr.value == 0
#
#     def count_func(ctr: AtomicCounter):
#         for i in range(10):
#             sleep(0.001)
#             ctr.inc()
#         for i in range(10):
#             sleep(0.001)
#             ctr.dec()
#
#     ctr = AtomicCounter()
#
#     t1 = Thread(target=count_func, daemon=True, args=[ctr])
#     t2 = Thread(target=count_func, daemon=True, args=[ctr])
#
#     t1.start()
#     t2.start()
#
#     assert ctr.wait_above(1) is True
#     assert ctr.wait_below(2) is True
#     assert ctr.wait_equal(0) is True
#
#     assert ctr.value == 0
#
#     ctr = AtomicCounter(1)
#     assert ctr.value == 1
#
#
# def test_atomic_counter_wait_timeout():
#     ctr = AtomicCounter()
#
#     assert ctr.wait_above(0, timeout=0.01) is False
#     assert ctr.wait_below(-1, timeout=0.01) is False
#     assert ctr.wait_equal(1, timeout=0.01) is False
