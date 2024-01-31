
import os
from pycontract import *
import unittest
import test.utest

DIR = os.path.dirname(__file__) + '/'

"""
Examples in README.md file.
"""


@data
class Event:
    time: int


@data
class Dispatch(Event):
    cmd: str


@data
class Complete(Event):
    cmd: str


class CommandExecution(Monitor):
    """
    Verifies that commands that are dispatched also completed within 3 seconds.
    """

    @initial
    class Always(AlwaysState):
        def transition(self, event):
            match event:
                case Dispatch(time, cmd):
                    return self.DoComplete(time, cmd)

    @data
    class DoComplete(HotState):
        time: int
        cmd: str

        def transition(self, event):
            match event:
                case Complete(time, self.cmd):
                    if time - self.time <= 3000:
                        return ok
                    else:
                        return error(f'{self.cmd} completion takes too long')


def converter(line: list[str]) -> Event:
    match line[0]:
        case "CMD_DISPATCH":
            return Dispatch(time=int(line[1]), cmd=line[2])
        case "CMD_COMPLETE":
            return Complete(time=int(line[1]), cmd=line[2])


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        self.assert_equal_files(DIR + 'test-9-csv.CommandExecution.test.pu', DIR + 'test-9-csv.CommandExecution.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = CommandExecution()
        set_debug(True)
        csv_reader = CSVReader('commands.csv', converter)
        for event in csv_reader:
            if event is not None:
                m.eval(event)
        m.end()
        csv_reader.close()
        errors_expected = [
            "*** error transition in CommandExecution:\n    state DoComplete(1000, 'TURN')\n    event 3 Complete(time=5000, cmd='TURN')\n    TURN completion takes too long"]
        errors_actual = m.get_all_message_texts()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)









