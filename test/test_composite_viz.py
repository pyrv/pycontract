import unittest
import sys
import os
import ast

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pycontract as pc
from pycontract.pycontract_plantuml import Analyzer

@pc.data
class Initialize(pc.Event):
    pass

@pc.data
class Drive(pc.Event):
    pass

@pc.data
class TakePicture(pc.Event):
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
            return None
    
    @pc.data
    class DataCollection(pc.HotState):
        def transition(self, event):
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
            return None

if __name__ == '__main__':
    unittest.main()
