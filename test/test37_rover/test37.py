"""
Test file demonstrating AndState, OrState, and NotState for modeling a Mars rover.

The rover has the following commands:
- drive: Start moving the rover
- stop: Stop the rover's movement
- communicate: Send data to ground control
- take_picture: Capture an image with the rover's camera

The rover's behavior is modeled using composite states:
- AndState: For parallel activities (e.g., driving while taking pictures)
- OrState: For alternative modes of operation (e.g., science mode or transit mode)
- NotState: For safety constraints (e.g., cannot drive while communicating)
"""

import unittest
import pycontract as pc
from pycontract import visualize

# Define events for the rover

@pc.data
class Initialize(pc.Event):
    pass

@pc.data
class EnterTransitMode(pc.Event):
    pass

@pc.data
class EnterScienceMode(pc.Event):
    pass

@pc.data
class Drive(pc.Event):
    pass

@pc.data
class Stop(pc.Event):
    pass

@pc.data
class CheckSafety(pc.Event):
    pass

@pc.data
class Communicate(pc.Event):
    pass

@pc.data
class EndCommunication(pc.Event):
    pass

@pc.data
class CollectData(pc.Event):
    pass

@pc.data
class TakePicture(pc.Event):
    pass

@pc.data
class CollectSample(pc.Event):
    pass

@pc.data
class CameraError(pc.Event):
    pass

@pc.data
class InstrumentError(pc.Event):
    pass

@pc.data
class SignalLost(pc.Event):
    pass

@pc.data
class ObstacleDetected(pc.Event):
    pass

@pc.data
class ExitMode(pc.Event):
    pass

@pc.data
class Shutdown(pc.Event):
    pass

class RoverMonitor(pc.Monitor):
    """
    Monitor for a Mars rover with multiple operational modes and safety constraints.
    """
    def transition(self, event):
        match event:
            case Initialize():
                # Start with the rover in a safe, idle state
                return RoverMonitor.OperationalModes()
        return None

    @pc.data
    class OperationalModes(pc.HotState):
        """
        The rover has two main operational modes: Transit or Science.
        This is modeled as an OrState - the rover is in either one mode or the other.
        """
        def transition(self, event):
            match event:
                case EnterTransitMode():
                    return pc.OrState(
                        RoverMonitor.TransitMode(),
                        RoverMonitor.SafetyConstraints()
                    )
                case EnterScienceMode():
                    return pc.OrState(
                        RoverMonitor.ScienceMode(),
                        RoverMonitor.SafetyConstraints()
                    )
                case Shutdown():
                    return pc.ok
            return None
            
    @pc.data
    class TransitMode(pc.HotState):
        """Transit mode focuses on movement operations."""
        def transition(self, event):
            match event:
                case Drive():
                    return RoverMonitor.Driving()
                case ExitMode():
                    return RoverMonitor.OperationalModes()
            return None
            
    @pc.data
    class ScienceMode(pc.HotState):
        """Science mode focuses on data collection operations."""
        def transition(self, event):
            match event:
                case CollectData():
                    # In science mode, the rover can perform multiple activities in parallel
                    return pc.AndState(
                        RoverMonitor.Imaging(),
                        RoverMonitor.DataCollection()
                    )
                case ExitMode():
                    return RoverMonitor.OperationalModes()
            return None
            
    @pc.data
    class SafetyConstraints(pc.HotState):
        """
        Safety constraints that apply in all operational modes.
        """
        def transition(self, event):
            match event:
                case CheckSafety():
                    # Cannot drive while communicating - this is a safety constraint
                    return pc.NotState(
                        pc.AndState(
                            RoverMonitor.Driving(),
                            RoverMonitor.Communicating()
                        )
                    )
            return None
            
    @pc.data
    class Driving(pc.HotState):
        """State representing the rover in motion."""
        def transition(self, event):
            match event:
                case Stop():
                    return pc.ok
                case ObstacleDetected():
                    return pc.error("Safety violation: Obstacle detected while driving")
            return None
            
    @pc.data
    class Imaging(pc.HotState):
        """State for the rover's imaging operations."""
        def transition(self, event):
            match event:
                case TakePicture():
                    return pc.ok
                case CameraError():
                    return pc.error("Equipment failure: Camera malfunction")
            return None
            
    @pc.data
    class DataCollection(pc.HotState):
        """State for scientific data collection."""
        def transition(self, event):
            match event:
                case CollectSample():
                    return pc.ok
                case InstrumentError():
                    return pc.error("Equipment failure: Instrument malfunction")
            return None
            
    @pc.data
    class Communicating(pc.HotState):
        """State representing active communication with ground control."""
        def transition(self, event):
            match event:
                case Communicate():
                    return pc.ok
                case EndCommunication():
                    return RoverMonitor.OperationalModes()
                case SignalLost():
                    return pc.error("Communication failure: Signal lost")
            return None

class Test37(unittest.TestCase):
    """Test cases for the RoverMonitor."""
    
    def setUp(self):
        """Set up a fresh rover monitor for each test."""
        pc.Monitor.reset()
        self.monitor = RoverMonitor()
        
    def test_transit_mode(self):
        """Test the rover's transit mode operations."""
        self.monitor.eval(Initialize())
        self.monitor.eval(EnterTransitMode())
        self.monitor.eval(Drive())
        self.monitor.eval(Stop())
        self.monitor.eval(ExitMode())
        self.monitor.eval(Shutdown())
        self.monitor.end()
        self.assertFalse(self.monitor.errors_found())
        
    def test_science_mode(self):
        """Test the rover's science mode operations."""
        self.monitor.eval(Initialize())
        self.monitor.eval(EnterScienceMode())
        self.monitor.eval(CollectData())
        self.monitor.eval(TakePicture())
        self.monitor.eval(CollectSample())
        self.monitor.eval(ExitMode())
        self.monitor.eval(Shutdown())
        self.monitor.end()
        self.assertFalse(self.monitor.errors_found())
        
    def test_safety_violation(self):
        """Test that safety constraints are enforced."""
        self.monitor.eval(Initialize())
        self.monitor.eval(EnterTransitMode())
        self.monitor.eval(Drive())
        # This should trigger the safety constraint (cannot drive and communicate)
        self.monitor.eval(CheckSafety())
        self.monitor.eval(Communicate())
        self.monitor.end()
        # The NotState should cause an error when both driving and communicating
        self.assertTrue(self.monitor.errors_found())
        
    def test_equipment_failure(self):
        """Test handling of equipment failures."""
        self.monitor.eval(Initialize())
        self.monitor.eval(EnterScienceMode())
        self.monitor.eval(CollectData())
        self.monitor.eval(CameraError())
        self.monitor.end()
        self.assertTrue(self.monitor.errors_found())

if __name__ == "__main__":
    # Create a monitor instance and feed it events to create composite states
    monitor = RoverMonitor()
    
    # Create OrState (Transit mode with safety constraints)
    monitor.eval(Initialize())
    monitor.eval(EnterTransitMode())
    
    # Create AndState (Science activities in parallel)
    monitor2 = RoverMonitor()
    monitor2.eval(Initialize())
    monitor2.eval(EnterScienceMode())
    monitor2.eval(CollectData())
    
    # Create NotState (Safety constraint)
    monitor3 = RoverMonitor()
    monitor3.eval(Initialize())
    monitor3.eval(EnterTransitMode())
    monitor3.eval(Drive())
    monitor3.eval(CheckSafety())
    
    # Generate visualizations for the monitors in this file
    visualize(__file__, outdir="viz")
