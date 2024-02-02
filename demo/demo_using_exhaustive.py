
from pycontract import *

"""
Requirement:

The dispatch of a TURN command must be followed by an EVR1, EVR2, and EVR3
in any order, all labelled with the TURN command and the same number used
for the dispatch. If the command is completed before the EVRs are observed
it is an error.

Likewise, the dispatch of a THRUST command must be followed by an EVR4, EVR5, and EVR6
in any order, all labelled with the THRUST command and the same number used
for the dispatch. There is no requirement wrt. completion. Instead, if a CANCEL
is observed the check is cancelled.
"""

class Commands(Monitor):
    def transition(self, event):
        match event:
            case {'op': 'DISPATCH', 'cmd': 'TURN', 'nr': nr}:
                return self.DoCompleteTurn(nr)
            case {'op': 'DISPATCH', 'cmd': 'THRUST', 'nr': nr}:
                return self.DoCompleteThrust(nr)

    @data
    class DoCompleteTurn(HotState):
        nr: str

        @exhaustive
        def transition(self, event):
            match event:
                case {'op': 'EVR1', 'cmd': 'TURN', 'nr': self.nr}:
                    return done()
                case {'op': 'EVR2', 'cmd': 'TURN', 'nr': self.nr}:
                    return done()
                case {'op': 'EVR3', 'cmd': 'TURN', 'nr': self.nr}:
                    return done()
                case {'op': 'COMPLETE', 'cmd': 'TURN', 'nr': self.nr}:
                    return error('TURN Completes too early')

    @data
    class DoCompleteThrust(HotState):
        nr: str

        @exhaustive
        def transition(self, event):
            match event:
                case {'op': 'EVR4', 'cmd': 'THRUST', 'nr': self.nr}:
                    return done()
                case {'op': 'EVR5', 'cmd': 'THRUST', 'nr': self.nr}:
                    return done()
                case {'op': 'EVR6', 'cmd': 'THRUST', 'nr': self.nr}:
                    return done()
                case {'op': 'WARNING', 'cmd': 'THRUST', 'nr': self.nr}:
                    return ok


if __name__ == '__main__':
    set_debug(False)
    m = Commands()
    with CSVSource('evrs_with_header.csv') as csv_reader:
        for event in csv_reader:
            if event is not None:
                m.eval(event)
        m.end()



