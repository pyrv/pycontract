import os
from datetime import datetime
from typing import Optional, List

from pycontract import *
import unittest
import test.utest
import gc
import cProfile
import re
import timeit

DIR = os.path.dirname(__file__) + '/'

"""
Lock acquisition and release.
Reading from CSV file.
"""


@data
class Event:
    time: int


@data
class Acquire(Event):
    lock: str


@data
class Release(Event):
    lock: str


class Failure(Event):
    pass


class AcquireRelease(Monitor):
    """
    Verifies that locks that are acquired are also released.
    """

    def key(self, event) -> Optional[str]:
        match event:
            case Acquire(_, lock):
                return lock
            case Release(_, lock):
                return lock
            case _:
                return None

    @initial
    class Always(AlwaysState):
        def transition(self, event):
            match event:
                case Acquire(_, lock):
                    return self.DoRelease(lock)

    @data
    class DoRelease(HotState):
        lock: str

        def transition(self, event):
            match event:
                case Release(_, self.lock):
                    return ok


def converter(line: List[str]) -> Event:
    match line[0]:
        case "ACQUIRE":
            return Acquire(time=line[2], lock=line[1])
        case "RELEASE":
            return Release(time=line[2], lock=line[1])
        case "BAD":
            return Failure(time=line[1])
        case _:
            return None


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test10.AcquireRelease.test.pu', DIR + 'test10.AcquireRelease.pu')


class Test2(test.utest.Test):
    # class Test1:
    def test1(self):
        m = AcquireRelease()
        set_debug(False)
        csv_reader = CSVReader(DIR + 'lock_file.csv', converter)
        begin_time = datetime.now()
        # counter = 0
        for event in csv_reader:
            # counter += 1
            # if counter % 1000 == 0:
            #     print(f'---------------------> {counter}')
            #     print(m.number_of_states())
            if event:
                m.eval(event)
        m.end()
        print()
        print(f'Execution time: {datetime.now() - begin_time}')
        csv_reader.close()
        errors_expected = [
         "*** error at end in AcquireRelease:\n    terminates in hot state DoRelease('LOCK_408')",
         "*** error at end in AcquireRelease:\n    terminates in hot state DoRelease('LOCK_27')",
         "*** error at end in AcquireRelease:\n    terminates in hot state DoRelease('LOCK_76')",
         "*** error at end in AcquireRelease:\n    terminates in hot state DoRelease('LOCK_149')",
         "*** error at end in AcquireRelease:\n    terminates in hot state DoRelease('LOCK_469')",
         "*** error at end in AcquireRelease:\n    terminates in hot state DoRelease('LOCK_38')",
         "*** error at end in AcquireRelease:\n    terminates in hot state DoRelease('LOCK_2')",
         "*** error at end in AcquireRelease:\n    terminates in hot state DoRelease('LOCK_417')",
         "*** error at end in AcquireRelease:\n    terminates in hot state DoRelease('LOCK_39')",
         "*** error at end in AcquireRelease:\n    terminates in hot state DoRelease('LOCK_403')",
         "*** error at end in AcquireRelease:\n    terminates in hot state DoRelease('LOCK_375')",
         "*** error at end in AcquireRelease:\n    terminates in hot state DoRelease('LOCK_43')"]

        errors_actual = m.get_all_message_texts()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)
