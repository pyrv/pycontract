
import os
from typing import List, Dict

from pycontract import *
import unittest
import test.utest
from datetime import datetime

DIR = os.path.dirname(__file__) + '/'

"""
Test example for SAC-SVT 2022.
"""


class M4(Monitor):
    def transition(self, event):
        match event:
            case {'name': 'command', 'cmd': c, 'nr': n, 'kind': "FSW"}:
                return self.Dispatch(c, n)

    @data
    class Dispatch(HotState):
        cmd: str
        nr: str

        def transition(self, event):
            match event:
                case {'name': 'cancel', 'cmd': self.cmd, 'nr': self.nr}:
                    return ok
                case {'name': 'dispatch', 'cmd': self.cmd, 'nr': self.nr}:
                    return self.Succeed(self.cmd, self.nr)

    @data
    class Succeed(HotState):
        cmd: str
        nr: str

        def transition(self, event):
            match event:
                case {'name': 'succeed', 'cmd': self.cmd, 'nr': self.nr}:
                    return self.Close(self.cmd, self.nr)
                case {'name': 'command', 'cmd': self.cmd, 'nr': _, 'kind': "FSW"}:
                    return error(f' command {self.cmd} re-issued')
                case {'name': 'fail', 'cmd': self.cmd, 'nr': self.nr}:
                    return error(f'failure of cmd={self.cmd}, n={self.nr}')

    @data
    class Close(HotState):
        cmd: str
        nr: str

        def transition(self, event):
            match event:
                case {'name': 'succeed', 'cmd': self.cmd, 'nr': self.nr}:
                    return error(f'cmd={self.cmd}, n={self.nr} succeeds more than once')
                case {'name': 'close', 'cmd': self.cmd, 'nr': self.nr}:
                    return ok


def converter(line: List[str]) -> Dict[str,str]:
    match line[0]:
        case "command":
            return {'name': 'command', 'cmd': line[1], 'nr': line[2], 'kind': line[3]}
        case _:
            return {'name': line[0], 'cmd': line[1], 'nr': line[2]}


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)


"""
log-1-12500.csv
log-50-250.csv

log-1-50000.csv
log-5-10000.csv
log-10-5000.csv
log-20-2500.csv

log-1-125000.csv
log-5-25000.csv
"""
file = DIR + 'log-5-25000.csv'


class Test2(test.utest.Test):
    def test1(self):
        m = M4()
        set_debug(False)
        set_debug_progress(1000)
        csv_reader = CSVReader(file, converter)
        begin_time = datetime.now()
        for event in csv_reader:
            if event is not None:
                m.eval(event)
        m.end()
        csv_reader.close()
        print(f'\nExecution time: {datetime.now() - begin_time}\n')



