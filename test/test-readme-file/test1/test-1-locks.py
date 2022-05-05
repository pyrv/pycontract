
from pycontract import *
import unittest
import test.utest

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


class AcquireRelease(Monitor):
    @initial
    class Start(AlwaysState):
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
                case Release(self.thread, self.lock):
                    return ok


class ShortAcquireRelease(Monitor):
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
                case Release(self.thread, self.lock):
                    return ok


class CountingAcquireRelease(Monitor):
    def __init__(self):
        super().__init__()
        self.count: int = 0

    def transition(self, event):
        match event:
            case Acquire(thread, lock):
                if self.count < 3:
                    self.count += 1
                    return self.Locked(thread, lock)
                else:
                    return error('more that 3 locks acquired')

    @data
    class Locked(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Acquire(_, self.lock):
                    return error('lock re-acquired')
                case Release(self.thread, self.lock):
                    self.count -= 1
                    return ok


class ConditionedAcquireRelease(Monitor):
    def __init__(self):
        super().__init__()
        self.count: int = 0

    def transition(self, event):
        match event:
            case Acquire(thread, lock) if self.count < 3:
                self.count += 1
                return self.Locked(thread, lock)
            #case Acquire(thread, lock) if self.count >= 3:
            case Acquire(_, _):
                 return error('more that 3 locks acquired')


    @data
    class Locked(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Acquire(_, self.lock):
                    return error('lock re-acquired')
                case Release(self.thread, self.lock):
                    self.count -= 1
                    return ok


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files('test-1-locks.AcquireRelease.test.pu', 'test-1-locks.AcquireRelease.pu')
        self.assert_equal_files('test-1-locks.ConditionedAcquireRelease.test.pu', 'test-1-locks.ConditionedAcquireRelease.pu')
        self.assert_equal_files('test-1-locks.CountingAcquireRelease.test.pu', 'test-1-locks.CountingAcquireRelease.pu')
        self.assert_equal_files('test-1-locks.ShortAcquireRelease.test.pu', 'test-1-locks.ShortAcquireRelease.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = ConditionedAcquireRelease()
        set_debug(True)
        m.eval(Acquire("arm", 10))
        m.eval(Acquire("wheel", 12))
        m.eval(Acquire("arm", 121))
        m.eval(Acquire("arm", 122))
        m.eval(Release("arm", 12))
        m.eval(Release("wheel", 12))
        m.end()
        errors_expected = [
            "*** error transition in ConditionedAcquireRelease:\n    state Always()\n    event 4 Acquire(thread='arm', lock=122)\n    more that 3 locks acquired",
            "*** error at end in ConditionedAcquireRelease:\n    terminates in hot state Locked('arm', 10)",
            "*** error at end in ConditionedAcquireRelease:\n    terminates in hot state Locked('arm', 121)"]
        errors_actual = m.get_all_errors()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)


if __name__ == '__main__':
    unittest.main()





