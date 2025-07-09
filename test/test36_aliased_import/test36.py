import unittest
import pycontract as pc
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

# Basic monitor with aliased imports
class AliasedMonitor(pc.Monitor):
    @pc.initial
    class Initial(pc.State):
        def transition(self, event):
            if event.name == 'start':
                return self.Next()

    class Next(pc.State):
        def transition(self, event):
            if event.name == 'end':
                return pc.ok

# Monitor with hot states
class SecurityMonitor(pc.Monitor):
    @pc.initial
    class LoggedOut(pc.State):
        def transition(self, event):
            # Restructured to make the transition more explicit for the visualizer
            if isinstance(event, LoginEvent):
                if event.success:
                    return self.LoggedIn(event.username)
            # Default transition if no conditions match
            return pc.ok

    class LoggedIn(pc.HotState):
        def __init__(self, username):
            super().__init__()
            self.username = username

        def transition(self, event):
            if event.name == 'logout':
                return self.LoggedOut()
            # No transition for 'timeout', so it will remain in this hot state

# Monitor with composite states using OrState
class PaymentMonitor(pc.Monitor):
    @pc.initial
    class Idle(pc.State):
        def transition(self, event):
            if isinstance(event, TransferEvent):
                # Create an OrState with two possible paths
                return pc.OrState(
                    self.SmallTransfer(event.amount, event.destination),
                    self.LargeTransfer(event.amount, event.destination)
                )

    class SmallTransfer(pc.State):
        def __init__(self, amount, destination):
            self.amount = amount
            self.destination = destination

        def transition(self, event):
            if self.amount < 1000:
                if event.name == 'approve':
                    return pc.ok
                elif event.name == 'reject':
                    return self.Idle()
            else:
                # Not a small transfer, this branch should be dropped
                return pc.error("Not a small transfer")

    class LargeTransfer(pc.State):
        def __init__(self, amount, destination):
            self.amount = amount
            self.destination = destination

        def transition(self, event):
            if self.amount >= 1000:
                if event.name == 'approve_by_manager':
                    return pc.ok
                elif event.name == 'reject':
                    return self.Idle()
            else:
                # Not a large transfer, this branch should be dropped
                return pc.error("Not a large transfer")

# Monitor using ensure helper and sequence operator
class OrderProcessingMonitor(pc.Monitor):
    @pc.initial
    class OrderReceived(pc.State):
        def transition(self, event):
            if event.name == 'validate':
                # Use ensure helper to check conditions
                return self.ensure(event.value > 0, "Order value must be positive")
            elif event.name == 'process':
                # Use sequence operator to define ordered processing steps
                return self.PaymentProcessing() >> self.Shipping()

    class PaymentProcessing(pc.HotState):
        def __init__(self):
            super().__init__()
            
        def transition(self, event):
            if event.name == 'payment_complete':
                return pc.ok
            elif event.name == 'payment_failed':
                # Need to use the monitor's OrderReceived class
                return OrderProcessingMonitor.OrderReceived()

    class Shipping(pc.State):
        def transition(self, event):
            if event.name == 'shipped':
                return self.ensure(event.value == 'success', "Shipping failed")

# Monitor with AndState example
class AndStateMonitor(pc.Monitor):
    @pc.initial
    class Start(pc.State):
        def transition(self, event):
            if event.name == 'parallel':
                # Create an AndState with two parallel paths
                return pc.AndState(
                    self.PathA(),
                    self.PathB()
                )
            return pc.ok

    class PathA(pc.State):
        def transition(self, event):
            if event.name == 'a_complete':
                return pc.ok
            return None

    class PathB(pc.State):
        def transition(self, event):
            if event.name == 'b_complete':
                return pc.ok
            return None

class Test36(unittest.TestCase):
    def setUp(self):
        # Reset the monitor state before each test
        pc.Monitor.reset()
        
    def test_basic_monitor(self):
        """Tests that the basic monitor with aliased imports works correctly."""
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
