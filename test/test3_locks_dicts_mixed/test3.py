from typing import Dict

import os
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
# This time using dictionaries as events, but with subclasses for
# each kind of event.

"""
Events:
"""


@data
class Message(Event):
    data: Dict[str, object]


class Acquire(Message):
    pass


class Release(Message):
    pass


"""
Monitor:
"""


class AcquireRelease(Monitor):
    @initial
    class Start(AlwaysState):
        def transition(self, event):
            match event:
                case Acquire({'task': task, 'lock': lock}):
                    return self.Acquired(task, lock)

    @data
    class Acquired(HotState):
        task: int
        lock: int

        def transition(self, event):
            match event:
                case Acquire({'lock': self.lock}):
                    return error(f'P{self.lock} acquired again')
                case Release({'task': self.task, 'lock': self.lock}):
                    return ok


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test3.AcquireRelease.test.pu', DIR + 'test3.AcquireRelease.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = AcquireRelease()
        set_debug(True)

        trace = [
            Acquire({'task': 1, 'lock': 100}),
            Acquire({'task': 1, 'lock': 200}),
            Release({'task': 1, 'lock': 200}),
            Release({'task': 1, 'lock': 100}),
        ]
        m.verify(trace)

        errors_expected = []
        errors_actual = m.get_all_message_texts()
        self.assert_equal(errors_expected, errors_actual)

    def test2(self):
        m = AcquireRelease()
        set_debug(True)

        trace = [
            Acquire({'task': 1, 'lock': 100}),
            Acquire({'task': 1, 'lock': 200}),
            Acquire({'task': 2, 'lock': 100}),
            Release({'task': 1, 'lock': 200}),
            Acquire({'task': 2, 'lock': 300}),
        ]
        m.verify(trace)

        errors_expected = [
            "*** error transition in AcquireRelease:\n    state Acquired(1, 100)\n    event 3 Acquire(data={'task': 2, 'lock': 100})\n    P100 acquired again",
            '*** error at end in AcquireRelease:\n    terminates in hot state Acquired(2, 100)',
            '*** error at end in AcquireRelease:\n    terminates in hot state Acquired(2, 300)']

        errors_actual = m.get_all_message_texts()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)


