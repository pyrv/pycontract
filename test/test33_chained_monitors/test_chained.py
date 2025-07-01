from test import utest
from pycontract import *

# --- Events ---
@data
class SetValue(Event):
    """A low-level event."""
    val: int

@data
class HighLevelEvent(Event):
    """An abstracted event sent from the low-level to the high-level monitor."""
    num: int

# --- States ---
@data
class HighLevelState(HotState):
    """A state in the high-level monitor, should be terminated properly."""
    num: int

# --- Monitors ---
class LowLevelMonitor(Monitor):
    def __init__(self, high_level_monitor: Monitor):
        super().__init__()
        self.high_level = high_level_monitor

    def transition(self, event: Event):
        match event:
            case SetValue(val):
                # Process the low-level event and notify the high-level monitor
                # with an abstracted event.
                self.high_level.eval(HighLevelEvent(val * 2))
                return ok

class HighLevelMonitor(Monitor):
    def transition(self, event: Event):
        match event:
            case HighLevelEvent(num):
                return HighLevelState(num)

# --- Test Case ---
class TestChainedMonitors(utest.Test):
    def test_decoupled_bottom_up_communication(self):
        """
        Verifies bottom-up communication where the high-level monitor does not
        hold a reference to the low-level one.
        """
        # 1. Setup: Create both monitors and link them.
        high_m = HighLevelMonitor()
        low_m = LowLevelMonitor(high_m)

        # 2. Drive the system with a low-level event.
        low_m.eval(SetValue(10))

        # 3. Verify communication: The high-level monitor should have reacted.
        self.assertTrue(high_m.exists(HighLevelState, num=20))

        # 4. End the low-level monitor.
        # Since low_m holds a reference to high_m, the end() call should
        # automatically propagate up to the high-level monitor.
        low_m.end()

        # 5. Verify final states.
        # Since error reporting is now recursive, the low-level monitor should
        # also report the error found in the high-level monitor it is connected to.
        self.assertTrue(low_m.errors_found())
        self.assertTrue(high_m.errors_found())
        self.assertIn("terminates in hot state HighLevelState(20)", low_m.get_all_messages()[0].text)


