from pycontract import *

class Locking(Monitor):
    @initial
    class Always(AlwaysState):
        def transition(self, event):
            match event:
                case Acquire(thread, lock): return self.Locked(thread, lock)
    @data
    class Locked(HotState):
        thread: object
        lock: object
        def transition(self, event):
            match event:
                case Acquire(_, self.lock): return error('lock re-acquired')
                case Release(self.thread, self.lock): return ok