
from pycontract import *


class Commands(Monitor):
    def transition(self, event):
        match event:
            case {'op': 'DISPATCH', 'time': time, 'cmd': cmd, 'nr': nr}:
                return self.DoComplete(time, cmd, nr)

    @data
    class DoComplete(HotState):
        time: int
        cmd: str
        nr: int

        def transition(self, event):
            match event:
                case {'op': 'COMPLETE', 'time': time, 'cmd': self.cmd, 'nr': self.nr}:
                    if time - self.time <= 3000:
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


def converter(line: list[str]) -> dict:
    return {'op': line[0], 'time': int(line[1]), 'cmd': line[2], 'nr': line[3]}


if __name__ == '__main__':
    m = Commands()
    csv_reader = CSVReader('commands.csv', converter)
    for event in csv_reader:
        if event is not None:
            m.eval(event)
    m.end()
    csv_reader.close()


