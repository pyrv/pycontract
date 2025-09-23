
"""
Illustrating reactive monitors
"""

from pycontract import *

def submit_message(msg: str):
    print(msg)

@data
class A:
    x: int

@data
class B:
    y: int

class ABMonitor(Monitor):
    def transition(self, event):
        match event:
            case A(x):
                return ABMonitor.WaitForB(x)

    @data
    class WaitForB(State):
        x: int

        def transition(self, event):
            match event:
                case B(y):
                     submit_message(self.x + y)
                     return ok

if __name__ == '__main__':
    m = ABMonitor()
    m.eval(A(1))
    m.eval(B(2))
    m.end()
