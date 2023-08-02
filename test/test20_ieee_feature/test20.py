from typing import Dict

import pycontract as pc
import statistics

"""
Example for IEEE Feature article, 2023.
"""


class Statistics:
    def __init__(self):
        self.durations: Dict[str, float] = {}

    def __str__(self):
        result ='average command durations:\n'
        for cmd in sorted(self.durations.keys()):
            result += f'{cmd}: {statistics.mean(self.durations[cmd]):6.2f}\n'
        return result

    def add(self, cmd: str, time: float):
        if cmd in self.durations:
            self.durations[cmd].append(time)
        else:
            self.durations[cmd] = [time]

    def show(self):
        print(self)

class Commands(pc.Monitor):
    statistics = Statistics()

    def transition(self, event):
        match event:
            case {'name':'dispatch', 'cmd':c, 'time':t}:
                return Commands.DoComplete(c, t)

    @pc.data
    class DoComplete(pc.HotState):
        cmd: str
        time: int

        def transition(self, event):
            match event:
                case {'name':'fail', 'cmd':self.cmd}:
                    return pc.error(f'{self.cmd} failed')
                case {'time':t} if t - self.time > 3000:
                    return pc.error(f'{self.cmd} dispatched at time {self.time} timed out at time {t}')
                case {'name':'complete', 'cmd':self.cmd, 'time': t}:
                    self.monitor.statistics.add(self.cmd, t - self.time)
                    return pc.ok


if __name__ == '__main__':
    pc.set_debug(True)
    pc.visualize(__file__, True)
    m = Commands()

    trace1 = [
        {'name': 'dispatch', 'cmd': 'TURN', 'time': 1000}, # timed out at 5000
        {'name': 'dispatch', 'cmd': 'THRUST', 'time': 4000}, # fails at 5000
        {'name': 'dispatch', 'cmd': 'SEND', 'time': 5000}, # never succeeds
        {'name': 'dispatch', 'cmd': 'CHARGE', 'time': 5000}, # completes
        {'name': 'fail', 'cmd': 'THRUST', 'time': 5000},
        {'name': 'complete', 'cmd': 'CHARGE', 'time': 6000},
    ]

    trace2 = [
        {'name': 'dispatch', 'cmd': 'A', 'time': 1000},
        {'name': 'complete', 'cmd': 'A', 'time': 2000},
        {'name': 'dispatch', 'cmd': 'A', 'time': 3000},
        {'name': 'complete', 'cmd': 'A', 'time': 3500},
        {'name': 'dispatch', 'cmd': 'A', 'time': 4000},
        {'name': 'complete', 'cmd': 'A', 'time': 4800},
        {'name': 'dispatch', 'cmd': 'B', 'time': 5000},
        {'name': 'complete', 'cmd': 'B', 'time': 6000},
        {'name': 'dispatch', 'cmd': 'B', 'time': 6000},
        {'name': 'complete', 'cmd': 'B', 'time': 6700},
        {'name': 'dispatch', 'cmd': 'C', 'time': 7000},
        {'name': 'complete', 'cmd': 'C', 'time': 8100},
    ]

    trace = [
        {'name': 'dispatch', 'cmd': 'TURN', 'time': 1000},
        {'name': 'dispatch', 'cmd': 'THRUST', 'time': 4000},
        {'name': 'complete', 'cmd': 'TURN', 'time': 6000},
        {'name': 'dispatch', 'cmd': 'SEND', 'time': 6000},
        {'name': 'complete', 'cmd': 'SEND', 'time': 7000},
        {'name': 'dispatch', 'cmd': 'SEND', 'time': 7500},
        {'name': 'complete', 'cmd': 'SEND', 'time': 8000},
    ]

    m.verify(trace)
    m.statistics.show()
