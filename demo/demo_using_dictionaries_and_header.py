
from pycontract import *


class Commands(Monitor):
    def transition(self, event):
        match event:
            case {'op': 'DISPATCH', 'time': time, 'cmd': cmd, 'nr': nr}:
                return self.DoComplete(int(time), cmd, nr)

    @data
    class DoComplete(HotState):
        time: int
        cmd: str
        nr: int

        def transition(self, event):
            match event:
                case {'op': 'COMPLETE', 'time': time, 'cmd': self.cmd, 'nr': self.nr}:
                    if int(time) - self.time <= 3000:
                        return Commands.Completed(self.cmd, self.nr)
                    else:
                        return error(f'{self.cmd} {self.nr} completion takes too long')
                case {'op': 'DISPATCH', 'cmd': self.cmd, 'nr': self.nr}:
                    return error(f'{self.cmd} {self.nr} dispatched more than once')

    @data
    class Completed(State):
        cmd : str
        nr: int

        def transition(self, event):
            match event:
                case {'op': 'COMPLETE', 'cmd': self.cmd, 'nr': self.nr}:
                    return error(f'{self.cmd} already completed')


if __name__ == '__main__':
    m = Commands()
    with CSVSource('commands_with_header.csv') as csv_reader:
        for event in csv_reader:
            if event is not None:
                m.eval(event)
        m.end()



