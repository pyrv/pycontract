
import os
from pycontract import *
import unittest
import test.utest

DIR = os.path.dirname(__file__) + '/'

"""
Examples in README.md file.
"""


@data
class Start(Event):
    task: int


@data
class Stop(Event):
    task: int


class StartStop(Monitor):
    @initial
    class Ready(NextState):
        def transition(self, event):
            match event:
                case Start(task):
                    return self.Running(task)

    @data
    class Running(HotNextState):
        task: int

        def transition(self, event):
            match event:
                case Stop(self.task):
                    return self.Ready()


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test-2-start-sto.StartStop.test.pu', DIR + 'test-2-start-sto.StartStop.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = StartStop()
        set_debug(True)
        trace = [
            Start(1),
            Stop(1),
            Start(2),
            Stop(2)
        ]
        m.verify(trace)
        errors_expected = []
        errors_actual = m.get_all_message_texts()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)



