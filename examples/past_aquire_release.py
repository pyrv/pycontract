import pycontract as pyc

"""
===========
Bug report:
===========
The first is the PastAquireRelease monitor: https://github.com/pyrv/pycontract?tab=readme-ov-file#the-monitor-2
When trying to call “case Release(thread, lock) if not self.Locked(thread, lock):”, I am getting the following error:
RecursionError: maximum recursion depth exceeded
I am looking to use this feature to create a monitor that should produce an error if the rover has currently 
preheated (ie a Preheat state already exists) and then tries to preheat again
"""

@pyc.data
class Acquire:
    thread: str
    lock: int


@pyc.data
class Release:
    thread: str
    lock: int


class PastAcquireRelease(pyc.Monitor):
    def transition(self, event):
        match event:
            case Acquire(thread, lock):
                return self.Locked(thread, lock)
            case Release(thread, lock) if not self.Locked(thread, lock):  # <--- test on state
                return pyc.error(f"thread {thread} releases un-acquired lock {lock}")

    @pyc.data
    class Locked(pyc.HotState):
        thread: str
        lock: int

        def transition(self, event):  # same as before
            match event:
                case Acquire(_, self.lock):
                    return pyc.error("lock re-acquired")
                case Release(self.thread, self.lock):
                    return pyc.ok


if __name__ == "__main__":
    pyc.set_debug(True)
    m = PastAcquireRelease()

    # trace = [Acquire("wheel", 12)]  # Should produce failure
    # trace = [Release("wheel", 12)]  # Should produce failure
    trace = [Acquire("wheel", 12), Release("wheel", 12)]  # Should produce success

    print("Verifying trace:")
    m.verify(trace)
