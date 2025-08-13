
import os
import pycontract as pc
import test.utest

DIR = os.path.dirname(__file__) + '/'

"""
Examples in README.md file.
"""


@pc.data
class Start(pc.Event):
    task: int


@pc.data
class Stop(pc.Event):
    task: int


class StartStop(pc.Monitor):
    @pc.initial
    class Ready(pc.NextState):
        def transition(self, event):
            match event:
                case Start(task):
                    return self.Running(task)

    @pc.data
    class Running(pc.HotNextState):
        task: int

        def transition(self, event):
            match event:
                case Stop(self.task):
                    return self.Ready()


class Test1(test.utest.Test):
    def test1(self):
        pc.visualize(__file__, True)
        self.assert_equal_files(DIR + 'test_2_start_stop_pc.StartStop.test.pu', DIR + 'test_2_start_stop_pc.StartStop.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = StartStop()
        pc.set_debug(True)
        trace = [
            Start(1),
            Stop(1),
            Start(2),
            Stop(2)
        ]
        m.verify(trace)
        errors_expected = []
        errors_actual = m.get_all_message_texts()
        print(errors_actual)
        self.assert_equal(errors_expected, errors_actual)



