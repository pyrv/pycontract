from typing import Dict

from pycontract import *
import unittest
import test.utest

# Property AcquireRelease:
# A task acquiring a lock should eventually release it.
# At most one task can acquire a lock at a time. Locks
# are not re-entrant (a task cannot take the same lock
# more than once before releasing it).
#
# This time using dictionaries as events.

"""
Events:
"""


@data
class LockEvent(Event):
    name: str
    dict: Dict[str, object]


"""
Monitor:
"""


class AcquireRelease(Monitor):
    @initial
    class Start(AlwaysState):
        def transition(self, event):
            match event:
                case LockEvent('acquire', {'task': task, 'lock': lock}):
                    return self.Acquired(task, lock)

    @data
    class Acquired(HotState):
        task: int
        lock: int

        def transition(self, event):
            match event:
                case LockEvent('acquire', {'lock': self.lock}):
                    return error(f'P{self.lock} acquired again')
                case LockEvent('release', {'task': self.task, 'lock': self.lock}):
                    return ok


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files('test2.AcquireRelease.test.pu', 'test2.AcquireRelease.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = AcquireRelease()
        set_debug(True)

        trace = [
            LockEvent('acquire', {'task': 1, 'lock': 100}),
            LockEvent('acquire', {'task': 1, 'lock': 200}),
            LockEvent('release', {'task': 1, 'lock': 200}),
            LockEvent('release', {'task': 1, 'lock': 100}),
        ]
        m.verify(trace)

        errors_expected = []
        errors_actual = m.get_all_errors()
        self.assert_equal(errors_expected, errors_actual)

    def test2(self):
        m = AcquireRelease()
        set_debug(True)

        trace = [
            LockEvent('acquire', {'task': 1, 'lock': 100}),
            LockEvent('acquire', {'task': 1, 'lock': 200}),
            LockEvent('acquire', {'task': 2, 'lock': 100}),
            LockEvent('release', {'task': 1, 'lock': 200}),
            LockEvent('acquire', {'task': 2, 'lock': 300}),
        ]
        m.verify(trace)

        errors_expected = [
            "*** error transition in AcquireRelease:\n    state Acquired(1, 100)\n    event 3 LockEvent(name='acquire', dict={'task': 2, 'lock': 100})\n    P100 acquired again",
            '*** error at end in AcquireRelease:\n    terminates in hot state Acquired(2, 100)',
            '*** error at end in AcquireRelease:\n    terminates in hot state Acquired(2, 300)']

        errors_actual = m.get_all_errors()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)


if __name__ == '__main__':
    unittest.main()
