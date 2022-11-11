
import os
from pycontract import *
import unittest
import test.utest

DIR = os.path.dirname(__file__) + '/'

"""
Examples in README.md file.
"""

@data
class Acquire(Event):
    thread: str
    lock: int


@data
class Release(Event):
    thread: str
    lock: int


@data
class ReleaseAll(Event):
    pass


class LockMonitor(Monitor):
    def key(self, event) -> Optional[object]:
        match event:
            case Acquire(_, lock):
                return lock
            case Release(_, lock):
                return lock
            case ReleaseAll():
                return None


class AcquireRelease(LockMonitor):
    def transition(self, event):
        match event:
            case Acquire(thread, lock):
                return self.Locked(thread, lock)

    @data
    class Locked(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Acquire(_, self.lock):
                    return error('lock re-acquired')
                case ReleaseAll() | Release(self.thread, self.lock):
                    return ok


class PastAcquireRelease(LockMonitor):
    @initial
    class Start(State):
        def transition(self, event):
            match event:
                case Acquire(thread, lock):
                    return self.Locked(thread, lock)
                case Release(thread, lock):
                    return error(f'thread {thread} releases un-acquired lock {lock}')

    @data
    class Locked(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Acquire(_, self.lock):
                    return error('lock re-acquired')
                case Release(self.thread, self.lock):
                    return self.Start()


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test-8-indexing.LockMonitor.test.pu', DIR + 'test-8-indexing.LockMonitor.pu')
        self.assert_equal_files(DIR + 'test-8-indexing.AcquireRelease.test.pu', DIR + 'test-8-indexing.AcquireRelease.pu')
        self.assert_equal_files(DIR + 'test-8-indexing.PastAcquireRelease.test.pu', DIR + 'test-8-indexing.PastAcquireRelease.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = PastAcquireRelease()
        set_debug(True)
        trace = [
            Acquire("arm", 10),
            Acquire("wheel", 12),
            Release("arm", 10),
            Release("arm", 14)

        ]
        m.verify(trace)
        errors_expected = [
            "*** error transition in PastAcquireRelease:\n    state Start()\n    event 4 Release(thread='arm', lock=14)\n    thread arm releases un-acquired lock 14",
            "*** error at end in PastAcquireRelease:\n    terminates in hot state Locked('wheel', 12)"]

        errors_actual = m.get_all_message_texts()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)






