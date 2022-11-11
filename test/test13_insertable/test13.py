from dataclasses import field
import os
from typing import Tuple, Dict
from pycontract import *
import unittest
import test.utest

DIR = os.path.dirname(__file__) + '/'

"""
Dennis Dams's Insertable example.
"""

DEvent = Dict[str, str]


class NextMonitor(Monitor):
    """
    This class defines generic concepts useful for general use.
    """

    class Next(NextState):
        """
        A state which must match a transition in the next step. The next possible events
        are provided as arguments together with the resulting state for each event.
        The events must be grounded (no pattern matching possible).
        """
        def __init__(self, *transitions: Tuple[DEvent, State]):
            """
            The argument events and resulting states.
            :param transitions: either a ground event and resulting state, or a list
            of pairs of the form (e,s) where e is a ground event and s is a resulting state.
            """
            if len(transitions) == 2 and isinstance(transitions[0], dict):
                self.transitions = [(transitions[0], transitions[1])]
            else:
                self.transitions = transitions

        def __str__(self) -> str:
            result = 'Next:\n'
            for (e, s) in self.transitions:
                result += f'  {e} -> {s}\n'
            return result

        def transition(self, event):
            for (e, s) in self.transitions:
                if event == e:
                    return s
            return error(f'expected: {[e for (e,s) in self.transitions]} but saw {event}')

    class NextStep(State):
        """
        A state which goes away in the next step. It is used as a flag used
        in conditions of transitions that only can be triggered in the next step
        if at all. It is used to model the situation when an event may either cause
        the next event to be of a certain kind, or not.
        """

        def transition(self, event):
            return ok


class InsertableDevice(NextMonitor):
    @initial
    class Unknown(State):
        def transition(self, event):
            match event:
                case {'type': 'command', 'name': 'GetInsertionState'}:
                    return self.Next({'type': 'return', 'arg': 'Unknown'}, self.Unknown())
                case({'type': 'command', 'name': 'BeginInsert'}
                    | {'type': 'command', 'name': 'BeginRetract'}
                    | {'type': 'command', 'name': 'WaitForInsert'}
                    | {'type': 'command', 'name': 'WaitForRetract'}):
                        return self.Next({'type': 'exception', 'message': event['name'] + '_not_allowed'}, self.Unknown())
                case {'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Retracted'}:
                    return self.Retracted()
                case {'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Inserted'}:
                    return self.Inserted()
                case {'type': 'error', 'name': 'ErrorNotif', 'message': 'error - staying in UNKNOWN'}:
                    return self.Unknown()

    class Inserting(State):
        def transition(self, event):
            match event:
                case {'type': 'command', 'name': 'GetInsertionState'}:
                    return self.Next({'type': 'return', 'arg': 'Inserting'}, self.Inserting())
                case {'type': 'command', 'name': 'BeginInsert'}:
                    return self.Next({'type': 'exception', 'message': 'BeginInsert_not_allowed'}, self.Inserting())
                case {'type': 'command', 'name': 'BeginRetract'}:
                    return self.Next({'type': 'exception', 'message': 'BeginRetract_not_allowed'}, self.Inserting())
                case {'type': 'command', 'name': 'WaitForInsert'}:
                    return self.Next(
                        ({'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Inserted'}, self.Inserted()),
                        ({'type': 'exception', 'message': 'WaitForInsert_failed'},
                         self.Next({'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Unknown'}, self.Unknown())
                         )
                    )
                case {'type': 'command', 'name': 'WaitForRetract'}:
                    return self.Next({'type': 'exception', 'message': 'WaitForRetract_not_allowed'}, self.Inserting())
                case {'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Inserted'}:
                    return self.Inserted()
                case {'type': 'error', 'name': 'ErrorNotif', 'message': 'error - going to UNKNOWN'}:
                    return self.Next({'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Unknown'}, self.Unknown())

    class Inserted(State):
        def transition(self, event):
            match event:
                case {'type': 'command', 'name': 'GetInsertionState'}:
                    return self.Next({'type': 'return', 'arg': 'Inserted'}, self.Inserted())
                case {'type': 'command', 'name': 'BeginInsert'}:
                    return self.Next({'type': 'exception', 'message': 'BeginInsert_not_allowed'}, self.Inserted())
                case {'type': 'command', 'name': 'BeginRetract'}:
                    return self.Next(
                        ({'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Retracting'}, self.Retracting()),
                        ({'type': 'exception', 'message': 'BeginRetract_failed'}, self.Unknown())
                    )
                case {'type': 'command', 'name': 'WaitForInsert'}:
                    return [self.Inserted(), self.NextStep()]
                case {'type': 'exception', 'message': 'WaitForInsert_failed'} if self.NextStep():
                    return self.Unknown()
                case {'type': 'command', 'name': 'WaitForRetract'}:
                    return self.Next({'type': 'exception', 'message': 'WaitForRetract_not_allowed'}, self.Inserted())
                case {'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Retracting'}:
                    return self.Retracting()
                case {'type': 'error', 'name': 'ErrorNotif', 'message': 'error - going to UNKNOWN'}:
                    return self.Next({'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Unknown'}, self.Unknown())

    class Retracting(State):
        def transition(self, event):
            match event:
                case {'type': 'command', 'name': 'GetInsertionState'}:
                    return self.Next({'type': 'return', 'arg': 'Retracting'}, self.Retracting())
                case {'type': 'command', 'name': 'BeginInsert'}:
                    return self.Next({'type': 'exception', 'message': 'BeginInsert_not_allowed'}, self.Retracting())
                case {'type': 'command', 'name': 'BeginRetract'}:
                    return self.Next({'type': 'exception', 'message': 'BeginRetract_not_allowed'}, self.Retracting())
                case {'type': 'command', 'name': 'WaitForInsert'}:
                    return self.Next({'type': 'exception', 'message': 'WaitForInsert_not_allowed'}, self.Retracting())
                case {'type': 'command', 'name': 'WaitForRetract'}:
                    return self.Next(
                        ({'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Retracted'}, self.Retracted()),
                        ({'type': 'exception', 'message': 'WaitForRetract_failed'},
                         self.Next({'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Unknown'}, self.Unknown())
                         )
                    )
                case {'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Retracted'}:
                    return self.Retracted()
                case {'type': 'error', 'name': 'ErrorNotif', 'message': 'error - going to UNKNOWN'}:
                    return self.Next({'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Unknown'}, self.Unknown())

    class Retracted(State):
        def transition(self, event):
            match event:
                case {'type': 'command', 'name': 'GetInsertionState'}:
                    return self.Next({'type': 'return', 'arg': 'Retracted'}, self.Retracted())
                case {'type': 'command', 'name': 'BeginInsert'}:
                    return self.Next(
                        ({'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Inserting'}, self.Inserting()),
                        ({'type': 'exception', 'message': 'BeginInsert_failed'}, self.Unknown())
                    )
                case {'type': 'command', 'name': 'BeginRetract'}:
                    return self.Next({'type': 'exception', 'message': 'BeginRetract_not_allowed'}, self.Retracted())
                case {'type': 'command', 'name': 'WaitForInsert'}:
                    return self.Next({'type': 'exception', 'message': 'WaitForInsert_not_allowed'}, self.Retracted())
                case {'type': 'command', 'name': 'WaitForRetract'}:
                    return [self.Retracted(), self.NextStep()]
                case {'type': 'exception', 'message': 'WaitForRetract_failed'} if self.NextStep():
                    return self.Next({'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Unknown'}, self.Unknown())
                case {'type': 'error', 'name': 'ErrorNotif', 'message': 'error - going to UNKNOWN'}:
                    return self.Next({'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Unknown'}, self.Unknown())


class Test1(test.utest.Test):
    def test1(self):
        visualize(__file__, True)
        # self.assert_equal_files('test13.InsertableDevice.test.pu', 'test13.InsertableDevice.pu')


class Test2(test.utest.Test):
    def test1(self):
        m = InsertableDevice()
        set_debug(True)

        # Tests nested calls of Next:
        trace1 = [
            {'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Retracted'},
            {'type': 'command', 'name': 'BeginInsert'},
            {'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Inserting'},
            {'type': 'command', 'name': 'WaitForInsert'},
            {'type': 'exception', 'message': 'WaitForInsert_failed'},
            {'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Unknown'}
        ]
        # Tests NextStep:
        trace2 = [
            {'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Retracted'},
            {'type': 'command', 'name': 'WaitForRetract'},
            {'type': 'exception', 'message': 'WaitForRetract_failed'},
            {'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Unknown'}
        ]
        # Tests NextStep:
        trace3 = [
            {'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Retracted'},
            {'type': 'command', 'name': 'WaitForRetract'},
            {'type': 'command', 'name': 'BeginInsert'},
            {'type': 'notification', 'name': 'InsertionStateChanged', 'arg': 'Inserting'}
        ]
        m.verify(trace3)

        errors_expected = []
        errors_actual = m.get_all_message_texts()
        print(errors_actual)
        # self.assert_equal(errors_expected, errors_actual)



