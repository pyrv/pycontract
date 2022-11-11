
import os
from pycontract import *
import unittest
import test.utest

DIR = os.path.dirname(__file__) + '/'

"""
Examples in README.md file.
"""


class Monitor1(Monitor):
    def transition(self, event):
        if event == 1:
            self.report_error('event 1 submitted')


class Monitor2(Monitor):
    def transition(self, event):
        if event == 2:
            self.report_error('event 2 submitted')


class Monitors(Monitor):
    def __init__(self):
        super().__init__()
        self.monitor_this(Monitor1(), Monitor2())


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test-7-multiple-monitors.Monitor1.test.pu', DIR + 'test-7-multiple-monitors.Monitor1.test.pu')
        self.assert_equal_files(DIR + 'test-7-multiple-monitors.Monitor2.test.pu', DIR + 'test-7-multiple-monitors.Monitor2.test.pu')
        self.assert_equal_files(DIR + 'test-7-multiple-monitors.Monitors.test.pu', DIR + 'test-7-multiple-monitors.Monitors.test.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = Monitors()
        set_debug(True)
        trace = [3, 4, 5, 1, 2]
        m.verify(trace)
        errors_expected = [
            '*** error in Monitor1:\n    event 1 submitted',
            '*** error in Monitor2:\n    event 2 submitted']
        errors_actual = m.get_all_message_texts()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)



