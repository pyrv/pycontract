from pycontract import *

class High(Monitor):
    def transition(self, event):
        print(f'2x + 1 = {event+1}')


class Low(Monitor):
    def __init__(self, high: Monitor):
        super().__init__()
        self.high = high

    def transition(self, event):
        self.high.eval(event * 2)


high = High()
low = Low(high)
low.eval(3)
low.end