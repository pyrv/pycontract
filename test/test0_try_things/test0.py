
from pycontract import *

class MyMonitor(Monitor):
    @initial
    class Unknown(State):
        def transition(self, event):
            match event:
                case 1:
                    return self.One()
                case 2:
                    pass

    class One(State):
        pass


if __name__ == '__main__':
    visualize(__file__, True)
    m = MyMonitor()
    set_debug(True)
    trace = [2, 1]
    m.verify(trace)

