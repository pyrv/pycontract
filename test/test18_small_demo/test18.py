
import pycontract as pc


"""
Requirements:

A command is identified by a command name and a number.

1) A command dispatch must eventually succeed without a failure in between,
   unless it is cancelled after dispatch.
2) A command that succeeds must not succeed again.
"""


class Col:
    ID = 'ID'
    CMD = 'CMD'
    NR = 'NR'


class M(pc.Monitor):
    def transition(self, event):
        match event:
            case {Col.ID: 'dispatch', Col.CMD: c, Col.NR: n}:
                return self.Succeed(c, n)

    @pc.data
    class Succeed(pc.HotState):
        cmd: str
        nr: str

        def transition(self, event):
            match event:
                case {Col.ID: 'cancel', Col.CMD: self.cmd, Col.NR: self.nr}:
                    return pc.ok
                case {Col.ID: 'fail', Col.CMD: self.cmd, Col.NR: self.nr}:
                    return pc.error(f'command {self.cmd} nr {self.nr} failed')
                case {Col.ID: 'succeed', Col.CMD: self.cmd, Col.NR: self.nr}:
                    return M.DontSucceedAgain(self.cmd, self.nr)

    @pc.data
    class DontSucceedAgain(pc.State):
        cmd: str
        nr: str

        def transition(self, event):
            match event:
                case {Col.ID: 'succeed', Col.CMD: self.cmd, Col.NR: self.nr}:
                    return pc.error(f'command {self.cmd} nr {self.nr} executed twice')


if __name__ == '__main__':
    trace = [
        {'ID': 'dispatch', 'CMD': 'A', 'NR': 1, 'TIME': 1000},
        {'ID': 'dispatch', 'CMD': 'B', 'NR': 2, 'TIME': 2000},
        {'ID': 'dispatch', 'CMD': 'C', 'NR': 3, 'TIME': 3000},
        {'ID': 'dispatch', 'CMD': 'D', 'NR': 4, 'TIME': 4000},
        {'ID': 'cancel'  , 'CMD': 'A', 'NR': 1, 'TIME': 5000},
        {'ID': 'fail'    , 'CMD': 'B', 'NR': 2, 'TIME': 6000},  # failure of B,2
        {'ID': 'succeed' , 'CMD': 'C', 'NR': 3, 'TIME': 7000},
        {'ID': 'succeed',  'CMD': 'C', 'NR': 3, 'TIME': 8000},  # double success of C,3
        {'ID': 'succeed',  'CMD': 'E', 'NR': 4, 'TIME': 9000},  # success of E,4 that has not been dispatched
        # missing success of command A,1
    ]
    m = M()
    pc.set_debug(True)
    m.verify(trace)







"""
3) A command must succeed if it has not been dispatched.

            case {Col.ID: 'succeed', Col.CMD: c, Col.NR: nr} if not M.Succeed(c, nr):
                return pc.error(f'command {c} nr {nr} succeeds without a dispatch')
"""