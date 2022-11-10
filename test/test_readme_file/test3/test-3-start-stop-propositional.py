
import os
from pycontract import *
from enum import Enum
import unittest
import test.utest

DIR = os.path.dirname(__file__) + '/'

"""
Examples in README.md file.
"""


class Input(Enum):
    START = 1
    STOP = 2


class StartStop(Monitor):
    @initial
    class Ready(NextState):
        def transition(self, event):
            match event:
                case Input.START:
                    return self.Running()

    class Running(HotNextState):
        def transition(self, event):
            match event:
                case Input.STOP:
                    return self.Ready()


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test-3-start-stop-propositional.StartStop.test.pu', DIR + 'test-3-start-stop-propositional.StartStop.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = StartStop()
        set_debug(True)
        trace = [
            Input.START,
            Input.STOP,
            Input.START,
            Input.STOP
        ]
        m.verify(trace)
        errors_expected = []
        errors_actual = m.get_all_messages()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)




