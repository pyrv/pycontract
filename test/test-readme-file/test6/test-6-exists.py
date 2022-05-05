
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


class PastAcquireRelease(Monitor):
    def transition(self, event):
        match event:
            case Acquire(thread, lock):
                return self.Locked(thread, lock)
            case Release(thread, lock) if not self.Locked(thread, lock):
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
                    return ok


class FlexiblePastAcquireRelease(Monitor):
    def acquired(self, lock: object) -> Callable[[State], bool]:
        def predicate(state: State) -> bool:
            match state:
                case self.Locked(_, lock_) if lock_ == lock:
                    return True
        return predicate

    def transition(self, event):
        match event:
            case Acquire(thread, lock):
                return self.Locked(thread, lock)
            case Release(_, lock) if not self.exists(self.acquired(lock)):
                return error(f'thread releases un-acquired lock {lock}')

    @data
    class Locked(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Acquire(_, self.lock):
                    return error('lock re-acquired')
                case Release(_, self.lock):
                    return ok


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files('test-6-exists.PastAcquireRelease.test.pu', 'test-6-exists.PastAcquireRelease.pu')
        self.assert_equal_files('test-6-exists.FlexiblePastAcquireRelease.test.pu', 'test-6-exists.FlexiblePastAcquireRelease.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = FlexiblePastAcquireRelease()
        set_debug(True)
        m.eval(Acquire("arm", 10))
        m.eval(Acquire("wheel", 12))
        m.eval(Release("arm", 10))
        m.eval(Release("arm", 12))
        m.eval(Release("arm", 13))
        m.end()
        errors_expected = [
            "*** error transition in FlexiblePastAcquireRelease:\n    state Always()\n    event 5 Release(thread='arm', lock=13)\n    thread releases un-acquired lock 13"]
        errors_actual = m.get_all_errors()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)


if __name__ == '__main__':
    unittest.main()





