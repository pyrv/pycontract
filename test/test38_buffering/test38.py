import unittest
from pycontract import Monitor, data, initial, AlwaysState, ok, error

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
# Buffered monitor: B within A
# ----------------------------

class AContainsB(Monitor):
    """
    Enforce: B is always within A.
      - AStart < BStart
      - BEnd   < AEnd
    For equal timestamps, enforce the deterministic order:
      AStart < BStart < BEnd < AEnd
    """
    WINDOW_SIZE = 3  # opt-in buffering window

    def __init__(self):
        super().__init__()
        # Track whether we're inside A, and whether a B is open
        self.a_depth = 0      # allow nesting; 0 means "outside A"
        self.b_open = 0       # how many B segments currently open

    def window_key(self, e):
        order = {AStart: 0, BStart: 1, BEnd: 2, AEnd: 3}
        return (e.time, order.get(type(e), 99))

    @initial
    class Always(AlwaysState):
        def transition(self, e):
            m = self.monitor  # convenience

            match e:
                case AStart(_):
                    m.a_depth += 1
                    return ok

                case AEnd(_):
                    # B must have ended before A ends
                    if m.b_open > 0:
                        return error("AEnd encountered while B is still open")
                    if m.a_depth == 0:
                        return error("AEnd without prior AStart")
                    m.a_depth -= 1
                    return ok

                case BStart(_):
                    # B must start within A
                    if m.a_depth == 0:
                        return error("BStart occurred outside of A")
                    m.b_open += 1
                    return ok

                case BEnd(_):
                    if m.b_open == 0:
                        return error("BEnd without prior BStart")
                    m.b_open -= 1
                    return ok

            # Irrelevant events leave us in the same state
            return None


# ----------------------------
# Tests
# ----------------------------
class TestAContainsB(unittest.TestCase):
    def test_tied_starts_and_ends_are_ordered_correctly(self):
        """
        Incoming order is adversarial (arrival order is unreliable), but
        timestamps tie; buffering + event_key enforces:
          AStart(10) before BStart(10)
          BEnd(20)   before AEnd(20)
        Final evaluation order should be: AStart, BStart, BEnd, AEnd.
        """
        m = AContainsB()

        # Deliberately out-of-order arrivals with equal timestamps
        incoming = [
            BStart(time=10),  # arrives before AStart(10), but will be delayed by window
            AStart(time=10),
            AEnd(time=20),    # arrives before BEnd(20), but BEnd must be processed first
            BEnd(time=20),
        ]

        for e in incoming:
            m.eval(e)
        m.end()

        # No violations expected because the buffer imposes the desired tie order.
        self.assertFalse(m.errors_found(), f"Unexpected errors: {m.get_all_message_texts()}")

    def test_violation_b_starts_outside_a(self):
        m = AContainsB()
        incoming = [
            BStart(time=5),        # outside A
            AStart(time=10),
            BEnd(time=15),
            AEnd(time=20),
        ]
        for e in incoming:
            m.eval(e)
        m.end()

        msgs = m.get_all_message_texts()
        self.assertTrue(any("BStart occurred outside of A" in msg for msg in msgs), msgs)

    def test_violation_a_ends_before_b(self):
        m = AContainsB()
        incoming = [
            AStart(time=10),
            BStart(time=12),
            AEnd(time=16),         # ends A while B still open -> violation
            BEnd(time=17),
        ]
        for e in incoming:
            m.eval(e)
        m.end()

        msgs = m.get_all_message_texts()
        self.assertTrue(any("AEnd encountered while B is still open" in msg for msg in msgs), msgs)

    def test_nested_a_allows_multiple_b(self):
        """
        Demonstrates that nested A (a_depth>1) is permitted, and multiple B segments
        can occur as long as each B is fully inside some A.
        """
        m = AContainsB()
        incoming = [
            AStart(time=1),
            AStart(time=2),   # nested A
            BStart(time=3),
            BEnd(time=4),
            AEnd(time=5),     # close inner A
            AEnd(time=6),     # close outer A
        ]
        for e in incoming:
            m.eval(e)
        m.end()
        self.assertFalse(m.errors_found(), f"Unexpected errors: {m.get_all_message_texts()}")


if __name__ == "__main__":
    unittest.main()
