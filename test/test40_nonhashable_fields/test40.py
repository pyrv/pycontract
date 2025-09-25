import pycontract as pc

@pc.data
class M1(pc.Monitor):
    x: dict

    def transition(self, event):
        pass

@pc.data
class M2(pc.Monitor):
    x: dict

    def transition(self, event):
        pass

class M(pc.Monitor):
    def __init__(self):
        super().__init__()
        self.monitor_this(M1({'a':1}), M2({'a':1}))

if __name__ == "__main__":
    m = M()
    pc.visualize(__file__)


