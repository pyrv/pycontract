import pycontract as pyc

"""
Using a Count object.
"""

@pyc.data
class Acquire:
    thread: str
    lock: int


@pyc.data
class Release:
    thread: str
    lock: int

class Count:
    def __init__(self):
        self.count: int = 0

    def __str__(self):
        return f'Count({self.count})'

    def incr(self):
        self.count += 1

    def decr(self):
        self.count -= 1

    def read(self) -> int:
        return self.count

class CountingAcquireRelease(pyc.Monitor):
    def __init__(self):
        super().__init__()
        self.count = Count()

    def transition(self, event):
        print(f"--- Count inside Always() state: {self.count}")
        match event:
            case Acquire(thread, lock):
                if self.count.read() < 3:
                    self.count.incr()
                    return self.Locked(thread, lock)
                else:
                    return pyc.error("*** more that 3 locks acquired")

    @pyc.data
    class Locked(pyc.HotState):
        thread: str
        lock: int

        def transition(self, event):
            print(f"--- Count inside Locked({self.thread}, {self.lock}) state: {self.count}")
            match event:
                case Acquire(_, self.lock):
                    return pyc.error("lock re-acquired")
                case Release(self.thread, self.lock):
                    self.count.decr()
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
