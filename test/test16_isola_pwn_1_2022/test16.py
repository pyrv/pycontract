from typing import Dict, List

from pycontract import *
import statistics

"""
Example for ISoLA PWN 2022: the command execution example
"""


class Verifier(Monitor):
    def transition(self, event):
        match event:
            case {'kind': 'dispatch', 'cmd': c, 'budget': b, 'time': t}:
                return self.Dispatched(c, float(b), float(t))

    @data
    class Dispatched(HotState):
        cmd: str
        time_budget: float
        time_dispatched: float

        def transition(self, event):
            match event:
                case {'kind': 'success', 'cmd': self.cmd, 'time': time_succeeded}:
                    if time_succeeded - self.time_dispatched <= self.time_budget:
                        return ok
                    else:
                        return error(f'time budget exceeded for cmd {self.cmd}')
                case {'kind': 'failure', 'cmd': self.cmd}:
                    return error(f'command {self.cmd} failed!')


class Analyzer(Monitor):
    durations: Dict[str, List[float]] = {}

    def end(self):
        super().end()
        for (cmd,durs) in self.durations.items():
            print(f'cmd {cmd} : {statistics.mean(durs)}')


    def add_dur(self, cmd: str, dur: float):
        if cmd in self.durations:
            self.durations[cmd].append(dur)
        else:
            self.durations[cmd] = [dur]

    def transition(self, event):
        match event:
            case {'kind': 'dispatch', 'cmd': c, 'budget': b, 'time': t}:
                return self.Dispatched(c, float(b), float(t))

    @data
    class Dispatched(HotState):
        cmd: str
        time_budget: float
        time_dispatched: float

        def transition(self, event):
            match event:
                case {'kind': 'success', 'cmd': self.cmd, 'time': time_succeeded}:
                    dur = time_succeeded - self.time_dispatched
                    print(f'cmd {self.cmd} succeeds, start: {self.time_dispatched}, end: {time_succeeded}, dur: {dur}')
                    self.monitor.add_dur(self.cmd, dur)
                    if time_succeeded - self.time_dispatched <= self.time_budget:
                        return ok
                    else:
                        return error(f'time budget exceeded for cmd {self.cmd}')
                case {'kind': 'failure', 'cmd': self.cmd}:
                    return error(f'command {self.cmd} failed!')


if __name__ == '__main__':
    trace = [
        {'kind': 'dispatch', 'cmd': 1, 'budget': 2000, 'time': 1000},
        {'kind': 'dispatch', 'cmd': 2, 'budget': 1000, 'time': 1500},
        {'kind': 'failure', 'cmd': 1, 'time': 2000},
        {'kind': 'success', 'cmd': 2, 'time': 4000},
        {'kind': 'dispatch', 'cmd': 10, 'budget': 2000, 'time': 5000},
        {'kind': 'dispatch', 'cmd': 11, 'budget': 2000, 'time': 6000},
        {'kind': 'dispatch', 'cmd': 12, 'budget': 2000, 'time': 7000},
        {'kind': 'dispatch', 'cmd': 13, 'budget': 2000, 'time': 8000},
        {'kind': 'dispatch', 'cmd': 14, 'budget': 2000, 'time': 9000},
        {'kind': 'dispatch', 'cmd': 15, 'budget': 2000, 'time': 10000},
        {'kind': 'success', 'cmd': 10, 'time': 11000},
        {'kind': 'success', 'cmd': 11, 'time': 12000},
        {'kind': 'success', 'cmd': 12, 'time': 13000},
        {'kind': 'success', 'cmd': 13, 'time': 14000},
        {'kind': 'success', 'cmd': 14, 'time': 15000},
        {'kind': 'success', 'cmd': 15, 'time': 16000},
    ]
    m = Analyzer()
    m.verify(trace)
