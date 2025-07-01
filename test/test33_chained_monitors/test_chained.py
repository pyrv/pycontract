from test import utest
from pycontract import *


@data
class SetValue(Event):
    """A low-level event."""
    val: int

@data
class HighLevelEvent(Event):
    """An abstracted event sent from the low-level to the high-level monitor."""
    num: int


class Low(Monitor):
    def __init__(self, high_level_monitor: Monitor):
        super().__init__()
        self.high_level = high_level_monitor

    def transition(self, event: Event):
        match event:
            case SetValue(val):
                self.high_level.eval(HighLevelEvent(val * 2))
                return ok

class High(Monitor):
    def transition(self, event: Event):
        match event:
            case HighLevelEvent(num):
                return High.HighState(num)

    @data
    class HighState(HotState):
        num: int

# --- Test Case ---
class TestChainedMonitors(utest.Test):
    def test_decoupled_bottom_up_communication(self):
        high_m = High()
        low_m = Low(high_m)

        low_m.eval(SetValue(10))
        self.assertTrue(high_m.exists('HighState', num=20))
        low_m.end()
        self.assertTrue(low_m.errors_found())
        self.assertTrue(high_m.errors_found())
        self.assertIn("terminates in hot state HighState(20)", low_m.get_all_messages()[0].text)


