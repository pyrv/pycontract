
from pycontract import *
import unittest
import test.utest

DIR = os.path.dirname(__file__) + '/'

"""
Examples in README.md file.
"""


class Obligations1(Monitor):
    def transition(self, event):
        match event:
            case {'name': 'dispatch', 'cmd': cmd}:
                return [
                    self.DoComplete(cmd),
                    self.DoLog(cmd),
                    self.DoClean(cmd)
                    ]

    @data
    class DoComplete(HotState):
        cmd: str

        def transition(self, event):
            match event:
                case {'name': 'complete', 'cmd': self.cmd}:
                    return ok

    @data
    class DoLog(HotState):
        cmd: str

        def transition(self, event):
            match event:
                case {'name': 'log', 'cmd': self.cmd}:
                    return ok

    @data
    class DoClean(HotState):
        cmd: str

        def transition(self, event):
            match event:
                case {'name': 'clean', 'cmd': self.cmd}:
                    return ok


class Obligations2(Monitor):
    def transition(self, event):
        match event:
            case {'name': 'dispatch', 'cmd': cmd}:
                return self.DoCompleteLogClean(cmd)

    @data
    class DoCompleteLogClean(HotState):
        cmd: str

        @exhaustive
        def transition(self, event):
            match event:
                case {'name': 'complete', 'cmd': self.cmd}:
                    return done()
                case {'name': 'log', 'cmd': self.cmd}:
                    return done()
                case {'name': 'clean', 'cmd': self.cmd}:
                    return done()


class Obligations3(Monitor):
    def transition(self, event):
        match event:
            case {'name': 'dispatch', 'cmd': cmd}:
                return self.DoCompleteLogClean(cmd)

    @data
    class DoCompleteLogClean(HotState):
        cmd: str

        @exhaustive
        def transition(self, event):
            match event:
                case {'name': 'complete', 'cmd': self.cmd}:
                    return done()
                case {'name': 'log', 'cmd': self.cmd}:
                    return done()
                case {'name': 'clean', 'cmd': self.cmd}:
                    return done()
                case {'name': 'cancel', 'cmd': self.cmd}:
                    return ok
                case {'name': 'fail', 'cmd': self.cmd}:
                    return error()


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test-10-exhaustive.Obligations1.test.pu', DIR + 'test-10-exhaustive.Obligations1.pu')
        self.assert_equal_files(DIR + 'test-10-exhaustive.Obligations2.test.pu', DIR + 'test-10-exhaustive.Obligations2.pu')
        self.assert_equal_files(DIR + 'test-10-exhaustive.Obligations3.test.pu', DIR + 'test-10-exhaustive.Obligations3.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = Obligations1()
        set_debug(True)

        trace = [
            {'name': 'dispatch', 'cmd': 'TURN'},
            {'name': 'complete', 'cmd': 'TURN'},
            # {'name': 'log', 'cmd': 'TURN'},
            {'name': 'cancel', 'cmd': 'TURN'},
            # {'name': 'fail', 'cmd': 'TURN'},
            {'name': 'clean', 'cmd': 'TURN'},
        ]
        m.verify(trace)
        errors_expected = [
            "*** error at end in Obligations1:\n    terminates in hot state DoLog('TURN')"
        ]
        errors_actual = m.get_all_messages()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)

    def test2(self):
        m = Obligations2()
        set_debug(True)

        trace = [
            {'name': 'dispatch', 'cmd': 'TURN'},
            {'name': 'complete', 'cmd': 'TURN'},
            # {'name': 'log', 'cmd': 'TURN'},
            {'name': 'clean', 'cmd': 'TURN'},
        ]
        m.verify(trace)
        errors_expected = [
            "*** error at end in Obligations2:\n    terminates in hot state DoCompleteLogClean('TURN')\n    Cases not matched that lead to calls of done() :\n      line 64 : case {'name': 'log', 'cmd': self.cmd}"
        ]
        errors_actual = m.get_all_messages()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)

    def test3(self):
        m = Obligations3()
        set_debug(True)

        trace = [
            {'name': 'dispatch', 'cmd': 'TURN'},
            {'name': 'complete', 'cmd': 'TURN'},
            {'name': 'log', 'cmd': 'TURN'},
            {'name': 'fail', 'cmd': 'TURN'},
            {'name': 'clean', 'cmd': 'TURN'},
        ]
        m.verify(trace)
        errors_expected = [
                "*** error transition in Obligations3:\n    state DoCompleteLogClean('TURN')\n    Cases not matched that lead to calls of done() :\n      line 87 : case {'name': 'clean', 'cmd': self.cmd}\n    event 4 {'name': 'fail', 'cmd': 'TURN'}\n    "
            ]
        errors_actual = m.get_all_messages()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)


