import unittest
from pycontract import *

# ----------------------------
# Events
# ----------------------------

@data
class AStart:
    time: int

@data
class AEnd:
    time: int

@data
class BStart:
    time: int

@data
class BEnd:
    time: int


# ----------------------------
# Monitor
# ----------------------------

class BWithinA(Monitor):
    """
    Enforce:
      - B occurs fully within A
      - A cannot start twice in a row (no AStart while A open)
      - A cannot end if it wasn't started
      - B cannot end if it wasn't started

    Ordering:
      AStart < BStart < BEnd < AEnd
    """

    WINDOW_SIZE = 3  # enable buffering

    def window_key(self, e):
        order = {AStart: 0, BStart: 1, BEnd: 2, AEnd: 3}
        return (e.time, order.get(type(e), 99))

    def transition(self, e):
        match e:
            case AStart():
                return self.AOpen()

            case AEnd():
                if not self.exists(BWithinA.AOpen):
                    return error("AEnd without prior AStart")

            case BStart():
                if not self.exists(BWithinA.AOpen):
                    return error("BStart occurred outside of A")
                return self.BOpen()

            case BEnd():
                if not self.exists(BWithinA.BOpen):
                    return error("BEnd without prior BStart")

    @data
    class AOpen(HotState):
        def transition(self, e):
            match e:
                case AStart():
                    return error("AStart while A already open")
                case AEnd():
                    return ok

    @data
    class BOpen(HotState):
        def transition(self, e):
            match e:
                case AEnd():
                    return error("AEnd encountered while B is still open")
                case BEnd():
                    return ok

# ----------------------------
# Tests
# ----------------------------

class TestBWithinA(unittest.TestCase):
    def test_ties_resolved_by_buffering(self):
        """
        Arrival order adversarial, times tie; buffer enforces:
          AStart(10) < BStart(10) < BEnd(20) < AEnd(20)
        """
        m = BWithinA()
        incoming = [
            BStart(time=10),  # arrives first, but should be processed after AStart(10)
            AStart(time=10),
            AEnd(time=20),    # arrives before BEnd(20), but must be processed last
            BEnd(time=20),
        ]
        for e in incoming:
            m.eval(e)
        m.end()
        self.assertFalse(m.errors_found(), f"Unexpected errors: {m.get_all_message_texts()}")

    def test_b_starts_outside_a(self):
        m = BWithinA()
        incoming = [BStart(time=5), AStart(time=10), BEnd(time=15), AEnd(time=20)]
        for e in incoming:
            m.eval(e)
        m.end()
        msgs = m.get_all_message_texts()
        self.assertTrue(any("BStart occurred outside of A" in msg for msg in msgs), msgs)

    def test_a_ends_while_b_open(self):
        m = BWithinA()
        incoming = [AStart(time=10), BStart(time=12), AEnd(time=16), BEnd(time=17)]
        for e in incoming:
            m.eval(e)
        m.end()
        msgs = m.get_all_message_texts()
        self.assertTrue(any("AEnd encountered while B is still open" in msg for msg in msgs), msgs)

    def test_a_cannot_start_twice(self):
        m = BWithinA()
        incoming = [AStart(time=1), AStart(time=2)]  # second start invalid
        for e in incoming:
            m.eval(e)
        m.end()
        msgs = m.get_all_message_texts()
        self.assertTrue(any("AStart while A already open" in msg for msg in msgs), msgs)

    def test_a_end_without_start(self):
        m = BWithinA()
        incoming = [AEnd(time=5)]
        for e in incoming:
            m.eval(e)
        m.end()
        msgs = m.get_all_message_texts()
        self.assertTrue(any("AEnd without prior AStart" in msg for msg in msgs), msgs)

    def test_b_end_without_start(self):
        m = BWithinA()
        incoming = [AStart(time=1), BEnd(time=2), AEnd(time=3)]  # BEnd invalid
        for e in incoming:
            m.eval(e)
        m.end()
        msgs = m.get_all_message_texts()
        self.assertTrue(any("BEnd without prior BStart" in msg for msg in msgs), msgs)

    def test_happy_path_no_ties(self):
        m = BWithinA()
        incoming = [AStart(time=1), BStart(time=2), BEnd(time=3), AEnd(time=4)]
        for e in incoming:
            m.eval(e)
        m.end()
        self.assertFalse(m.errors_found(), f"Unexpected errors: {m.get_all_message_texts()}")


if __name__ == "__main__":
    unittest.main()
