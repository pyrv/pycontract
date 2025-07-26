import pycontract as pyc

"""
===========
BUG report:
===========

The second is the CountingAquireRelease monitor: https://github.com/pyrv/pycontract?tab=readme-ov-file#the-monitor-1
This is an error here where the count variable is not being modified how I expect. In the example I am running, 
I acquire three locks and then release one of them. This means there should be one more lock available, as there 
are two locks being used. I then acquire this third lock. However, there is an error that I have tried to acquire 
more than three locks (it thinks I have acquired four locks), when this is not the case. 
If I print out the count variable from both the Always() state as well as the Locked() state, it is clear that 
they do not agree on what the value of the count variable is as they print two separate values. 
I am looking to use this feature to create a monitor that checks if the rover has reached all the waypoints 
(ie keep track of the number of waypoints reached). 
"""

@pyc.data
class Acquire:
    thread: str
    lock: int


@pyc.data
class Release:
    thread: str
    lock: int


class CountingAcquireRelease(pyc.Monitor):
    def __init__(self):
        super().__init__()
        self.count: int = 0  # <--- variable initialized

    def transition(self, event):
        print(f"Count inside Always() state: {self.count}")
        match event:
            case Acquire(thread, lock):
                if self.count < 3:  # <--- variable tested
                    self.count += 1  # <--- variable incremented
                    return self.Locked(thread, lock)
                else:
                    return pyc.error("more that 3 locks acquired")

    @pyc.data
    class Locked(pyc.HotState):
        thread: str
        lock: int

        def transition(self, event):
            print(f"Count inside Locked({self.thread}, {self.lock}) state: {self.count}")
            match event:
                case Acquire(_, self.lock):
                    return pyc.error("lock re-acquired")
                case Release(self.thread, self.lock):
                    self.count -= 1  # <-- variable decremented. Variable is looked up in monitor
                    return pyc.ok


if __name__ == "__main__":
    pyc.set_debug(True)
    m = CountingAcquireRelease()

    # trace = [
    #     Acquire("wheel", 11),
    #     Acquire("wheel", 12),
    #     Acquire("wheel", 13),
    #     Acquire("wheel", 14),
    # ]  # This should fail
    trace = [
        Acquire("wheel", 11),
        Acquire("wheel", 12),
        Acquire("wheel", 13),
        Release("wheel", 11),
        Acquire("wheel", 14),
    ]  # This should fail due to the hot state, not because of trying to aquire more than three locks

    print("Verifying trace:")
    m.verify(trace)
