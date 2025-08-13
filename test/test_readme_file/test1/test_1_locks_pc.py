
import os
import pycontract as pc
import unittest
import test.utest

"""
Examples in README.md file.
"""
DIR = os.path.dirname(__file__) + '/'

@pc.data
class Acquire(pc.Event):
    thread: str
    lock: int


@pc.data
class Release(pc.Event):
    thread: str
    lock: int


class AcquireRelease(pc.Monitor):
    @pc.initial
    class Start(pc.AlwaysState):
        def transition(self, event):
            match event:
                case Acquire(thread, lock):
                    return self.Locked(thread, lock)

    @pc.data
    class Locked(pc.HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Acquire(_, self.lock):
                    return pc.error('lock re-acquired')
                case Release(self.thread, self.lock):
                    return pc.ok


class ShortAcquireRelease(pc.Monitor):
    def transition(self, event):
        match event:
            case Acquire(thread, lock):
                return self.Locked(thread, lock)

    @pc.data
    class Locked(pc.HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Acquire(_, self.lock):
                    return pc.error('lock re-acquired')
                case Release(self.thread, self.lock):
                    return pc.ok


class CountingAcquireRelease(pc.Monitor):
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
                    return pc.error('more that 3 locks acquired')

    @pc.data
    class Locked(pc.HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Acquire(_, self.lock):
                    return pc.error('lock re-acquired')
                case Release(self.thread, self.lock):
                    self.count -= 1
                    return pc.ok


class ConditionedAcquireRelease(pc.Monitor):
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
                 return pc.error('more that 3 locks acquired')


    @pc.data
    class Locked(pc.HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Acquire(_, self.lock):
                    return pc.error('lock re-acquired')
                case Release(self.thread, self.lock):
                    self.count -= 1
                    return pc.ok


class Test1(test.utest.Test):
    def test1(self):
        pc.visualize(__file__, True)
        self.assert_equal_files(DIR + 'test_1_locks_pc.AcquireRelease.test.pu', DIR + 'test_1_locks_pc.AcquireRelease.pu')
        self.assert_equal_files(DIR + 'test_1_locks_pc.ConditionedAcquireRelease.test.pu', DIR + 'test_1_locks_pc.ConditionedAcquireRelease.pu')
        self.assert_equal_files(DIR + 'test_1_locks_pc.CountingAcquireRelease.test.pu', DIR + 'test_1_locks_pc.CountingAcquireRelease.pu')
        self.assert_equal_files(DIR + 'test_1_locks_pc.ShortAcquireRelease.test.pu', DIR + 'test_1_locks_pc.ShortAcquireRelease.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = ConditionedAcquireRelease()
        pc.set_debug(True)
        m.eval(Acquire("arm", 10))
        m.eval(Acquire("wheel", 12))
        m.eval(Acquire("arm", 121))
        m.eval(Acquire("arm", 122))
        m.eval(Release("arm", 12))
        m.eval(Release("wheel", 12))
        m.end()
        errors_expected = [
            "*** error transition in ConditionedAcquireRelease:\n    state Always()\n    event 4 Acquire(thread='arm', lock=122)\n    more that 3 locks acquired",
            "[HOT STATE] *** error at end in ConditionedAcquireRelease:\n    terminates in hot state Locked('arm', 10)",
            "[HOT STATE] *** error at end in ConditionedAcquireRelease:\n    terminates in hot state Locked('arm', 121)"]
        errors_actual = m.get_all_message_texts()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)
