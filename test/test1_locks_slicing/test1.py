import os
import pathlib

from pycontract import *
import unittest
import test.utest

DIR = os.path.dirname(__file__) + '/'

# Property AcquireRelease:
# A task acquiring a lock should eventually release it.
# At most one task can acquire a lock at a time. Locks
# are not re-entrant (a task cannot take the same lock
# more than once before releasing it).
#
# Using slicing

"""
Events:
"""


@data
class Acquire(Event):
    task: int
    lock: int


@data
class Release(Event):
    task: int
    lock: int


"""
Monitor:
"""


class LockMonitor(Monitor):
    def key(self, event) -> object:
        match event:
            case Acquire(task, lock):
                return lock
            case Release(task, lock):
                return lock


class AcquireRelease(LockMonitor):
    @initial
    @data
    class Start(State):
        def transition(self, event):
            match event:
                case Acquire(task, lock):
                    return self.Acquired(task, lock)

    @data
    class Acquired(HotState):
        task: int
        lock: int

        def transition(self, event):
            match event:
                case Acquire(_, self.lock):
                    return error(f'P{self.lock} acquired again')
                case Release(self.task, self.lock):
                    return ok


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test1.AcquireRelease.test.pu', DIR + 'test1.AcquireRelease.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = AcquireRelease()
        set_debug(True)

        trace = [
             Acquire(1, 100),
             Acquire(1, 200),
             Acquire(2, 300),
             Release(1, 100),
             Release(1, 200),
             Release(2, 300)
        ]
        m.verify(trace)

        errors_expected = []
        errors_actual = m.get_all_messages()
        self.assertEqual(errors_expected, errors_actual)

    def test2(self):
        m = AcquireRelease()
        set_debug(True)

        trace = [
             Acquire(1, 100),
             Acquire(1, 200),
             Acquire(2, 100),
             Release(1, 100),
             Acquire(2, 300),
             Release(2, 400)
        ]
        m.verify(trace)
        errors_expected = [
            '*** error transition in AcquireRelease:\n    state Acquired(1, 100)\n    event 3 Acquire(task=2, lock=100)\n    P100 acquired again',
            '*** error at end in AcquireRelease:\n    terminates in hot state Acquired(1, 200)',
            '*** error at end in AcquireRelease:\n    terminates in hot state Acquired(2, 300)']
        errors_actual = m.get_all_messages()
        self.assert_equal(errors_expected, errors_actual)


