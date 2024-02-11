"""
PyContract
"""
import copy
import inspect
from abc import ABC
from dataclasses import dataclass
from typing import List, Set, Callable, Optional, Dict
import pyfiglet


def print_banner(text: str):
    '''
    Prints a banner as ASCII art in slant format.
    See: https://github.com/pwaller/pyfiglet.
    :param text: the text to be printed as ASCII art.
    '''
    ascii_banner = pyfiglet.figlet_format(text, font='slant')
    print(ascii_banner)


def data(cls):
    """
    Decorator for decorating events and states, allowing to
    declare parameters more easily than with __init__.
    Also, the unsafe_hash=True introduces a hash function needed
    for storing states in sets.
    """
    return dataclass(cls, unsafe_hash=True)


"""
Auxiliary types.
"""
Char = str


class Debug:
    """
    When set to true output will contain debugging information.
    """
    DEBUG: bool = False
    """
    When set garbage collected states will be printed.
    This can be used to study how garbage collection works.
    """
    DEBUG_GC: bool = False
    """
    When set progress will be reported for every `DEBUG_PROGRESS`
    event. Default is `None` which means no progress reports.
    """
    DEBUG_PROGRESS: Optional[int] = None


def test(nr: int, txt: str, msg: str = ''):
    """
    Prints error message. Used when locating a bug and temporary print statements
    are needed. By calling this function instead of print, it is possible quickly
    locate all such calls when one is done bug hunting, so that they can be removed again.
    :param nr: a number allowing to trace printed message back to code
    :param txt: a headline explaining the message
    :param msg: the message to be printed
    """
    print(f'# test [{nr}] {txt}: {msg}')


def set_debug(value: bool):
    """
    Sets the debug flag. When True, for each submitted event will be printed:
    1. the event number and event
    2. for each monitor:
       2.1 internal transitions in the monitor
       2.2 final set of states of the monitor
    :param value: when True debugging information is printed.
    """
    Debug.DEBUG = value


def set_debug_gc(value: bool):
    """
    Sets the garbage collection debug flag. When True, garbage collected
    states will be printed
    :param value: when True debugging information is printed.
    """
    Debug.DEBUG_GC = value


def set_debug_progress(value: int):
    """
    Sets the progress reporting debug value. When different from None,
    a message is issued for every `value` event.
    :param value: a message will be issued for every `value` event.
    """
    Debug.DEBUG_PROGRESS = value


def debug(msg: str):
    """
    Prints debugging information. By giving this function a special
    name it is easier to locate debugging statements.
    Calls of this function are always guarded by a test on the `DEBUG` flag.
    :param msg: the message to be printed.
    """
    print(msg)


def debug_frame(symbol: Char, msg: str):
    """
    Prints a message surrounded by a line of symbols before and after.
    :param symbol: the symbol to make up the line, as long as the message.
    :param msg: the message to be printed.
    """
    print_frame(symbol, msg)


def print_frame(symbol: Char, msg: str):
    """
    Prints a message surrounded by a line of symbols before and after,
    :param symbol: the symbol to make up the line, as long as the message.
    :param msg: the message to be printed.
    """
    length = len(msg)
    print(symbol * length)
    print(msg)
    print(symbol * length)
    print()


def mk_string(begin: str, separator: str, end: str, args: list) -> str:
    """
    Turns a list of values into a string, surrounded by given begin and end strings, and
    elements separated by a given separator.
    :param begin: string to begin with.
    :param separator: separator to separate list elements.
    :param end: string to end with.
    :param args: the list of values.
    :return: the resulting string.
    """
    result = begin
    sep = ""
    for arg in args:
        result += f'{sep}{quote(arg)}'
        sep = separator + ' '
    result += end
    return result


def is_state_class(member: object) -> bool:
    """
    Returns true if the object member is a class and specifically a subclass of State.
    Used for identifying the states in a monitor.
    :param member: the member object to check.
    :return: True iff the object member is a class and specifically a subclass of State.
    """
    return inspect.isclass(member) and issubclass(member, State)


def is_transition_method(member: object) -> bool:
    """
    Returns true if the object member is a method named `transition`.
    Used for identifying the methods in a monitor that model transitions.
    :param member: the member object to check.
    :return: True iff the object member is a function named `transition`.
    """
    return inspect.ismethod(member) and member.__name__ == 'transition'


def hasattr_really(obj: object, attr) -> bool:
    """
    Examines whether an object really has an attribute, without calling
    __getattr__, which in states looks up the attribute in the monitor
    it is part of.
    :param obj: the object to look for the attribute.
    :param attr: the attribute.
    :return: True iff the attribute is really defined in that object.
    """
    try:
        obj.__getattribute__(attr)
        return True
    except:
        return False


def quote(arg: object) -> object:
    """
    Puts quotes around a string (so it appears as a string in output). Otherwise returns
    argument unchanged.
    :param arg: argument to transform.
    :return: argument quoted if a string, otherwise unchanged.
    """
    if isinstance(arg,str):
        return f"'{arg}'"
    else:
        return arg

"""
The type of events. An event can be any Python value.
"""
Event = object


@data
class State:
    """
    Objects of this class represent active states in the state machine.
    It is defined as data state, which activates the hash function, used
    for storing states in a hashset.
    """

    def __init__(self):
        """
        Will eventually point to the monitor instance this state instance is part of.
        __init__ does not need to be called, but its definition removes some warnings
        in PyCharm.
        """
        self.monitor = None
        """
        Data specific to a particular form of analysis can be stored here and printed
        out when the `end()` method of the monitor containing the state is called.
        """
        self.__data_object__: object = None

    def __str__(self) -> str:
        result = self.get_state_name()
        if hasattr_really(self, '__init__'):
            args = inspect.getfullargspec(self.__init__).args[1:]
            result += mk_string('(', ',', ')', [getattr(self, arg) for arg in args])
        if hasattr_really(self, '__data_object__') and self.__data_object__ is not None:
            result += '\n' + self.__data_object__.__str__()
        return result

    def __getattr__(self, attr) -> object:
        """
        Used for looking up an attribute in the monitor of a state, when
        the attribute is not defined in the state. This is used for
        transition methods that are defined at the outermost level, and which
        get inserted into the anonymous always state. In that state the self argument
        of these methods no longer refers to the monitor. One would have to write
        self.monitor.attr in those methods which is annoying.
        :param attr: the attribute to look up.
        :return: the value of the attribute.
        """
        return getattr(self.monitor, attr)

    def __bool__(self):
        """
        Allows a state to be used as a  Boolean, which is True if
        the state is in the state vector. Can be used for expressing
        past time properties.
        :return: True of the state is in the state vector.
        """
        return self.monitor.contains_state(self)

    def __del__(self):
        """
        Called when a state object is garbage collected.
        Prints the state if `DEBUG_GC` is True.
        """
        if Debug.DEBUG_GC:
            print(f'{str(self)} garbage collected')

    def set_monitor_to(self, monitor: "Monitor"):
        """
        Assigns the monitor instance this state instance is part of to the
        variable self.monitor.
        :param monitor: assumed to be the parent monitor instance of this state instance.
        """
        self.monitor = monitor

    def get_state_name(self) -> str:
        """
        Returns the name of the state.
        :return: the name of the state.
        """
        return self.__class__.__name__

    def exists(self, predicate: Callable[["State"], bool]) -> bool:
        """
        Returns True iff there exists a state s in the state vector of the monitor,
        such that predicate(s) is True.
        :param predicate: the predicate which a state in the state vector must satisfy.
        :return: True iff. a state in the state vector satisfies the predicate.
        """
        return self.monitor.exists(predicate)

    def transition(self, event) -> Optional["State" | List["State"]]:
        """
        Evaluates a state on an event. The result is an optional state or a list of states.
        None is returned if there is no transition corresponding to the event (the default).
        The method can be overridden in a state to model the state's behavior.
        :param event: the event on which the state is evaluated.
        :return: the optional state or list of states, the target states of the transition.
        """
        pass

    def eval(self, event: Event) -> List["State"]:
        """
        Evaluates a state on an event. The result is a list of resulting states.
        In case the event does not match any transition, the singleton list containing
        the state itself is returned, modeling that we stay in that state.
        Otherwise, the state or list of states returned by the `transition` function is
        returned (if a single state is returned by the `transition` function, it is wrapped
        in a singleton list).
        The `eval` method is overridden in subclasses of class `State` to behave differently.
        :param event: the event on which the state is evaluated.
        :return: the list of resulting states, the target states of the transition.
        """
        result = self.transition(event)
        if result is None:
            return [self]
        else:
            return mk_state_vector(result)


class HotState(State):
    """
    A state that behaves as `State`. The difference is in how it is handled at the end of
    monitoring (when the `end()` method is called on the monitor). In that case any state
    of type `HotState` causes an error message to be issued. "Hot" reflects the concept of
    standing on hot coals, eventually it is necessary to move on.
    """
    pass


class NextState(State):
    """
    A state where the next event has to trigger a transition.
    It overrides the `eval` method of `State`, by checking that
    there is a matching `transition`. If not, an error is
    issued. Note that such a state should only be used together
    with some form of slicing.
    """

    def eval(self, event: Event) -> List[State]:
        """
        Overrides the `eval` method of `State`, by checking that
        there is a matching transition. If not, an error is
        issued.
        :param event: the event on which the state is evaluated.
        :return: the list of resulting states, the target states of the transition.
        The list will contain an error state if there is no matching transition.
        """
        result = self.transition(event)
        if result is None:
            return [error(f'no transition matching event')]
        else:
            return mk_state_vector(result)


class HotNextState(NextState):
    """
    A state that behaves as `NextState`. The difference is in how it is handled at the end of
    monitoring (when the `end()` method is called on the monitor). In that case any state
    of type `HotNextState` causes an error message to be issued. "Hot" reflects the concept of
    standing on hot coals, eventually it is necessary to move on.
    """
    pass


class AlwaysState(State):
    """
    A state that is always active: it is always maintained in the
    state vector. It overrides the `eval` method of `State`, by adding
    itself back into the state vector independently of whether the `transition` function
    matches the event.
    """

    def eval(self, event: Event) -> List[State]:
        """
        Overrides the `eval` method of `State`, by always adding itself back
        into the state vector.
        :param event: the event on which the state is evaluated.
        :return: the list of resulting states, the target states of the transition.
        """
        result = self.transition(event)
        if result is None:
            return [self]
        else:
            return mk_state_vector(result) + [self]


class ErrorState(State):
    """
    A transition can return an `ErrorState` object, including an error message and a data object.
    This will cause the error to be recorded. The `ErrorState` itself is removed
    from the state vector after processing.
    """

    def __init__(self, text: str, data: object):
        """
        The `ErrorState` is initialized with a message and a data object, which
        can be any Python object, such as a class instance, a dictionary, etc.
        :param text: the message.
        :param data: the data object
        """
        self.text = text
        self.data = data

    def __str__(self) -> str:
        return f'ErrorState({self.text})'


def error(text: str = "", obj: object = None) -> ErrorState:
    """
    Returns an `ErrorState`.
    :param text: the message.
    :param obj: the data object.
    :return: an `ErrorState` object.
    """
    return ErrorState(text, obj)


class InfoState(State):
    """
    A transition can return an `InfoState` object, including a message and a data object.
    This is for just recording facts about the trace. The `InfoState` itself is removed
    from the state vector after processing.
    """

    def __init__(self, text: str, data: object):
        """
        The `InfoState` is initialized with a message and a data object, which
        can be any Python object, such as a class instance, a dictionary, etc.
        :param text: the message.
        :param data: the data object
        """
        self.text = text
        self.data = data

    def __str__(self) -> str:
        return f'InfoState({self.text})'


def info(text: str, obj: object = None) -> InfoState:
    """
    Returns an `InfoState`, with a message.
    :param text: the message.
    :param obj: the data object.
    :return: an InfoState object.
    """
    return InfoState(text, obj)



"""
Is used as target of a transition when it is ok
to leave the source state without performing further monitoring.
"""


@data
class OkState(State):
    pass


ok = OkState()


def done() -> int:
    """
    The `done()` function is called in `exhaustive` states. All transitions that return
    `done()` must be taken before that state is left with an ok. Alternatively some other
    transition may cause us to leave the state, such as returning `ok`, `error`, or some other
    user defined state.
    :return: the line number in which this function is called. This is used to check off
    calls of `done()`. When all have been executed, the state is left with an `ok`.
    """
    frame_below_current = 1  # 0 is the top frame
    line_nr_of_call = 2
    line_called_from = inspect.stack()[frame_below_current][line_nr_of_call]
    return line_called_from


class MatchObligations:
    """
    Stores information about which lines in the transition function of a state
    contains calls of the `done()` function. It furthermore maps these line numbers
    to the case patterns that preceded them. calls of `add` add such associations
    when the `exhaustive` function is called, and calls of `remove` deletes such
    assiations as the `done()` function calls are executed. At the end if there are
    remaining calls of `done()` not executed (`empty()` returns false), this is
    recorded as an error in case it is a hot state.
    """
    def __init__(self):
        """
        Mapping each line number of a call of `done()` to a tuple consisting of
        the line number of the corresponding preceding case statement, and
        the case statement.
        """
        self.calls_of_done_map: Dict[int, tuple[int, str]] = {}
        """
        Controls the printing of this data structure. Only if `remove_called` is
        true and `empty()` returns false will remaining unmatched case statements be printed.
        """
        self.remove_called: bool = False
        self.removed: set[int] = set()

    def add(self, line_nr_done: int, line_nr_pattern: int, pattern: str):
        """
        Adds a new call of `done()`.
        :param line_nr_done: the line number of the call of `done()`.
        :param line_nr_pattern: the line number of the preceding case statement.
        :param pattern: the preceding case statement.
        """
        self.calls_of_done_map.update({line_nr_done: (line_nr_pattern, pattern)})

    def remove(self, line_nr_done: int):
        """
        Called when `done()` is called. Removes that call and corresponding case statement
        from the data structure. It is no longer an obligation.
        :param line_nr_done: line number of the call of `done()`.
        """
        self.remove_called = True
        if line_nr_done in self.calls_of_done_map:
            del self.calls_of_done_map[line_nr_done]
            self.removed.add(line_nr_done)
        else:
            assert line_nr_done in self.removed

    def empty(self) -> bool:
        """
        Returns true if there are no more obligations.
        :return: true if no more obligations.
        """
        return len(self.calls_of_done_map) == 0

    def __str__(self) -> str:
        result: str = ''
        if self.remove_called:
            result += "    Cases not matched that lead to calls of done() :"
            for (line_nr_pattern, pattern) in self.calls_of_done_map.values():
                if pattern[-1] == ':':
                    pattern = pattern[:-1]
                result += f'\n      line {line_nr_pattern} : {pattern}'
        return result


def exhaustive(transition_function: Callable[[object, Event], Optional[List[State]]]) -> Callable[[object, Event], Optional[List[State]]]:
    """
    Transition function decorator. It decorates a transition function, which is supposed to contain
    calls of the `done()` function. That is, it takes as argument a transition function and returns
    a new transition function behaving as follows: it returns the current state as long as there
    are remaining unexecuted calls of `done()` or until some other state is returned, such as
    `ok`, `error`, or some user-defined state.
    :param transition_function: the user-defined transition function.
    :return: the modified transition function that returns the current state as long as there are
    remaining un-executed calls of `done()`.
    """
    index_frame_below_current = 1  # 0 is the top frame
    index_line_nr_of_call = 2  # call of decorator function `exhaustive`.
    # line number of first line of transition function definition
    line_number = inspect.stack()[index_frame_below_current][index_line_nr_of_call] + 1
    (code, nr_of_lines) = inspect.getsourcelines(transition_function)
    # code includes decorator which must be removed.
    code_except_decorator = code[1:]
    match_obligations = MatchObligations()
    next_case: str = ""
    next_case_line_number: int = 0
    for line in code_except_decorator:
        if "case " in line:
            next_case_line_number = line_number
            next_case = line.strip()
        if "done()" in line:
            match_obligations.add(line_number, next_case_line_number, next_case)
        line_number += 1

    def new_transition(self, event):
        if not hasattr(self, '__data_object__') or self.__data_object__ is None:
            self.__data_object__ = match_obligations
        result = transition_function(self, event)
        if isinstance(result, int):
            self.__data_object__.remove(result)
            if self.__data_object__.empty():
                return ok  # we are done
            else:
                return self  # we are not done yet
        else:
            return result  # something else (ok, error, or another state)

    return new_transition


def initial(state_class: State) -> State:
    """
    Decorator function which introduces the Boolean variable 'is_initial' (assigning it the value True,
    although that is not important) in its argument state.
    It allows us to annotate states as follows:

      @initial
      class Init(State):
          ...

     This has the same effect as:

      class Init(State):
          ...
      Init.is_initial = True
    :param state_class: the state to decorate.
    :return: the decorated state.
    """
    state_class.is_initial = True
    return state_class


def mk_state_vector(arg: State | List[State]) -> List[State]:
    """
    Turns a state or a list of states into a list of states.
    If the argument is a single state s, the singular state vector [s] is returned.
    If the argument is a list of states, it is returned unchanged.
    :param arg: a state or a list of states.
    :return: the list of states.
    """
    if isinstance(arg, list):
        return arg
    else:
        return [arg]


class Message:
    """
    The type of messages stored in a monitor, generated when errors are detected
    with calls of the `error` method or information is generated with
    with calls of the `info` method.
    """
    def __init__(self, text: str, data: object):
        self.text = text
        self.data = data

    def __str__(self):
        return self.text


class Monitor:
    """
    Any user defined monitor class must extend this class. It defines a monitor.
    """

    def __init__(self):
        """
        monitors:
          A monitor can have sub-monitors, stored in this variable.
        is_top_monitor:
          Is True iff. this monitor is the topmost monitor in a monitor
          hierarchy, that is: not a sub-monitor of another monitor.
          Used for printing purposes in that only the topmost monitor prints
          out certain debugging information.
        states:
          The state vector of the monitor: the set of all active states.
        states_indexed:
          Indexed states, used for slicing.
        messages:
          Reported messages, including errors, during monitoring.
        event_count:
          Counts the events as they come in.
        option_show_state_event:
          When True, state and event will be printed on transition errors.
        option_print_summary:
          When True, a summary of the analysis is printed for the top monitor.
        """
        self.monitors: List[Monitor] = []
        self.is_top_monitor: bool = True
        self.states: Set[State] = set([])
        self.states_indexed : Dict[object, Set[State]] = {}
        self.messages: List[str] = []
        self.event_count: int = 0
        self.option_show_state_event: bool = True
        self.option_print_summary: bool = True
        # Create always state if outermost transitions exist
        outer_transitions = inspect.getmembers(self, predicate=is_transition_method)
        if len(outer_transitions) > 0:
            always = type("Always", (AlwaysState,), {})
            setattr(always, "is_initial", True)
            (name, method) = outer_transitions[0]
            setattr(always, name, method.__func__)
            setattr(self, "Always", always)
        # Locate all state classes (subclassing State):
        state_classes = inspect.getmembers(self, predicate=is_state_class)
        if len(state_classes) > 0:
            # Add initial states:
            initial_state_found = False
            for (state_name, state_class) in state_classes:
                if hasattr(state_class, 'is_initial'):
                    self.add_state_to_state_vector(self.states, state_class())
                    initial_state_found = True
            if not initial_state_found:
                (name, the_first_class) = state_classes[0]
                self.add_state_to_state_vector(self.states, the_first_class())

    def set_event_count(self, initial_value: int):
        """
        Sets the initial value of `event_count` to a different value than 0.
        This is used for example when processing CSV files, where there is a header
        row, which should be counted as an 'event' so that `event_count` will
        correspond to row number in the CSV file.
        :param initial_value: the initial value of `event_count`.
        """
        self.event_count = initial_value

    def get_monitor_name(self) -> str:
        """
        Returns the unqualified name (not including the module) of the monitor.
        :return: the monitor name.
        """
        return self.__class__.__name__

    def key(self, event) -> Optional[object]:
        """
        Returns indexing key of event. Returns None by default but can be
        overridden by the user.
        :param event: event to extract index from.
        :return: the index of the event.
        """
        return None

    def monitor_this(self, *monitors: "Monitor"):
        """
        Records one or more monitors as sub-monitors of this monitor.
        Each event submitted to this monitor is also submitted to the
        sub-monitors. Likewise when `end()` is called on this monitor,
        `end()` is also called on the sub-monitors.
        :param monitors: the monitors to record as sub-monitors.
        """
        for monitor in monitors:
            monitor.is_top_monitor = False
            self.monitors.append(monitor)

    def is_relevant(self, event: Event) -> bool:
        """
        Returns True if the event should be monitored. By default all submitted events
        are monitored. This method is meant to be overridden by the user.
        :param event: the incoming event.
        :return: True if the event should be monitored.
        """
        return True

    def eval(self, event: Event):
        """
          This method is used to submit events to the monitor.
          The monitor evaluates the event against the states in the state vector.
          The `eval` method is called recursively on sub-monitors, so it is only
          necessary to call it on the topmost monitor.
          :param event: the submitted event.
          """
        self.event_count += 1
        if Debug.DEBUG_PROGRESS and self.is_top_monitor and self.event_count % Debug.DEBUG_PROGRESS == 0:
            debug(f'---------------------> {self.event_count}')
        if Debug.DEBUG and self.is_top_monitor:
            debug_frame("=", f'Event {self.event_count} {event}')
        for monitor in self.monitors:
            monitor.eval(event)
        if Debug.DEBUG:
            debug_frame("#", f'Monitor {self.get_monitor_name()}')
        if self.is_relevant(event):
            index = self.key(event)
            if index is None:
                new_states = self.eval_states(event, self.states)
                if new_states is not None:
                    self.states = new_states
                for (idx, states) in self.states_indexed.items():
                    new_states = self.eval_states(event, states)
                    if new_states is not None:
                        self.states_indexed[idx] = new_states
            else:
                if index in self.states_indexed:
                    states = self.states_indexed[index]
                else:
                    states = self.states
                new_states = self.eval_states(event, states)
                if new_states is not None:
                    self.states_indexed[index] = new_states
        if Debug.DEBUG:
            debug(f'\n{self}')

    def eval_states(self, event: Event, states: Set[State]) -> Optional[Set[State]]:
        """
        Evaluates an event on each state in a set of states.
        :param event: the event to evaluate.
        :param states: the set of states to evaluate it on.
        :return: the resulting set of states. None is returned if no transitions fired.
        """
        transition_triggered = False
        states_to_remove = set([])
        states_to_add = set([])
        new_states = set([])
        for source_state in states:
            resulting_states = source_state.eval(event)
            if Debug.DEBUG:
                debug(f'{source_state} results in {mk_string("[",", ","]", resulting_states)}')
            transition_triggered = True
            states_to_remove.add(source_state)
            for target_state in resulting_states:
                if isinstance(target_state, OkState):
                    pass
                elif isinstance(target_state, ErrorState):
                    self.report_transition_error(source_state, event, target_state)
                elif isinstance(target_state, InfoState):
                    self.report_transition_information(source_state, event, target_state)
                else:
                    self.add_state_to_state_vector(states_to_add, target_state)
        if transition_triggered:
            new_states = states
            new_states = new_states - states_to_remove
            new_states = new_states.union(states_to_add)
            return new_states
        else:
            return None

    def end(self):
        """
        Terminates monitoring for the monitor. This includes looking for hot states
        of type `HotState`, which should not occur, and then printing out a summary
        of the verification. The `end()` method is called recursively on sub-monitors,
        so it only needs to be called on the top-most monitor.
        """
        if self.is_top_monitor:
            print()
            print('Terminating monitoring!')
            print()
        for monitor in self.monitors:
            monitor.end()
        print_frame("+", f'Terminating monitor {self.get_monitor_name()}')
        for state in self.get_all_states():
            if isinstance(state, HotState) or isinstance(state, HotNextState):
                self.report_end_error(f'terminates in hot state {state}')
        if self.is_top_monitor and self.option_print_summary:
            self.print_summary()

    def verify(self, trace: List[Event]):
        '''
        Verifies a trace, which is a list of events.
        It calls `eval` on each event and calls `end()` at the
        end of the trace.
        :param trace: the trace.
        '''
        for event in trace:
            self.eval(event)
        self.end()

    def __str__(self) -> str:
        monitor_name = self.__class__.__name__
        suffix = " states:"
        bar_length = len(monitor_name) + len(suffix)
        result = f'{"-" * bar_length}\n'
        result += monitor_name + suffix + "\n"
        for state in self.states:
            result += f'{state}\n'
        for (index, states) in self.states_indexed.items():
            if states:
                result += f'index {index}:\n'
                for state in states:
                    result += f'  {state}\n'
        result += f'{"-" * bar_length}\n'
        return result

    def add_state_to_state_vector(self, states: Set[State], state: State):
        """
        Adds a state to a state vector. Also sets the monitor field of the state
        to self (the monitor the state is part of).
        :param states: the state vector to add state to.
        :param state: the state to become initial states.
        """
        state.set_monitor_to(self)
        states.add(state)

    def report_transition_error(self, state: State, event: Event, error_state: ErrorState):
        """
        Reports an error caused by taking a transition that results in an ErrorState.
        :param state: the state in which the transition is taken.
        :param event: the event that causes the transition to be taken.
        :param error_state: the error state.
        """
        text = f'*** error transition in {self.get_monitor_name()}:\n'
        if self.option_show_state_event:
            text += f'    state {state}\n'
            text += f'    event {self.event_count} {event}\n'
        text += f'    {error_state.text}'
        self.messages.append(Message(text, error_state.data))
        print(text)

    def report_transition_information(self, state: State, event: Event, info_state: InfoState):
        """
        Reports a message caused by taking a transition that results in an `InfoState`.
        This is not considered as an error necessarily.
        :param state: the state in which the transition is taken.
        :param event: the event that causes the transition to be taken.
        :param info_state: the info state.
        """
        text = f'--- message from {self.get_monitor_name()}:\n'
        text += f'    {info_state.text}'
        self.messages.append(Message(text, info_state.data))
        print(text)

    def report_end_error(self, text: str):
        """
        Reports a hot state (`HotState`) encountered in the state vector of the monitor
        at the end of monitoring, when the `end()` method is called.
        :param text: error message, identifying the hot state.
        """
        message = f'*** error at end in {self.get_monitor_name()}:\n'
        message += f'    {text}'
        self.messages.append(Message(message, None))
        print(message)

    def report_error(self, text: str, obj: object = None):
        """
        Reports an error. Usually called by user when not using state machines.
        :param text: error message.
        :param obj: a data object.
        """
        message = f'*** error in {self.get_monitor_name()}:\n'
        message += f'    {text}'
        self.messages.append(Message(message, obj))
        print(message)

    def report_information(self, text: str, obj: object = None):
        """
        Reports a message. Usually called by user when not using state machines.
        :param text: message.
        :param obj: data object.
        """
        message = f'--- message from {self.get_monitor_name()}:\n'
        message += f'    {text}'
        self.messages.append(Message(message, obj))
        print(message)

    def exists(self, predicate: Callable[[State], bool]) -> bool:
        """
        Returns True if there exists a state s in the monitor's state vector, for
        which predicate(s) is True.
        :param predicate: the predicate to apply to states in the state vector.
        :return: True if a state exists in the state vector for which the predicate is True.
        """
        return any(predicate(state) for state in self.get_all_states())

    def contains_state(self, state: State) -> bool:
        """
        A specialized version of exists, where we just check for whether
        a state is in the state vector.
        :param state: the state to check membership for.
        :return: True if the state is in the state vector.
        """
        return state in self.get_all_states()

    def get_all_states(self) -> Set[State]:
        """
        Returns all the states of a monitor. These include the main set of states
        as well as the states in the indexed slices, if any exist.
        :return: all states of the monitor.
        """
        result = self.states.copy()
        for (index, states) in self.states_indexed.items():
            result = result.union(states)
        return result

    def get_message_count(self) -> int:
        """
        Returns the number of messages reported by the monitor. It is the sum
        of the messages reported by this monitor plus the messages reported by
        sub-monitors (recursively).
        :return: the number of messages reported.
        """
        result = len(self.messages)
        for monitor in self.monitors:
            result += monitor.get_message_count()
        return result

    def get_all_message_texts(self) -> List[str]:
        """
        Returns all texts of messages recorded by this monitor, including those of sub-monitors
        (recursively).
        :return: the message texts recorded by this monitor.
        """
        return [msg.text for msg in self.get_all_messages()]

    def get_all_messages(self) -> List[Message]:
        """
        Returns all messages recorded by this monitor, including those of sub-monitors
        (recursively). Each message is represented by a `Message` object.
        :return: the messages recorded by this monitor.
        """
        result = self.messages.copy()
        for monitor in self.monitors:
            result += monitor.get_all_messages()
        return result

    def number_of_states(self) -> int:
        """
        Returns number of states stored.
        :return: number of states stored.
        """
        result = len(self.states)
        for (idx, states) in self.states_indexed.items():
            result += len(states)
        for monitor in self.monitors:
            result += monitor.number_of_states()
        return result

    def print_summary(self):
        """
        Prints a summary of all messages reported by this monitor,
        including those of sub-monitors (recursively). It is only supposed to
        be called on the topmost monitor.
        """
        print()
        print("================")
        print("Analysis result:")
        print("================")
        print()
        messages = self.get_all_message_texts()
        if messages:
            print(f'{len(messages)} messages!')
            for message in messages:
                print()
                print(message)
        else:
            print('No messages!')
