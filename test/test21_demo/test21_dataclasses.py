
from pycontract import *


@data
class Event:
    time: int


@data
class Dispatch(Event):
    cmd: str
    nr: int


@data
class Complete(Event):
    cmd: str
    nr: int


class Commands(Monitor):
    def transition(self, event):
        match event:
            case Dispatch(time, cmd, nr):
                return self.DoComplete(time, cmd, nr)

    @data
    class DoComplete(HotState):
        time: int
        cmd: str
        nr: int

        def transition(self, event):
            match event:
                case Complete(time, self.cmd, self.nr):
                    if time - self.time <= 3000:
                        return Commands.Completed(self.cmd, self.nr)
                    else:
                        return error(f'{self.cmd} {self.nr} completion takes too long')
                case Dispatch(time, self.cmd, self.nr):
                    return error(f'{self.cmd} {self.nr} dispatched more than once')

    @data
    class Completed(State):
        cmd : str
        nr: int

        def transition(self, event):
            match event:
                case Complete(_, self.cmd, self.nr):
                    return error(f'{self.cmd} already completed')


def converter(line: list[str]) -> Event:
    match line[0]:
        case "DISPATCH":
            return Dispatch(time=int(line[1]), cmd=line[2], nr=line[3])
        case "COMPLETE":
            return Complete(time=int(line[1]), cmd=line[2], nr=line[3])


if __name__ == '__main__':
    m = Commands()
    csv_reader = CSVReader('commands.csv', converter)
    for event in csv_reader:
        if event is not None:
            m.eval(event)
    m.end()
    csv_reader.close()


