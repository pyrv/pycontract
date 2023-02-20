
import os
# import pycontract as pc
from pycontract import Monitor, data, HotState, State, error, visualize, set_debug, AlwaysState, initial
import unittest
import test.utest

DIR = os.path.dirname(__file__) + '/'

"""
Introductory example.
"""

"""
class Commands(Monitor):
    def transition(self, event):
        match event:
            case {'name':'dispatch', 'cmd':c, 'nr':n, 'time': t}:
                return Commands.DoComplete(c, n, t)

    @data
    class DoComplete(HotState):
        cmd: str
        nr: int
        time: int

        def transition(self, event):
            match event:
                case {'name':'fail', 'cmd':self.cmd, 'nr':self.nr}:
                    return error('failed')
                case {'time':t} if t - self.time > 3000:
                    return error('time')
                case {'name':'complete', 'cmd':self.cmd, 'nr':self.nr}:
                    return Commands.Executed(self.nr)

    @data
    class Executed(State):
        nr: int

        def transition(self, event):
            match event:
                case {'name':'complete', 'nr':self.nr}:
                    return error('completion again')
"""


class Commands(Monitor):
    @initial
    class Start(AlwaysState):
        def transition(self, event):
            match event:
                case {'name': 'dispatch', 'cmd': c, 'nr': n, 'time': t}:
                    return Commands.DoComplete(c, n, t)

    @data
    class DoComplete(HotState):
        cmd: str
        nr: int
        time: int

        def transition(self, event):
            match event:
                case {'name':'fail', 'cmd':self.cmd, 'nr':self.nr}:
                    return error('failed')
                case {'time':t} if t - self.time > 3000:
                    return error('time')
                case {'name':'complete', 'cmd':self.cmd, 'nr':self.nr}:
                    return Commands.Executed(self.nr)

    @data
    class Executed(State):
        nr: int

        def transition(self, event):
            match event:
                case {'name':'complete', 'nr':self.nr}:
                    return error('completion again')


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'intro.Commands.test.pu', DIR + 'intro.Commands.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = Commands()
        set_debug(True)

        trace = [
            {'name': 'dispatch', 'cmd': 'TURN', 'nr': 203, 'time': 1000},
            {'name': 'dispatch', 'cmd': 'THRUST', 'nr': 204, 'time': 4000},
            {'name': 'complete', 'cmd': 'TURN', 'nr': 203, 'time': 5000},
            {'name': 'complete', 'cmd': 'THRUST', 'nr': 204, 'time': 6000},
            {'name': 'complete', 'cmd': 'THRUST', 'nr': 204, 'time': 7500},

        ]
        m.verify(trace)
        errors_expected = ["*** error transition in Commands:\n    state DoComplete('TURN', 203, 1000)\n    event 3 {'name': 'complete', 'cmd': 'TURN', 'nr': 203, 'time': 5000}\n    time",
                           "*** error transition in Commands:\n    state Executed(204)\n    event 5 {'name': 'complete', 'cmd': 'THRUST', 'nr': 204, 'time': 7500}\n    completion again"]


        errors_actual = m.get_all_message_texts()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)



