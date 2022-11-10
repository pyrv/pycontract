
import os
from pycontract import *
import unittest
import test.utest

DIR = os.path.dirname(__file__) + '/'

"""
Examples in README.md file.
"""


class CommandExecution(Monitor):
    def transition(self, event):
        match event:
            case {'name': 'dispatch', 'cmd': cmd, 'nr': nr, 'time': time}:
                return [
                    self.DoComplete(cmd, nr, time),
                    self.Dispatched(nr)
                    ]

    @data
    class DoComplete(HotState):
        cmd: str
        nr: int
        time: int

        def transition(self, event):
            match event:
                case {'name': 'complete', 'cmd': self.cmd, 'nr': self.nr, 'time': time}:
                    if time - self.time > 3000:
                        return error(f'command execution beyond 3 seconds')
                    else:
                        return self.Executed(self.nr)

    @data
    class Executed(State):
        nr: int

        def transition(self, event):
            match event:
                case {'name': 'complete', 'nr': self.nr}:
                    return error(f'command nr {self.nr} re-executed')

    @data
    class Dispatched(State):
        nr: int

        def transition(self, event):
            match event:
                case {'name': 'dispatch', 'nr': self.nr}:
                    return error(f'command nr {self.nr} continues')


class SmarterCommandExecution(Monitor):
    def transition(self, event):
        match event:
            case {'name': 'dispatch', 'cmd': cmd, 'nr': nr, 'time': time}:
                return [
                    self.DoComplete(cmd, nr, time),
                    self.Dispatched(nr)
                    ]

    @data
    class DoComplete(HotState):
        cmd: str
        nr: int
        time: int

        def transition(self, event):
            match event:
                case {'time': time} if time - self.time > 3000:
                    return error(f'command execution beyond 3 seconds')
                case {'name': 'complete', 'cmd': self.cmd, 'nr': self.nr, 'time': time}:
                    return self.Executed(self.nr)

    @data
    class Executed(State):
        nr: int

        def transition(self, event):
            match event:
                case {'name': 'complete', 'nr': self.nr}:
                    return error(f'command nr {self.nr} re-executed')

    @data
    class Dispatched(State):
        nr: int

        def transition(self, event):
            match event:
                case {'name': 'dispatch', 'nr': self.nr}:
                    return error(f'command nr {self.nr} continues')


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test-4-commands.CommandExecution.test.pu', DIR + 'test-4-commands.CommandExecution.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = SmarterCommandExecution()
        set_debug(True)

        trace = [
            {'name': 'dispatch', 'cmd': 'TURN', 'nr': 203, 'time': 1000},
            {'name': 'dispatch', 'cmd': 'THRUST', 'nr': 204, 'time': 4000},
            {'name': 'complete', 'cmd': 'TURN', 'nr': 203, 'time': 5000},
            {'name': 'complete', 'cmd': 'THRUST', 'nr': 204, 'time': 6000},
            {'name': 'complete', 'cmd': 'THRUST', 'nr': 204, 'time': 7500},

        ]
        m.verify(trace)
        errors_expected = [
            "*** error transition in SmarterCommandExecution:\n    state DoComplete('TURN', 203, 1000)\n    event 3 {'name': 'complete', 'cmd': 'TURN', 'nr': 203, 'time': 5000}\n    command execution beyond 3 seconds",
            "*** error transition in SmarterCommandExecution:\n    state Executed(204)\n    event 5 {'name': 'complete', 'cmd': 'THRUST', 'nr': 204, 'time': 7500}\n    command nr 204 re-executed"]
        errors_actual = m.get_all_messages()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)



