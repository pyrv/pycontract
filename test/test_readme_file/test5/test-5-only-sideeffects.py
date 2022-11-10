
import os
from pycontract import *
import unittest
import test.utest

DIR = os.path.dirname(__file__) + '/'

"""
Examples in README.md file.
"""


class CommandExecution(Monitor):
    def __init__(self):
        super().__init__()
        self.count: int = 0

    def transition(self, event):
        match event:
            case {'name': 'dispatch'}:
                self.count += 1
            case {'name': 'complete'}:
                self.count -= 1
                if self.count < 0:
                    self.report_error('more completions than dispatches')


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test-5-only-sideeffects.CommandExecution.test.pu', DIR + 'test-5-only-sideeffects.CommandExecution.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = CommandExecution()
        set_debug(True)
        trace = [
            {'name': 'dispatch', 'cmd': 'TURN', 'nr': 203, 'time': 1000},
            {'name': 'dispatch', 'cmd': 'THRUST', 'nr': 204, 'time': 4000},
            {'name': 'complete', 'cmd': 'TURN', 'nr': 203, 'time': 5000},
            {'name': 'complete', 'cmd': 'THRUST', 'nr': 204, 'time': 6000},
            {'name': 'complete', 'cmd': 'THRUST', 'nr': 204, 'time': 7500},

        ]
        m.verify(trace)
        errors_expected = ['*** error in CommandExecution:\n    more completions than dispatches']

        errors_actual = m.get_all_messages()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)







