import unittest
from pycontract import *
from dataclasses import dataclass

# Event classes for testing
class Event:
    def __init__(self, name, value=None):
        self.name = name
        self.value = value

@dataclass
class LoginEvent:
    username: str
    success: bool

@dataclass
class TransferEvent:
    amount: float
    destination: str

# Basic monitor with direct imports
class AliasedMonitor(Monitor):
    @initial
    class Initial(State):
        def transition(self, event):
            if event.name == 'start':
                return self.Next()

    class Next(State):
        def transition(self, event):
            if event.name == 'end':
                return ok

# Monitor with hot states
class SecurityMonitor(Monitor):
    @initial
    class LoggedOut(State):
        def transition(self, event):
            # Restructured to make the transition more explicit for the visualizer
            if isinstance(event, LoginEvent):
                if event.success:
                    return self.LoggedIn(event.username)
            # Default transition if no conditions match
            return ok

    class LoggedIn(HotState):
        def __init__(self, username):
            super().__init__()
            self.username = username

        def transition(self, event):
            if event.name == 'logout':
                return self.LoggedOut()
            # No transition for 'timeout', so it will remain in this hot state

# Monitor with composite states using OrState
class PaymentMonitor(Monitor):
    @initial
    class Idle(State):
        def transition(self, event):
            if isinstance(event, TransferEvent):
                # Create an OrState with two possible paths
                return OrState(
                    self.SmallTransfer(event.amount, event.destination),
                    self.LargeTransfer(event.amount, event.destination)
                )

    class SmallTransfer(State):
        def __init__(self, amount, destination):
            self.amount = amount
            self.destination = destination

        def transition(self, event):
            if self.amount < 1000:
                if event.name == 'approve':
                    return ok
                elif event.name == 'reject':
                    return self.Idle()
            else:
                # Not a small transfer, this branch should be dropped
                return error("Not a small transfer")

    class LargeTransfer(State):
        def __init__(self, amount, destination):
            self.amount = amount
            self.destination = destination

        def transition(self, event):
            if self.amount >= 1000:
                if event.name == 'approve_by_manager':
                    return ok
                elif event.name == 'reject':
                    return self.Idle()
            else:
                # Not a large transfer, this branch should be dropped
                return error("Not a large transfer")

# Monitor using ensure helper and sequence operator
class OrderProcessingMonitor(Monitor):
    @initial
    class OrderReceived(State):
        def transition(self, event):
            if event.name == 'validate':
                # Use ensure helper to check conditions
                return self.ensure(event.value > 0, "Order value must be positive")
            elif event.name == 'process':
                # Use sequence operator to define ordered processing steps
                return self.PaymentProcessing() >> self.Shipping()

    class PaymentProcessing(HotState):
        def __init__(self):
            super().__init__()
            
        def transition(self, event):
            if event.name == 'payment_complete':
                return ok
            elif event.name == 'payment_failed':
                # Need to use the monitor's OrderReceived class
                return OrderProcessingMonitor.OrderReceived()

    class Shipping(State):
        def transition(self, event):
            if event.name == 'shipped':
                return self.ensure(event.value == 'success', "Shipping failed")

# Monitor with AndState example
class AndStateMonitor(Monitor):
    @initial
    class Start(State):
        def transition(self, event):
            if event.name == 'parallel':
                # Create an AndState with two parallel paths
                return AndState(
                    self.PathA(),
                    self.PathB()
                )
            return ok

    class PathA(State):
        def transition(self, event):
            if event.name == 'a_complete':
                return ok
            return None

    class PathB(State):
        def transition(self, event):
            if event.name == 'b_complete':
                return ok
            return None

class Test36(unittest.TestCase):
    def setUp(self):
        # Reset the monitor state before each test
        Monitor.reset()
        
    def test_basic_monitor(self):
        """Tests that the basic monitor with direct imports works correctly."""
        mon = AliasedMonitor()
        trace = [
            Event('start'),
            Event('end')
        ]
        for event in trace:
            mon.eval(event)
        mon.end()
        self.assertFalse(mon.errors_found(), "Monitor should have no errors")

    def test_hot_state_monitor(self):
        """Tests a monitor with hot states."""
        mon = SecurityMonitor()
        # Successful path - login and logout
        trace = [
            LoginEvent(username="user1", success=True),
            Event('logout')
        ]
        for event in trace:
            mon.eval(event)
        mon.end()
        self.assertFalse(mon.errors_found(), "Monitor should have no errors")
        
        # Error path - login but no logout (ends in hot state)
        mon = SecurityMonitor()
        trace = [
            LoginEvent(username="user1", success=True),
            Event('timeout')
        ]
        for event in trace:
            mon.eval(event)
        mon.end()
        self.assertTrue(mon.errors_found(), "Monitor should detect hot state termination")

    def test_composite_state_monitor(self):
        """Tests a monitor with composite OrState."""
        # Small transfer path
        mon = PaymentMonitor()
        trace = [
            TransferEvent(amount=500, destination="account123"),
            Event('approve')
        ]
        for event in trace:
            mon.eval(event)
        mon.end()
        self.assertFalse(mon.errors_found(), "Monitor should have no errors")
        
        # Large transfer path
        mon = PaymentMonitor()
        trace = [
            TransferEvent(amount=1500, destination="account456"),
            Event('approve_by_manager')
        ]
        for event in trace:
            mon.eval(event)
        mon.end()
        self.assertFalse(mon.errors_found(), "Monitor should have no errors")
        
    def test_sequence_and_ensure(self):
        """Tests a monitor using sequence operator and ensure helper."""
        # Successful validation path
        mon = OrderProcessingMonitor()
        trace = [
            Event('validate', value=100)
        ]
        for event in trace:
            mon.eval(event)
        mon.end()
        self.assertFalse(mon.errors_found(), "Monitor should have no errors")
        
        # Failed validation path
        mon = OrderProcessingMonitor()
        trace = [
            Event('validate', value=-10)
        ]
        for event in trace:
            mon.eval(event)
        mon.end()
        self.assertTrue(mon.errors_found(), "Monitor should detect validation error")
        
        # Sequence path - successful completion
        mon = OrderProcessingMonitor()
        trace = [
            Event('process'),
            Event('payment_complete'),
            Event('shipped', value='success')
        ]
        for event in trace:
            mon.eval(event)
        mon.end()
        self.assertFalse(mon.errors_found(), "Monitor should have no errors")
        
        # Sequence path - payment failure
        mon = OrderProcessingMonitor()
        trace = [
            Event('process'),
            Event('payment_failed'),
            Event('validate', value=50)
        ]
        for event in trace:
            mon.eval(event)
        mon.end()
        self.assertFalse(mon.errors_found(), "Monitor should have no errors")
