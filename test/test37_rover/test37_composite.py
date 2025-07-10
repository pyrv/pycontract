import unittest
import pycontract as pc
from pycontract import visualize

@pc.data
class Initialize(pc.Event):
    pass

@pc.data
class Drive(pc.Event):
    pass

@pc.data
class Stop(pc.Event):
    pass

@pc.data
class TakePicture(pc.Event):
    pass

@pc.data
class Communicate(pc.Event):
    pass

@pc.data
class CollectSample(pc.Event):
    pass

class OrStateMonitor(pc.Monitor):
    def transition(self, event):
        match event:
            case Initialize():
                return pc.OrState(
                    OrStateMonitor.SciencePath(),
                    OrStateMonitor.TransitPath()
                )
        return None
    
    @pc.data
    class SciencePath(pc.HotState):
        def transition(self, event):
            match event:
                case TakePicture():
                    return pc.ok
                case CollectSample():
                    return pc.ok
            return None
    
    @pc.data
    class TransitPath(pc.HotState):
        def transition(self, event):
            match event:
                case Drive():
                    return pc.ok
                case Stop():
                    return pc.ok
            return None

class AndStateMonitor(pc.Monitor):
    def transition(self, event):
        match event:
            case Initialize():
                return [
                    AndStateMonitor.Imaging(),
                    AndStateMonitor.DataCollection()
                ]
        return None
    
    @pc.data
    class Imaging(pc.HotState):
        def transition(self, event):
            match event:
                case TakePicture():
                    return pc.ok
            return None
    
    @pc.data
    class DataCollection(pc.HotState):
        def transition(self, event):
            match event:
                case CollectSample():
                    return pc.ok
            return None

class NotStateMonitor(pc.Monitor):
    def transition(self, event):
        match event:
            case Initialize():
                and_state = pc.AndState(
                    NotStateMonitor.Driving(),
                    NotStateMonitor.Communicating()
                )
                return pc.NotState(and_state)
        return None
    
    @pc.data
    class Driving(pc.HotState):
        def transition(self, event):
            match event:
                case Drive():
                    return pc.ok
            return None
    
    @pc.data
    class Communicating(pc.HotState):
        def transition(self, event):
            match event:
                case Communicate():
                    return pc.ok
            return None

class RoverMonitor(pc.Monitor):
    def transition(self, event):
        match event:
            case Initialize():
                return RoverMonitor.Idle()
        return None
    
    @pc.data
    class Idle(pc.HotState):
        def transition(self, event):
            match event:
                case Drive():
                    return pc.OrState(
                        RoverMonitor.TransitMode(),
                        RoverMonitor.SafetyMode()
                    )
                case TakePicture():
                    return [
                        RoverMonitor.Imaging(),
                        RoverMonitor.DataCollection()
                    ]
            return None
    
    @pc.data
    class TransitMode(pc.HotState):
        def transition(self, event):
            match event:
                case Stop():
                    return pc.ok
            return None
    
    @pc.data
    class SafetyMode(pc.HotState):
        def transition(self, event):
            match event:
                case Communicate():
                    return pc.NotState(RoverMonitor.Driving())
            return None
    
    @pc.data
    class Imaging(pc.HotState):
        def transition(self, event):
            match event:
                case TakePicture():
                    return pc.ok
            return None
    
    @pc.data
    class DataCollection(pc.HotState):
        def transition(self, event):
            match event:
                case CollectSample():
                    return pc.ok
            return None
    
    @pc.data
    class Driving(pc.HotState):
        def transition(self, event):
            match event:
                case Stop():
                    return pc.ok
            return None

def create_monitors_for_visualization():
    or_monitor = OrStateMonitor()
    or_monitor.eval(Initialize())
    
    and_monitor = AndStateMonitor()
    and_monitor.eval(Initialize())
    
    not_monitor = NotStateMonitor()
    not_monitor.eval(Initialize())
    
    rover_monitor = RoverMonitor()
    rover_monitor.eval(Initialize())
    rover_monitor.eval(TakePicture())
    
    return or_monitor, and_monitor, not_monitor, rover_monitor

# No test cases needed for visualization

if __name__ == "__main__":
    create_monitors_for_visualization()
    visualize(__file__, outdir="viz")
