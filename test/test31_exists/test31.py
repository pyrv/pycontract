from test import utest
from pycontract import *

# Define some simple states and events for testing
@data
class Start(Event):
    pass

@data
class StateA(State):
    val: int

@data
class StateB(State):
    name: str

class ExistsMonitor(Monitor):
    def transition(self, event: Event):
        match event:
            case Start():
                return AndState(
                    StateA(val=10),
                    Sequence(
                        StateB(name="first"),
                        StateB(name="second")
                    )
                )

class TestExists(utest.Test):
    def test_exists_by_type_and_fields(self):
        """Tests the new exists() method with class types and field matching."""
        m = ExistsMonitor()
        m.eval(Start())

        # Test finding simple state by type
        self.assertTrue(m.exists(StateA))
        # Test finding simple state by type and field
        self.assertTrue(m.exists(StateA, val=10))
        self.assertFalse(m.exists(StateA, val=99))
        # Test finding nested state by type
        self.assertTrue(m.exists(StateB))
        # Test finding nested state by type and field
        self.assertTrue(m.exists(StateB, name="first"))
        self.assertTrue(m.exists(StateB, name="second"))
        self.assertFalse(m.exists(StateB, name="third"))
        # Test finding non-existent state
        self.assertFalse(m.exists(HotState))

    def test_exists_by_string_name(self):
        """Tests the new exists() method with class names as strings."""
        m = ExistsMonitor()
        m.eval(Start())
        self.assertTrue(m.exists("StateA", val=10))
        self.assertTrue(m.exists("StateB", name="first"))
        self.assertFalse(m.exists("StateC"))

    def test_original_exists_predicate(self):
        """Tests that the original predicate-based exists() still works."""
        m = ExistsMonitor()
        m.eval(Start())
        # Test original predicate functionality
        self.assertTrue(m.exists(lambda s: isinstance(s, StateA) and s.val > 5))
        self.assertFalse(m.exists(lambda s: isinstance(s, StateB) and s.name == "third"))
        self.assertTrue(m.exists(lambda s: isinstance(s, AndState)))

    def test_exists_type_error(self):
        """Tests that exists() raises a TypeError for invalid arguments."""
        m = ExistsMonitor()
        m.eval(Start())
        with self.assertRaises(TypeError):
            m.exists(123) # Not a type, string, or callable
