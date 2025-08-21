import unittest
from pycontract import *

@data
class Timed(Event):
    time: int

@data
class Acquire(Timed):
    thread: str
    lock: int

@data
class Release(Timed):
    thread: str
    lock: int

class ReleaseAfterAcquire(Monitor):
    """
    Enforce: every Acquire must followed a Release.
    """

    WINDOW_SIZE = 3  # enable buffered processing

    def window_key(self, e):
        """
        Sort by time; break ties so Acquire is processed before Release.
        """
        order = {Acquire: 0, Release: 1}
        return (e.time, order.get(type(e), 99))

    def transition(self, event):
        match event:
            case Acquire(thread, lock):
                return self.Acquired(thread, lock)

    @data
    class Acquired(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Release(self.thread, self.lock):
                    return ok

class TestReleaseAfterAcquire(unittest.TestCase):
    def test1(self):
        m = ReleaseAfterAcquire()
        trace = [
            Acquire(time=10, thread=1, lock=10),
            Release(time=10, thread=1, lock=10)
        ]
        m.verify(trace)
        self.assertFalse(m.errors_found(), f"Unexpected errors: {m.get_all_message_texts()}")

    def test2(self):
        m = ReleaseAfterAcquire()
        trace = [
            Release(time=10, thread=1, lock=10),
            Acquire(time=10, thread=1, lock=10)
        ]
        m.verify(trace)
        self.assertFalse(m.errors_found(), f"Unexpected errors: {m.get_all_message_texts()}")

    def test3(self):
        m = ReleaseAfterAcquire()
        trace = [
            Release(time=10, thread=1, lock=10),
            Acquire(time=11, thread=1, lock=10)
        ]
        m.verify(trace)
        self.assertTrue(m.errors_found(), f"Unexpected no errors")

if __name__ == "__main__":
    unittest.main()
