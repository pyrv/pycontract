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

class TestCompositePlantuml(unittest.TestCase):
    def test_composite_visualization(self):
        # Create an analyzer
        analyzer = Analyzer()
        
        # Parse this file
        with open(__file__, 'r') as f:
            source_code = f.read()
        
        # Parse the AST
        tree = ast.parse(source_code)
        
        # Visit the AST to extract monitors and states
        analyzer.visit(tree)
        
        # Check that we have the expected monitors
        monitor_names = [m.name for m in analyzer.monitors]
        self.assertIn('OrStateMonitor', monitor_names)
        self.assertIn('AndStateMonitor', monitor_names)
        self.assertIn('NotStateMonitor', monitor_names)
        
        # Check OrStateMonitor
        or_monitor = next(m for m in analyzer.monitors if m.name == 'OrStateMonitor')
        or_states = [s.name for s in or_monitor.states]
        self.assertIn('__Always__', or_states)
        self.assertIn('OR', or_states)
        self.assertIn('SciencePath', or_states)
        self.assertIn('TransitPath', or_states)
        
        # Check AndStateMonitor
        and_monitor = next(m for m in analyzer.monitors if m.name == 'AndStateMonitor')
        and_states = [s.name for s in and_monitor.states]
        self.assertIn('__Always__', and_states)
        self.assertIn('Imaging', and_states)
        self.assertIn('DataCollection', and_states)
        
        # Check NotStateMonitor
        not_monitor = next(m for m in analyzer.monitors if m.name == 'NotStateMonitor')
        not_states = [s.name for s in not_monitor.states]
        self.assertIn('__Always__', not_states)
        self.assertIn('NOT', not_states)
        self.assertIn('Driving', not_states)
        self.assertIn('Communicating', not_states)
        
        # Check for AND_INNER state in NotStateMonitor
        self.assertIn('AND_INNER', not_states)
        
        # Check for transitions in NotStateMonitor
        not_transitions = not_monitor.transitions
        has_not_to_and_inner = False
        has_and_inner_to_driving = False
        has_and_inner_to_communicating = False
        
        for t in not_transitions:
            if t.source == 'NOT' and t.target == 'AND_INNER':
                has_not_to_and_inner = True
            elif t.source == 'AND_INNER' and t.target == 'Driving':
                has_and_inner_to_driving = True
            elif t.source == 'AND_INNER' and t.target == 'Communicating':
                has_and_inner_to_communicating = True
        
        self.assertTrue(has_not_to_and_inner, "Missing transition from NOT to AND_INNER")
        self.assertTrue(has_and_inner_to_driving, "Missing transition from AND_INNER to Driving")
        self.assertTrue(has_and_inner_to_communicating, "Missing transition from AND_INNER to Communicating")

if __name__ == '__main__':
    unittest.main()
