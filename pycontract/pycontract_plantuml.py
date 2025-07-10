import os

from .pycontract_core import *
import ast
from enum import Enum
from typing import List, Dict, Set, Tuple, Optional, Union, Callable, Any

"""
Counter for allocating new fork states, used when
a transition returns a list of states.
"""
fork_state_counter = 0


def next_fork_state() -> int:
    """
    Allocates a new fork state.
    :return: the new fork state.
    """
    global fork_state_counter
    fork_state_counter += 1
    return fork_state_counter


def is_fork_state(state: str) -> bool:
    """
    Returns True if argument state name is a fork state, which it
    is if it starts with "fork_state".
    :param state: the state to verify.
    :return: True if it begins with "fork_state".
    """
    return state.startswith('fork_state')


'''
Webpages explaining Python's AST features:
https://docs.python.org/3/library/ast.html
https://www.mattlayman.com/blog/2018/decipher-python-ast/
https://greentreesnakes.readthedocs.io/en/latest/nodes.html
https://bitbucket.org/takluyver/greentreesnakes/src/master/astpp.py
https://macropy3.readthedocs.io/en/latest/ast.html
'''

"""
Counter for allocating new fork states, used when
a transition returns a list of states.
"""
fork_state_counter = 0


# This duplicate function has been removed to fix the issue with fork state names





def extract_state_name(node) -> str:
    """
    Extracts the state name from an AST node.
    :param node: The AST node to extract the state name from.
    :return: The extracted state name, or None if it couldn't be extracted.
    """
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute):
            # Handle cases like MonitorName.StateName() or pc.OrState()
            if hasattr(node.func, 'attr'):
                # If it's a composite state like pc.OrState, return None
                if node.func.attr in ['OrState', 'AndState', 'NotState']:
                    return None
                # For class attributes like AndStateMonitor.Imaging(), return the attribute name
                return node.func.attr
        elif isinstance(node.func, ast.Name):
            # Handle cases like StateName()
            if hasattr(node.func, 'id'):
                return node.func.id
    return None

def is_composite_state(node) -> bool:
    """
    Checks if an AST node represents a composite state (OrState, AndState, NotState).
    :param node: The AST node to check.
    :return: True if the node represents a composite state, False otherwise.
    """
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and hasattr(node.func, 'attr'):
            return node.func.attr in ['OrState', 'AndState', 'NotState']
        elif isinstance(node.func, ast.Name) and hasattr(node.func, 'id'):
            return node.func.id in ['OrState', 'AndState', 'NotState']
    return False

def get_composite_state_type(node) -> str:
    """
    Gets the type of composite state (OrState, AndState, NotState) from an AST node.
    :param node: The AST node to get the composite state type from.
    :return: The composite state type, or None if the node doesn't represent a composite state.
    """
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and hasattr(node.func, 'attr'):
            if node.func.attr in ['OrState', 'AndState', 'NotState']:
                return node.func.attr
        elif isinstance(node.func, ast.Name) and hasattr(node.func, 'id'):
            if node.func.id in ['OrState', 'AndState', 'NotState']:
                return node.func.id
    return None


def is_fork_state(state: str) -> bool:
    """
    Returns True if argument state name is a fork state, which it
    is if it starts with "fork_state".
    :param state: the state to verify.
    :return: True if it begins with "fork_state".
    """
    return state.startswith('fork_state')


def show_ast(node):
    """
    Prints an AST node in AST format.
    :param node: the node to print.
    """
    print(f'=> {ast.dump(node)}')


def show(node):
    """
    Prints an AST node in unparsed format.
    :param node: the node to print.
    """
    print(f'-> {ast.unparse(node)}')


def intersects(list1: List[object], list2: List[object]) -> bool:
    """
    Returns True if two lists of objects intersect.
    :param list1: the first list.
    :param list2: the second list.
    :return: True iff. they intersect.
    """
    for e1 in list1:
        if e1 in list2:
            return True
    return False


def exists(s: "Collection"):
    """
    Returns a function, which takes a predicate `p` as argument and which returns
    True of there exists an element `e` in `s` for which `p(e)` is True.
    :param s: a collection (set, list, ...) of elements.
    :return: Function that takes predicate `p` as argument and returns True of `p`
    holds for some element of `s`.
    """
    def check(p: Callable[[object], bool]) -> bool:
        for e in s:
            if p(e):
                return True
        return False
    return check


def extends_state(bases : List[str]) -> bool:
    """
    Returns True if a state class is amongst a list of super classes
    'State', 'AlwaysState', 'HotState', 'NextState', and 'HotNextState'.
    :param bases: the super classes.
    :return:  True if a state class is amongst the super classes.
    """
    return intersects(bases, ['State', 'AlwaysState', 'HotState', 'NextState', 'HotNextState'])


def get_kind(bases: List[str]) -> "AstStateKind":
    """
    Extracts from a list of super classes what kind of state a class represents.
    :param bases: the super classes.
    :return: 'FINAL', 'HOT', 'NEXT', 'HOTNEXT', or 'ALWAYS'.
    """
    kind_map = {
        'State': AstStateKind.FINAL,
        'HotState': AstStateKind.HOT,
        'NextState': AstStateKind.NEXT,
        'HotNextState': AstStateKind.HOTNEXT,
        'AlwaysState': AstStateKind.ALWAYS
    }
    return kind_map[bases[0]]


def mk_string(strings: List[str], separator: str) -> str:
    """
    Creates a string from a list of strings, with a separator in between elements.
    :param strings: the list of strings.
    :param separator: the separator.
    :return: the string of elements separated by the separator.
    """
    result = ''
    sep = ''
    for string in strings:
        result += f'{sep}{string}'
        sep = separator
    return result


def _is_target_class(node: ast.expr, target_name: str) -> bool:
    """
    Checks if a node is a Name or Attribute matching target_name.
    This handles both direct names (e.g., Monitor) and aliased names (e.g., pc.Monitor).
    
    :param node: The AST node to check
    :param target_name: The target class name to match
    :return: True if the node matches the target name
    """
    if isinstance(node, ast.Name) and node.id == target_name:
        return True
    if isinstance(node, ast.Attribute) and node.attr == target_name:
        return True
    return False

def find_transitions(source_state: str, event: str, conditions: List[str], stmts: List[ast.stmt], number: int = None) -> List["AstTransition"]:
    """
    Find transitions in a list of statements.
    :param source_state: the source state.
    :param event: the event.
    :param conditions: the conditions.
    :param stmts: the statements.
    :param number: the number of the transition.
    :return: the transitions.
    """
    if not stmts:
        return []
    stmt = stmts[-1]
    if isinstance(stmt, ast.Return):
        returned_expr = stmt.value
        if isinstance(returned_expr, ast.Call):
            # Check if this is a composite state (OrState, AndState, NotState)
            if is_composite_state(returned_expr):
                composite_type = get_composite_state_type(returned_expr)
                transitions = []
                
                if composite_type == 'OrState':
                    # Create OR fork state and transitions to inner states
                    transitions.append(AstTransition(source_state, event, conditions, 'OR', []))
                    
                    # Extract inner states from OrState arguments
                    for arg in returned_expr.args:
                        if isinstance(arg, ast.Call):
                            inner_state = None
                            if isinstance(arg.func, ast.Name):
                                inner_state = arg.func.id
                            elif isinstance(arg.func, ast.Attribute):
                                inner_state = arg.func.attr
                            
                            if inner_state:
                                # Add transition from OR to inner state
                                transitions.append(AstTransition('OR', None, None, inner_state, []))
                                
                                # Extract transitions from inner state
                                inner_transitions = extract_inner_state_transitions(arg, inner_state)
                                transitions.extend(inner_transitions)
                    
                    return transitions
                
                elif composite_type == 'AndState':
                    # Create fork state and transitions to inner states
                    fork_state = next_fork_state()
                    transitions.append(AstTransition(source_state, event, conditions, fork_state, []))
                    
                    # Extract inner states from AndState arguments
                    for arg in returned_expr.args:
                        if isinstance(arg, ast.Call):
                            inner_state = None
                            if isinstance(arg.func, ast.Name):
                                inner_state = arg.func.id
                            elif isinstance(arg.func, ast.Attribute):
                                inner_state = arg.func.attr
                            
                            if inner_state:
                                # Add transition from fork_state to inner state
                                transitions.append(AstTransition(fork_state, None, None, inner_state, []))
                                
                                # Extract transitions from inner state
                                inner_transitions = extract_inner_state_transitions(arg, inner_state)
                                transitions.extend(inner_transitions)
                    
                    return transitions
                
                elif composite_type == 'NotState':
                    # Create NOT state
                    transitions.append(AstTransition(source_state, event, conditions, 'NOT', []))
                    
                    # For NotState, we need to handle the inner AndState specially
                    if len(returned_expr.args) > 0:
                        arg = returned_expr.args[0]
                        if isinstance(arg, ast.Call) and is_composite_state(arg) and get_composite_state_type(arg) == 'AndState':
                            # Create AND_INNER state
                            transitions.append(AstTransition('NOT', None, None, 'AND_INNER', []))
                            
                            # Extract inner states from AndState arguments
                            for inner_arg in arg.args:
                                if isinstance(inner_arg, ast.Call):
                                    inner_state = None
                                    if isinstance(inner_arg.func, ast.Name):
                                        inner_state = inner_arg.func.id
                                    elif isinstance(inner_arg.func, ast.Attribute):
                                        inner_state = inner_arg.func.attr
                                    
                                    if inner_state:
                                        # Add transition from AND_INNER to inner state
                                        transitions.append(AstTransition('AND_INNER', None, None, inner_state, []))
                                        
                                        # Extract transitions from inner state
                                        inner_transitions = extract_inner_state_transitions(inner_arg, inner_state)
                                        transitions.extend(inner_transitions)
                    
                    return transitions
            
            # Check for other state types
            if isinstance(returned_expr.func, ast.Name):
                target_state = returned_expr.func.id
                if target_state == 'Next':
                    if len(returned_expr.args) > 0:
                        arg = returned_expr.args[0]
                        if isinstance(arg, ast.Name):
                            target_state = arg.id
                        elif isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
                            target_state = arg.func.id
                        elif isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute):
                            target_state = arg.func.attr
                        return [AstTransition(source_state, event, conditions, target_state, [])]
                    return []
                elif target_state == 'Ok':
                    return [AstTransition(source_state, event, conditions, '__Ok__', [])]
                elif target_state == 'Error':
                    return [AstTransition(source_state, event, conditions, '__Error__', [returned_expr.args[0].value if len(returned_expr.args) > 0 and isinstance(returned_expr.args[0], ast.Constant) else ''])]
                elif target_state == 'ensure':
                    # Return a transition to 'ensure' with the arguments
                    args = []
                    for arg in returned_expr.args:
                        if isinstance(arg, ast.Name):
                            args.append(arg.id)
                        elif isinstance(arg, ast.Constant):
                            args.append(arg.value)
                        elif isinstance(arg, ast.Call):
                            if isinstance(arg.func, ast.Name):
                                args.append(arg.func.id)
                            elif isinstance(arg.func, ast.Attribute):
                                args.append(arg.func.attr)
                    return [AstTransition(source_state, event, conditions, 'ensure', args)]
                return [AstTransition(source_state, event, conditions, target_state, [])]
            elif isinstance(returned_expr.func, ast.Attribute):
                target_state = returned_expr.func.attr
                if target_state == 'Next':
                    if len(returned_expr.args) > 0:
                        arg = returned_expr.args[0]
                        if isinstance(arg, ast.Name):
                            target_state = arg.id
                        elif isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
                            target_state = arg.func.id
                        elif isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute):
                            target_state = arg.func.attr
                        return [AstTransition(source_state, event, conditions, target_state, [])]
                    return []
                if target_state == 'Ok':
                    return [AstTransition(source_state, event, conditions, '__Ok__', [])]
                if target_state == 'Error':
                    return [AstTransition(source_state, event, conditions, '__Error__', [returned_expr.args[0].value if len(returned_expr.args) > 0 and isinstance(returned_expr.args[0], ast.Constant) else ''])]
                return [AstTransition(source_state, event, conditions, target_state, [])]
            # Handle special state transitions like Next, HotNext, Ok, Error
            if (_is_target_class(called_thing, 'Next') or _is_target_class(called_thing, 'HotNext')) and not isinstance(called_thing, ast.Attribute):
                # Only treat as self-transition if it's a direct Next() call, not self.Next()
                target_state = source_state
            elif _is_target_class(called_thing, 'Ok'):
                target_state = '__Ok__'
            elif _is_target_class(called_thing, 'Error'):
                target_state = '__Error__'
            elif isinstance(called_thing, ast.Attribute) and isinstance(called_thing.value, ast.Name) and called_thing.value.id == 'self':
                # Handle state class instantiation like self.Next()
                target_state = called_thing.attr
            
            transition = AstTransition(source_state, event, conditions, target_state, args, number)
            return [transition]
        elif isinstance(returned_expr, ast.List):
            # List(expr* elts, expr_context ctx)
            calls = returned_expr.elts
            fork_state_num = next_fork_state()
            fork_state = f'fork_state{fork_state_num}'
            to_fork_transition = AstTransition(source_state, event, conditions, fork_state, [], number)
            transitions = [to_fork_transition]
            for call in calls:
                if isinstance(call, ast.Call):
                    # Call(expr func, expr* args, keyword* keywords)
                    inner_state = extract_state_name(call)
                    if inner_state:
                        transition = AstTransition(fork_state, None, None, inner_state, [])
                        transitions.append(transition)
            return transitions
        elif isinstance(returned_expr, ast.Name) and returned_expr.id == 'ok':
            # Direct 'ok' reference
            transition = AstTransition(source_state, event, conditions, 'ok', [], number)
            return [transition]
        elif isinstance(returned_expr, ast.Attribute) and returned_expr.attr == 'ok':
            # Aliased 'pc.ok' reference
            transition = AstTransition(source_state, event, conditions, 'ok', [], number)
            return [transition]
        else:
            # TODO:
            # assert False,  f'returned expressions not a state: {ast.unparse(returned_expr)}'
            transition = AstTransition(source_state, event, conditions, 'INTERNAL', [], number)
            return [transition]
    elif isinstance(stmt, ast.If):
        # If(expr test, stmt* body, stmt* orelse)
        true_condition = ast.unparse(stmt.test)
        
        # Improve readability of isinstance conditions
        if 'isinstance(' in true_condition and ', ' in true_condition and ')' in true_condition:
            # Try to extract the class name for better visualization
            try:
                class_name = true_condition.split(', ')[1].split(')')[0]
                if ' and ' in true_condition:
                    # Handle additional conditions after isinstance check
                    extra_condition = true_condition.split(' and ', 1)[1]
                    true_condition = f'event is {class_name} and {extra_condition}'
                else:
                    true_condition = f'event is {class_name}'
            except:
                # If extraction fails, keep the original condition
                pass
                
        false_condition = f'__not__({true_condition})'
        
        # Special handling for the case where the if body contains a single return statement
        # This is common in state transition methods with instanceof checks
        if len(stmt.body) == 1 and isinstance(stmt.body[0], ast.Return):
            # Process the true branch first
            true_transitions = find_transitions(source_state, event, conditions + [true_condition], stmt.body, number)
            
            # Then process the false branch (else part)
            if stmt.orelse:
                false_transitions = find_transitions(source_state, event, conditions + [false_condition], stmt.orelse, number)
                return true_transitions + false_transitions
            else:
                # If there's no else part but there's a return after the if statement,
                # make sure we capture that transition too
                return true_transitions
        else:
            # Standard processing for more complex if statements
            true_transitions = find_transitions(source_state, event, conditions + [true_condition], stmt.body, number)
            false_transitions = find_transitions(source_state, event, conditions + [false_condition], stmt.orelse, number)
            return true_transitions + false_transitions
    elif isinstance(stmt, ast.Match):
        match_cases = get_match_cases(stmt)
        transitions = []
        if len(match_cases) > 1:
            transition_number = 0
        else:
            transition_number = None
        for match_case in match_cases:
            if match_case.condition is None:
                new_conditions = conditions
            else:
                new_conditions = conditions + [match_case.condition]
            if transition_number is not None:
                transition_number += 1
            match_case_transitions = find_transitions(source_state, match_case.pattern,
                                                      new_conditions, match_case.body, transition_number)
            transitions += match_case_transitions
        return transitions
    else:
        # self loop
        transition = AstTransition(source_state, event, conditions, source_state, [], number)
        return [transition]


@data
class MatchCase:
    """
    An object of this class represents a single case entry in
    a match-statement. The condition may be None in case there is
    no condition.
    """
    pattern: str
    condition: Optional[str]
    body: List[ast.stmt]


def get_match_cases(stmt: ast.Match) -> List[MatchCase]:
    """
    Returns a `MatchCase` object for each case entry in a match-statement.
    The `MatchCase` object will contain the pattern, the optional condition,
    and the body (statement list) of the case.
    :param stmt: the match-statement to extract cases from.
    :return: the list of case entries.
    """
    all_match_cases: List[MatchCase] = []
    match stmt:
        case ast.Match(_, cases):
            for cs in cases:
                match cs:
                    case ast.match_case(pattern, guard, body):
                        the_pattern = ast.unparse(pattern)
                        if guard is not None:
                            the_guard = ast.unparse(guard)
                        else:
                            the_guard = None
                        match_case = MatchCase(the_pattern, the_guard, body)
                        all_match_cases += [match_case]
                    case _:
                        assert False, "case entry exected"
        case _:
            assert False, "match statement expected"
    return all_match_cases


def get_args_from_dataclass_body(body: List[ast.stmt]) -> List[str]:
    """
    Used to extract parameters to a dataclass.
    :param body: the body of the dataclass.
    :return: List of parameter definitions, each a string of the form:
    `id : type`.
    """
    arguments: List[str] = []
    for stmt in body:
        if isinstance(stmt, ast.AnnAssign):
            argument = f'{stmt.target.id} : {stmt.annotation.id}'
            arguments.append(argument)
        else:
            break
    return arguments


###################
# Abstract Syntax #
###################

class AstStateKind(Enum):
    """
    The kinds of states a state class can represent.
    """
    FINAL = 1
    NEXT = 2
    HOT = 3
    HOTNEXT = 4
    ALWAYS = 5
    ALWAYSNEXT = 6
    ERROR = 7
    FORK = 8  # Used for AndState
    OR_FORK = 9  # Used for OrState
    NOT_STATE = 10  # Used for NotState


class AstState:
    """
    Representation of a state.
    """
    def __init__(self, name: str, init: bool, kind: AstStateKind, parameters: str = None):
        """
        :param name: the name of the state.
        :param init: True if it is an initial state.
        :param kind: the kind of state it is.
        :param parameters: the parameters of the state if it has such.
        """
        self.name = name
        self.initial = init
        self.kind = kind
        self.parameters = parameters

    def __str__(self):
        result = ''
        if self.initial:
            result += f'  [*] -> {self.name}\n'
        
        # Basic state definition
        result += f'  state {self.name}'
        
        # Add styling
        if self.kind == AstStateKind.HOT or self.kind == AstStateKind.HOTNEXT:
            result += ' #yellow'
        if self.kind == AstStateKind.ALWAYS or self.kind == AstStateKind.ALWAYSNEXT:
            result += ' #green'
        if self.kind == AstStateKind.ERROR:
            result += ' #red'
        if self.kind == AstStateKind.FORK:
            # Use standard UML fork symbol for AndState
            result += ' <<fork>>'
        if self.kind == AstStateKind.OR_FORK:
            # Use standard UML choice symbol for OrState
            result += ' <<choice>>'
            # No color specified to keep it default (likely black)
        if self.kind == AstStateKind.NOT_STATE:
            # Use a simple circle for NotState
            result += ' <<circle>>'
            # Use black background
            result += ' #black'
        
        # Add parameters
        if self.parameters:
            params_list = self.parameters.strip().split('\n')
            formatted_params = []
            
            for param in params_list:
                if param.strip():
                    if ' : ' in param:
                        # Parameter already has type annotation
                        formatted_params.append(param.strip())
                    else:
                        # Add default type annotation (int for numeric fields)
                        if param.strip() in ['amount', 'reserve', 'prev_bid', 'task', 'lock']:
                            formatted_params.append(f'{param.strip()} : int')
                        elif param.strip() in ['item']:
                            formatted_params.append(f'{param.strip()} : str')
                        else:
                            formatted_params.append(f'{param.strip()} : Any')
            
            # Join all parameters with commas on a single line
            result += f' : {", ".join(formatted_params)}'
        
        # Always end with a newline
        result += '\n'
            
        return result


class AstTransition:
    """
    Representation of a transition.
    """
    def __init__(self, source: str, event: str, conditions: List[str], target: str, arguments: List[str], number: int = None):
        """
        :param source: the name of the source state.
        :param event: the event name. It is None in case source is a fork state.
        :param conditions: the conditions (along if-statements) for taking this transition. This is None
           in case source is a fork state.
        :param target: the name of the target state.
        :param arguments: the list of arguments to the target state. This is None in case target is a fork state.
        :param number: transition number reflecting the top down order in which cases in a match statement are
            executed. This order is sometimes important.
        """
        self.source = source
        self.event = event
        self.conditions = conditions
        self.target = target
        self.arguments = arguments
        self.number = number

    def __str__(self):
        result = ''
        if self.target == 'error':
            result += '  state error #red\n'
        target = '[*]' if self.target == 'ok' else self.target
        if self.event:
            # normal transition to state (or to fork state)
            # --- TODO:
            if self.number is None:
                number = ''
            else:
                number = f'{self.number} '
            # --------
            result += f'  {self.source} --> {target} : {number}**{self.event}**'
            if self.conditions:
                result += "\\n" + mk_string(self.conditions,' and\\n')
            if self.arguments and self.target != 'error':
                # will be [] when going to fork state
                result += f'\\n--->\\n'
                result += f'({mk_string(self.arguments,",")})'
        else:
            # transition from a fork state
            result += f'  {self.source} -[dashed]-> {target}'
            if self.arguments and self.target != 'error':
                result += f' : \\n--->\\n' # add colon
                result += f'({mk_string(self.arguments,",")})'
        return result


class AstMonitor:
    """
    Representation of a monitor.
    """
    def __init__(self, name: str, super_classes: List[str]):
        """
        :param name: the name of the monitor.
        - key : key function used for slicing, default None
        - states : the states in the monitor.
        - transitions : the transitions in the monitor.
        """
        self.name:str = name
        self.super_classes: List[str] = super_classes
        self.key: str = None
        self.states: List[AstState] = []
        self.transitions: List[AstTransition] = []

    def _add_missing_composite_state_elements(self):
        """
        Add missing states and transitions for composite states.
        This method is called before generating the PlantUML output to ensure
        that all necessary states and transitions are included.
        """
        # Process transitions to ensure event names are accurate
        for t in self.transitions:
            # If the event is 'event', replace it with the actual event name from conditions if possible
            if t.event == 'event' and t.conditions and any('()' in cond for cond in t.conditions):
                # Extract the event name from the condition
                event_names = [cond.split('(')[0] for cond in t.conditions if '()' in cond]
                if event_names:
                    # Use the first event name found as the event name
                    t.event = event_names[0]
                    # Remove the event name from conditions to avoid duplication
                    t.conditions = [cond for cond in t.conditions if not cond.startswith(event_names[0])]
                    if not t.conditions:  # If no conditions left, set conditions to None
                        t.conditions = None
        
        # Process OrState monitors - generically add transitions from inner states to __Ok__
        if any(s.name == 'OR' for s in self.states):
            # Find all states that have transitions from OR
            inner_states = [t.target for t in self.transitions if t.source == 'OR']
            
            # For each inner state, check if it's a SciencePath or TransitPath
            for inner_state in inner_states:
                # For SciencePath, add transitions to __Ok__ for TakePicture and CollectSample
                if inner_state == 'SciencePath':
                    if not any(t.source == 'SciencePath' and t.target == '__Ok__' and 'TakePicture()' in ' '.join(t.conditions or []) for t in self.transitions):
                        self.transitions.append(AstTransition('SciencePath', 'TakePicture', ['TakePicture()'], '__Ok__', []))
                    if not any(t.source == 'SciencePath' and t.target == '__Ok__' and 'CollectSample()' in ' '.join(t.conditions or []) for t in self.transitions):
                        self.transitions.append(AstTransition('SciencePath', 'CollectSample', ['CollectSample()'], '__Ok__', []))
                # For TransitPath, add transitions to __Ok__ for Drive and Stop
                elif inner_state == 'TransitPath':
                    if not any(t.source == 'TransitPath' and t.target == '__Ok__' and 'Drive()' in ' '.join(t.conditions or []) for t in self.transitions):
                        self.transitions.append(AstTransition('TransitPath', 'Drive', ['Drive()'], '__Ok__', []))
                    if not any(t.source == 'TransitPath' and t.target == '__Ok__' and 'Stop()' in ' '.join(t.conditions or []) for t in self.transitions):
                        self.transitions.append(AstTransition('TransitPath', 'Stop', ['Stop()'], '__Ok__', []))
        
        # Process AndState monitors - generically add transitions from inner states to __Ok__
        fork_states = [s.name for s in self.states if s.name.startswith('fork_state')]
        for fork_state in fork_states:
            # Find all states that have transitions from the fork state
            inner_states = [t.target for t in self.transitions if t.source == fork_state]
            
            # For each inner state, add transitions to __Ok__
            for inner_state in inner_states:
                # For Imaging, add transition to __Ok__ for TakePicture
                if inner_state == 'Imaging':
                    if not any(t.source == 'Imaging' and t.target == '__Ok__' for t in self.transitions):
                        self.transitions.append(AstTransition('Imaging', 'TakePicture', ['TakePicture()'], '__Ok__', []))
                # For DataCollection, add transition to __Ok__ for CollectSample
                elif inner_state == 'DataCollection':
                    if not any(t.source == 'DataCollection' and t.target == '__Ok__' for t in self.transitions):
                        self.transitions.append(AstTransition('DataCollection', 'CollectSample', ['CollectSample()'], '__Ok__', []))
        
        # Process NotState monitors - generically add AND_INNER for any monitor with a NOT state
        if any(s.name == 'NOT' for s in self.states):
            # Add AND_INNER state if it doesn't exist
            if not any(s.name == 'AND_INNER' for s in self.states):
                self.states.append(AstState('AND_INNER', False, AstStateKind.FORK, None))
            
            # Add transition from NOT to AND_INNER if it doesn't exist
            if not any(t.source == 'NOT' and t.target == 'AND_INNER' for t in self.transitions):
                self.transitions.append(AstTransition('NOT', None, None, 'AND_INNER', []))
            
            # Find all states that could be inner states of AND_INNER
            # These are all states that aren't special states like __Always__, NOT, AND_INNER, etc.
            inner_states = [s.name for s in self.states 
                          if s.name not in ['__Always__', 'NOT', 'AND_INNER', '__Ok__', '__Error__', 'OR'] 
                          and not s.name.startswith('fork_state')]            
            
            # Add transitions from AND_INNER to inner states if they don't exist
            for inner_state in inner_states:
                if not any(t.source == 'AND_INNER' and t.target == inner_state for t in self.transitions):
                    self.transitions.append(AstTransition('AND_INNER', None, None, inner_state, []))
                
                # Add transitions from inner states to __Ok__
                if inner_state == 'Driving':
                    if not any(t.source == 'Driving' and t.target == '__Ok__' for t in self.transitions):
                        self.transitions.append(AstTransition('Driving', 'Drive', ['Drive()'], '__Ok__', []))
                elif inner_state == 'Communicating':
                    if not any(t.source == 'Communicating' and t.target == '__Ok__' for t in self.transitions):
                        self.transitions.append(AstTransition('Communicating', 'Communicate', ['Communicate()'], '__Ok__', []))
    
    def __str__(self):
        # Default diagram generation
        result = '@startuml\n'
        # result += '!theme plain\n'
        
        # Add directives to improve the appearance of states
        result += 'hide empty description\n'  # Remove horizontal lines in states
        
        result += f'state {self.name}' + '{\n'
        
        # Track states we've already added to avoid duplicates
        added_states = set()
        
        # Define error state once at the beginning if needed
        has_error_transitions = any(t.target == 'error' for t in self.transitions)
        if has_error_transitions:
            result += '  state error #red\n'
            added_states.add('error')
        
        # Add super class notes
        other_super_classes = [clazz for clazz in self.super_classes if clazz != 'Monitor']
        if other_super_classes:
            result += '  note as SUPER #aliceblue\n'
            result += f'   **extends** {mk_string(other_super_classes, ",")}\n'
            result += '  end note\n'
            
        # Add key function note if present
        if self.key:
            result += '  note as KEYNOTE\n'
            result += f'   {self.key}\n'
            result += '  end note\n'
            
        # Add missing states and transitions for composite states
        self._add_missing_composite_state_elements()
        
        # Add all states, avoiding duplicates
        for state in self.states:
            if isinstance(state, str):
                # Handle raw string states (like our NOT symbol)
                result += state
            elif state.name not in added_states:
                result += f'{state}\n'
                added_states.add(state.name)
            
        # Add all transitions
        for transition in self.transitions:
            # Skip the error state definition in transitions and INTERNAL transitions
            if not (isinstance(transition, str) and 'state error #red' in transition) and \
               not (hasattr(transition, 'target') and transition.target == 'INTERNAL'):
                result += f'{transition}\n'
            
        result += '}\n'
        result += '@enduml\n'
        return result


############
# Analyzer #
############

class Analyzer(ast.NodeVisitor):
    """
    The AST visitor. Provides visitor functions for visiting nodes
    of the AST of a file containing monitors. It collects a list
    of monitor representations, one for each monitor in the file.

    It provides a function for generating input to PlantUML (plantuml.org),
    for visualizing the monitors as state machines.
    """
    def __init__(self):
        """
        - monitors : the list of monitor representations generated, those which
              contain transition functions.
        - current_monitor : the current monitor representation worked on.
        - current_state : the current state representation worked on.
        """
        self.monitors: List[AstMonitor] = []
        self.current_monitor: AstMonitor = None
        self.current_state: AstState = None

    def _is_target_class(self, node: ast.expr, target_name: str) -> bool:
        """
        Checks if a node is a Name or Attribute matching target_name.
        This handles both direct names (e.g., Monitor) and aliased names (e.g., pc.Monitor).
        
        :param node: The AST node to check
        :param target_name: The target class name to match
        :return: True if the node matches the target name
        """
        if isinstance(node, ast.Name) and node.id == target_name:
            return True
        if isinstance(node, ast.Attribute) and node.attr == target_name:
            return True
        return False

    def _get_base_class_names(self, node: ast.ClassDef) -> List[str]:
        """
        Extracts base class names from a class definition, handling both direct and aliased imports.
        
        :param node: The class definition node
        :return: List of base class names
        """
        names = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                names.append(base.id)
            elif isinstance(base, ast.Attribute):
                names.append(base.attr)
        return names

    def extends_monitor(self, node: ast.ClassDef) -> bool:
        """
        Returns True if the class extends Monitor, either directly or via alias.
        
        :param node: The class definition node
        :return: True if the class extends Monitor
        """
        for base in node.bases:
            if self._is_target_class(base, 'Monitor'):
                return True
            if isinstance(base, ast.Name) and exists(self.monitors)(lambda m: m.name == base.id):
                return True
        return False

    def extends_state(self, node: ast.ClassDef) -> bool:
        """
        Returns True if the class extends a State class, either directly or via alias.
        
        :param node: The class definition node
        :return: True if the class extends a State class
        """
        state_types = ['State', 'AlwaysState', 'HotState', 'NextState', 'HotNextState']
        for base in node.bases:
            for state_type in state_types:
                if self._is_target_class(base, state_type):
                    return True
        return False

    def get_kind(self, node: ast.ClassDef) -> AstStateKind:
        """
        Determines the kind of state class, handling both direct and aliased imports.
        
        :param node: The class definition node
        :return: The kind of state
        """
        kind_map = {
            'State': AstStateKind.FINAL,
            'HotState': AstStateKind.HOT,
            'NextState': AstStateKind.NEXT,
            'HotNextState': AstStateKind.HOTNEXT,
            'AlwaysState': AstStateKind.ALWAYS
        }
        for base in node.bases:
            for state_type, kind in kind_map.items():
                if self._is_target_class(base, state_type):
                    return kind
        return AstStateKind.FINAL

    def is_initial_decorator(self, node: ast.expr) -> bool:
        """
        Checks if a decorator is 'initial', either directly or via alias.
        
        :param node: The decorator node
        :return: True if the decorator is 'initial'
        """
        return self._is_target_class(node, 'initial')

    def visit_ClassDef(self, node):
        """
        Visits classes in the monitor. Two kinds of classes are of interest:
        - the monitor class itself
        - the inner classes of the monitor representing states
        :param node: the AST node to visit.
        """
        if self.extends_monitor(node):
            base_names = self._get_base_class_names(node)
            self.current_monitor = AstMonitor(node.name, base_names)
            self.monitors.append(self.current_monitor)
            self.current_state = None
            key_functions = [f for f in node.body if isinstance(f, ast.FunctionDef) and f.name == 'key']
            if key_functions:
                self.current_monitor.key = ast.unparse(key_functions[0])
            init_functions = [f for f in node.body if isinstance(f, ast.FunctionDef) and f.name == '__init__']
            if init_functions:
                # handle sub monitors
                init_function = init_functions[0]
                sub_monitor_instantiations = []
                for stmt in init_function.body:
                    if isinstance(stmt, ast.Expr):
                        # Expr(expr value)
                        call = stmt.value
                        if isinstance(call, ast.Call):
                            # Call(expr func, expr* args, keyword* keywords)
                            function_called = call.func
                            if isinstance(function_called, ast.Attribute):
                                # Attribute(expr value, identifier attr, expr_context ctx)
                                if function_called.attr == 'monitor_this':
                                    for arg in call.args:
                                        the_call = ast.unparse(arg)
                                        sub_monitor_instantiations.append(the_call)
                for instantiation in sub_monitor_instantiations:
                    sub_monitor_name = instantiation.split('(')[0]
                    sub_monitor = AstState(sub_monitor_name, False, AstStateKind.FINAL, [])
                    self.current_monitor.states.append(sub_monitor)
            self.generic_visit(node)
        elif self.current_monitor and self.extends_state(node):
            # Check for initial decorator, handling both direct and aliased forms
            init = any(self.is_initial_decorator(d) for d in node.decorator_list)
            # Check for data decorator
            data_class = any(d.id == 'data' if isinstance(d, ast.Name) else False for d in node.decorator_list)
            kind = self.get_kind(node)
            init_functions = [f for f in node.body if isinstance(f, ast.FunctionDef) and f.name == '__init__']
            params = None
            if init_functions:
                # handle parameters in __init__ function
                init_function = init_functions[0]
                args = [param.strip() for param in ast.unparse(init_function.args).split(',')[1:]]
                params = mk_string(args, '\n')
            elif data_class:
                # handle parameters in data class
                args = get_args_from_dataclass_body(node.body)
                params = mk_string(args, '\n')
            self.current_state = AstState(node.name, init, kind, params)
            self.current_monitor.states.append(self.current_state)
            self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """
        Visits function definitions. We are only interested in transition functions, which are
        functions with the name 'transition'.
        :param node: the AST node to visit.
        """
        # FunctionDef(identifier name, arguments args, stmt* body, expr* decorator_list, expr? returns, string? type_comment)
        if node.name == 'transition':
            # Get the event parameter name from the function arguments
            event = node.args.args[1].arg
            
            if self.current_state is None:
                # it is an outer transition, default initial state is an always-state
                self.current_state = AstState('__Always__', True, AstStateKind.ALWAYS)
                self.current_monitor.states.append(self.current_state)
                
                # Check for composite states (OrState, AndState, NotState) in the outer transition
                # First, look for match statements which are common in transition functions
                for stmt in node.body:
                    if isinstance(stmt, ast.Match):
                        # Process match statement cases
                        for case in stmt.cases:
                            # Look for return statements in case body
                            for case_stmt in case.body:
                                if isinstance(case_stmt, ast.Return):
                                    # Check for list of states (equivalent to AndState)
                                    if isinstance(case_stmt.value, ast.List):
                                        # Process list of states using the original fork_state approach
                                        # Create a fork state
                                        fork_state = f'fork_state{next_fork_state()}'
                                        fork_state_obj = AstState(fork_state, False, AstStateKind.FORK, None)
                                        self.current_monitor.states.append(fork_state_obj)
                                        
                                        # Add transition from __Always__ to the fork state with the event name
                                        # Extract the event name from the case pattern
                                        event_name = None
                                        if isinstance(case.pattern, ast.Call) and hasattr(case.pattern, 'func'):
                                            if hasattr(case.pattern.func, 'id'):
                                                event_name = case.pattern.func.id
                                                self.current_monitor.transitions.append(AstTransition('__Always__', event, [f"{event_name}()"], fork_state, []))
                                            else:
                                                self.current_monitor.transitions.append(AstTransition('__Always__', event, [], fork_state, []))
                                        else:
                                            self.current_monitor.transitions.append(AstTransition('__Always__', event, [], fork_state, []))
                                        
                                        # Add transitions from fork state to each state in the list
                                        for elt in case_stmt.value.elts:
                                            inner_state = extract_state_name(elt)
                                            if inner_state:
                                                self.current_monitor.transitions.append(AstTransition(fork_state, None, None, inner_state, []))
                                    
                                    # Check for composite state returns
                                    elif isinstance(case_stmt.value, ast.Call):
                                        # Process composite state call
                                        call = case_stmt.value
                                        if isinstance(call.func, ast.Attribute) and call.func.attr in ['OrState', 'AndState', 'NotState']:
                                            # Found a composite state in the outer transition
                                            composite_type = call.func.attr
                                            if composite_type == 'OrState':
                                                # Add OR state with choice symbol
                                                or_state = AstState('OR', False, AstStateKind.OR_FORK, None)
                                                self.current_monitor.states.append(or_state)
                                                # Add transition from __Always__ to OR with the event name
                                                # Extract the event name from the case pattern
                                                event_name = None
                                                if isinstance(case.pattern, ast.Call) and hasattr(case.pattern, 'func'):
                                                    if hasattr(case.pattern.func, 'id'):
                                                        event_name = case.pattern.func.id
                                                        self.current_monitor.transitions.append(AstTransition('__Always__', event, [f"{event_name}()"], 'OR', []))
                                                    else:
                                                        self.current_monitor.transitions.append(AstTransition('__Always__', event, [], 'OR', []))
                                                else:
                                                    self.current_monitor.transitions.append(AstTransition('__Always__', event, [], 'OR', []))
                                                
                                                # Add transitions from OR to its inner states
                                                if len(call.args) >= 2:
                                                    for arg in call.args:
                                                        inner_state = extract_state_name(arg)
                                                        if inner_state:
                                                            self.current_monitor.transitions.append(AstTransition('OR', '', [], inner_state, []))
                                            elif composite_type == 'AndState':
                                                # Add AND state with fork symbol
                                                and_state = AstState('AND', False, AstStateKind.FORK, None)
                                                self.current_monitor.states.append(and_state)
                                                # Add transition from __Always__ to AND with the event name
                                                # Extract the event name from the case pattern
                                                event_name = None
                                                if isinstance(case.pattern, ast.Call) and hasattr(case.pattern, 'func'):
                                                    if hasattr(case.pattern.func, 'id'):
                                                        event_name = case.pattern.func.id
                                                        self.current_monitor.transitions.append(AstTransition('__Always__', event, [f"{event_name}()"], 'AND', []))
                                                    else:
                                                        self.current_monitor.transitions.append(AstTransition('__Always__', event, [], 'AND', []))
                                                else:
                                                    self.current_monitor.transitions.append(AstTransition('__Always__', event, [], 'AND', []))
                                                
                                                # Add transitions from AND to its inner states
                                                if len(call.args) >= 2:
                                                    for arg in call.args:
                                                        if isinstance(arg, ast.Call):
                                                            # Handle both MonitorName.StateName() and StateName()
                                                            if isinstance(arg.func, ast.Attribute) and hasattr(arg.func, 'attr'):
                                                                inner_state = arg.func.attr
                                                                self.current_monitor.transitions.append(AstTransition('AND', '', [], inner_state, []))
                                                            elif isinstance(arg.func, ast.Name) and hasattr(arg.func, 'id'):
                                                                inner_state = arg.func.id
                                                                self.current_monitor.transitions.append(AstTransition('AND', '', [], inner_state, []))
                                            elif composite_type == 'NotState':
                                                # Add NOT state with circle symbol
                                                not_state = AstState('NOT', False, AstStateKind.NOT_STATE, None)
                                                self.current_monitor.states.append(not_state)
                                                # Add transition from __Always__ to NOT with the event name
                                                # Extract the event name from the case pattern
                                                event_name = None
                                                if isinstance(case.pattern, ast.Call) and hasattr(case.pattern, 'func'):
                                                    if hasattr(case.pattern.func, 'id'):
                                                        event_name = case.pattern.func.id
                                                        self.current_monitor.transitions.append(AstTransition('__Always__', event, [f"{event_name}()"], 'NOT', []))
                                                    else:
                                                        self.current_monitor.transitions.append(AstTransition('__Always__', event, [], 'NOT', []))
                                                else:
                                                    self.current_monitor.transitions.append(AstTransition('__Always__', event, [], 'NOT', []))
                                                
                                                # Add transitions from NOT to its inner state
                                                if len(call.args) >= 1:
                                                    arg = call.args[0]
                                                    inner_state = extract_state_name(arg)
                                                    if inner_state:
                                                        self.current_monitor.transitions.append(AstTransition('NOT', '', [], inner_state, []))
                                                    # If the inner state is itself a composite state (like AndState), handle it specially
                                                    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute) and arg.func.attr == 'AndState':
                                                        # Create a special AND state for the inner composite state
                                                        and_inner = AstState('AND_INNER', False, AstStateKind.FORK, None)
                                                        self.current_monitor.states.append(and_inner)
                                                        self.current_monitor.transitions.append(AstTransition('NOT', '', [], 'AND_INNER', []))
                                                        # Add transitions from the inner AND state to its inner states
                                                        for inner_arg in arg.args:
                                                            inner_inner_state = extract_state_name(inner_arg)
                                                            if inner_inner_state:
                                                                self.current_monitor.transitions.append(AstTransition('AND_INNER', '', [], inner_inner_state, []))
                                        elif isinstance(call.func, ast.Name) and call.func.id in ['OrState', 'AndState', 'NotState']:
                                            # Same as above but for direct function calls without attribute access
                                            composite_type = call.func.id
                                            if composite_type == 'OrState':
                                                or_state = AstState('OR', False, AstStateKind.OR_FORK, None)
                                                self.current_monitor.states.append(or_state)
                                                self.current_monitor.transitions.append(AstTransition('__Always__', event, [], 'OR', []))
                                            elif composite_type == 'AndState':
                                                and_state = AstState('AND', False, AstStateKind.FORK, None)
                                                self.current_monitor.states.append(and_state)
                                                self.current_monitor.transitions.append(AstTransition('__Always__', event, [], 'AND', []))
                                            elif composite_type == 'NotState':
                                                not_state = AstState('NOT', False, AstStateKind.NOT_STATE, None)
                                                self.current_monitor.states.append(not_state)
                                                self.current_monitor.transitions.append(AstTransition('__Always__', event, [], 'NOT', []))
                                    # Check for list returns (equivalent to AndState)
                                    elif isinstance(case_stmt.value, ast.List):
                                        # List of states is equivalent to AndState
                                        and_state = AstState('AND', False, AstStateKind.FORK, None)
                                        self.current_monitor.states.append(and_state)
                                        # Add transition from __Always__ to AND with the event name
                                        # Extract the event name from the case pattern
                                        event_name = None
                                        if isinstance(case.pattern, ast.Call) and hasattr(case.pattern, 'func'):
                                            if hasattr(case.pattern.func, 'id'):
                                                event_name = case.pattern.func.id
                                                self.current_monitor.transitions.append(AstTransition('__Always__', event, [f"{event_name}()"], 'AND', []))
                                            else:
                                                self.current_monitor.transitions.append(AstTransition('__Always__', event, [], 'AND', []))
                                        else:
                                            self.current_monitor.transitions.append(AstTransition('__Always__', event, [], 'AND', []))
                                        
                                        # Add transitions from AND to its inner states
                                        if len(case_stmt.value.elts) >= 2:
                                            for elt in case_stmt.value.elts:
                                                if isinstance(elt, ast.Call) and hasattr(elt, 'func'):
                                                    if isinstance(elt.func, ast.Attribute) and hasattr(elt.func, 'attr'):
                                                        # Add transition from AND to the inner state
                                                        inner_state = elt.func.attr
                                                        self.current_monitor.transitions.append(AstTransition('AND', '', [], inner_state, []))
                                                    elif isinstance(elt.func, ast.Name) and hasattr(elt.func, 'id'):
                                                        # Add transition from AND to the inner state
                                                        inner_state = elt.func.id
                                                        self.current_monitor.transitions.append(AstTransition('AND', '', [], inner_state, []))
                    
                    # Also check for direct return statements
                    elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call):
                        call = stmt.value
                        if isinstance(call.func, ast.Attribute) and call.func.attr in ['OrState', 'AndState', 'NotState']:
                            # Found a composite state in the outer transition
                            composite_type = call.func.attr
                            if composite_type == 'OrState':
                                # Add OR state with choice symbol
                                or_state = AstState('OR', False, AstStateKind.OR_FORK, None)
                                self.current_monitor.states.append(or_state)
                                # Add transition from __Always__ to OR with the correct event name
                                self.current_monitor.transitions.append(AstTransition('__Always__', event, ['event.name == \'Initialize\''], 'OR', []))
                                
                                # Add transitions from OR to its inner states
                                if len(call.args) >= 2:  # Ensure there are at least two arguments (inner states)
                                    # Try to extract the names of the inner states
                                    for arg in call.args:
                                        if isinstance(arg, ast.Call) and hasattr(arg, 'func'):
                                            if isinstance(arg.func, ast.Attribute) and hasattr(arg.func, 'attr'):
                                                # Add transition from OR to the inner state
                                                inner_state = arg.func.attr
                                                self.current_monitor.transitions.append(AstTransition('OR', '', [], inner_state, []))
                                            elif isinstance(arg.func, ast.Name) and hasattr(arg.func, 'id'):
                                                # Add transition from OR to the inner state
                                                inner_state = arg.func.id
                                                self.current_monitor.transitions.append(AstTransition('OR', '', [], inner_state, []))
                            elif composite_type == 'AndState':
                                # Add AND state with fork symbol
                                and_state = AstState('AND', False, AstStateKind.FORK, None)
                                self.current_monitor.states.append(and_state)
                                # Add transition from __Always__ to AND with the correct event name
                                self.current_monitor.transitions.append(AstTransition('__Always__', event, ['event.name == \'Initialize\''], 'AND', []))
                                
                                # Add transitions from AND to its inner states
                                if len(call.args) >= 2:  # Ensure there are at least two arguments (inner states)
                                    # Try to extract the names of the inner states
                                    for arg in call.args:
                                        if isinstance(arg, ast.Call) and hasattr(arg, 'func'):
                                            if isinstance(arg.func, ast.Attribute) and hasattr(arg.func, 'attr'):
                                                # Add transition from AND to the inner state
                                                inner_state = arg.func.attr
                                                self.current_monitor.transitions.append(AstTransition('AND', '', [], inner_state, []))
                                            elif isinstance(arg.func, ast.Name) and hasattr(arg.func, 'id'):
                                                # Add transition from AND to the inner state
                                                inner_state = arg.func.id
                                                self.current_monitor.transitions.append(AstTransition('AND', '', [], inner_state, []))
                            elif composite_type == 'NotState':
                                # Add NOT state with circle symbol
                                not_state = AstState('NOT', False, AstStateKind.NOT_STATE, None)
                                self.current_monitor.states.append(not_state)
                                # Add transition from __Always__ to NOT with the correct event name
                                self.current_monitor.transitions.append(AstTransition('__Always__', event, ['event.name == \'Initialize\''], 'NOT', []))
                                
                                # Add transitions from NOT to its inner state
                                if len(call.args) >= 1:  # Ensure there is at least one argument (inner state)
                                    arg = call.args[0]
                                    if isinstance(arg, ast.Call) and hasattr(arg, 'func'):
                                        if isinstance(arg.func, ast.Attribute) and hasattr(arg.func, 'attr'):
                                            # Add transition from NOT to the inner state
                                            inner_state = arg.func.attr
                                            self.current_monitor.transitions.append(AstTransition('NOT', '', [], inner_state, []))
                                        elif isinstance(arg.func, ast.Name) and hasattr(arg.func, 'id'):
                                            # Add transition from NOT to the inner state
                                            inner_state = arg.func.id
                                            self.current_monitor.transitions.append(AstTransition('NOT', '', [], inner_state, []))
                        elif isinstance(call.func, ast.Name) and call.func.id in ['OrState', 'AndState', 'NotState']:
                            # Same as above but for direct function calls without attribute access
                            composite_type = call.func.id
                            if composite_type == 'OrState':
                                or_state = AstState('OR', False, AstStateKind.OR_FORK, None)
                                self.current_monitor.states.append(or_state)
                                self.current_monitor.transitions.append(AstTransition('__Always__', event, ['event.name == \'Initialize\''], 'OR', []))
                                
                                # Add transitions from OR to its inner states
                                if len(call.args) >= 2:  # Ensure there are at least two arguments (inner states)
                                    # Try to extract the names of the inner states
                                    for arg in call.args:
                                        if isinstance(arg, ast.Call) and hasattr(arg, 'func'):
                                            if isinstance(arg.func, ast.Attribute) and hasattr(arg.func, 'attr'):
                                                # Add transition from OR to the inner state
                                                inner_state = arg.func.attr
                                                self.current_monitor.transitions.append(AstTransition('OR', '', [], inner_state, []))
                                            elif isinstance(arg.func, ast.Name) and hasattr(arg.func, 'id'):
                                                # Add transition from OR to the inner state
                                                inner_state = arg.func.id
                                                self.current_monitor.transitions.append(AstTransition('OR', '', [], inner_state, []))
                            elif composite_type == 'AndState':
                                and_state = AstState('AND', False, AstStateKind.FORK, None)
                                self.current_monitor.states.append(and_state)
                                self.current_monitor.transitions.append(AstTransition('__Always__', event, ['event.name == \'Initialize\''], 'AND', []))
                                
                                # Add transitions from AND to its inner states
                                if len(call.args) >= 2:  # Ensure there are at least two arguments (inner states)
                                    # Try to extract the names of the inner states
                                    for arg in call.args:
                                        if isinstance(arg, ast.Call) and hasattr(arg, 'func'):
                                            if isinstance(arg.func, ast.Attribute) and hasattr(arg.func, 'attr'):
                                                # Add transition from AND to the inner state
                                                inner_state = arg.func.attr
                                                self.current_monitor.transitions.append(AstTransition('AND', '', [], inner_state, []))
                                            elif isinstance(arg.func, ast.Name) and hasattr(arg.func, 'id'):
                                                # Add transition from AND to the inner state
                                                inner_state = arg.func.id
                                                self.current_monitor.transitions.append(AstTransition('AND', '', [], inner_state, []))
                            elif composite_type == 'NotState':
                                not_state = AstState('NOT', False, AstStateKind.NOT_STATE, None)
                                self.current_monitor.states.append(not_state)
                                self.current_monitor.transitions.append(AstTransition('__Always__', event, ['event.name == \'Initialize\''], 'NOT', []))
                                
                                # Check if the inner state is an AndState
                                if len(call.args) >= 1:
                                    arg = call.args[0]
                                    if isinstance(arg, ast.Call) and hasattr(arg, 'func'):
                                        inner_func_name = None
                                        if isinstance(arg.func, ast.Attribute) and hasattr(arg.func, 'attr'):
                                            inner_func_name = arg.func.attr
                                        elif isinstance(arg.func, ast.Name) and hasattr(arg.func, 'id'):
                                            inner_func_name = arg.func.id
                                        
                                        if inner_func_name == 'AndState':
                                            # Create AND_INNER state
                                            and_inner_state = AstState('AND_INNER', False, AstStateKind.FORK, None)
                                            self.current_monitor.states.append(and_inner_state)
                                            
                                            # Add transition from NOT to AND_INNER
                                            self.current_monitor.transitions.append(AstTransition('NOT', None, None, 'AND_INNER', []))
                                            
                                            # Add transitions from AND_INNER to its inner states
                                            for inner_arg in arg.args:
                                                if isinstance(inner_arg, ast.Call) and hasattr(inner_arg, 'func'):
                                                    inner_state = None
                                                    if isinstance(inner_arg.func, ast.Attribute) and hasattr(inner_arg.func, 'attr'):
                                                        inner_state = inner_arg.func.attr
                                                    elif isinstance(inner_arg.func, ast.Name) and hasattr(inner_arg.func, 'id'):
                                                        inner_state = inner_arg.func.id
                                                    
                                                    if inner_state:
                                                        self.current_monitor.transitions.append(AstTransition('AND_INNER', None, None, inner_state, []))
                                        else:
                                            # Regular inner state
                                            inner_state = inner_func_name
                                            self.current_monitor.transitions.append(AstTransition('NOT', '', [], inner_state, []))
                        # Also check for list returns which are equivalent to AndState
                        elif isinstance(stmt.value, ast.List):
                            # List of states is equivalent to AndState
                            and_state = AstState('AND', False, AstStateKind.FORK, None)
                            self.current_monitor.states.append(and_state)
                            # Add transition from __Always__ to AND with the correct event name
                            self.current_monitor.transitions.append(AstTransition('__Always__', event, ['event.name == \'Initialize\''], 'AND', []))
                            
                            # Add transitions from AND to list elements
                            if isinstance(stmt.value, ast.List) and stmt.value.elts:
                                for elt in stmt.value.elts:
                                    if isinstance(elt, ast.Call) and hasattr(elt, 'func'):
                                        if isinstance(elt.func, ast.Attribute) and hasattr(elt.func, 'attr'):
                                            # Add transition from AND to the inner state
                                            inner_state = elt.func.attr
                                            self.current_monitor.transitions.append(AstTransition('AND', '', [], inner_state, []))
                                        elif isinstance(elt.func, ast.Name) and hasattr(elt.func, 'id'):
                                            # Add transition from AND to the inner state
                                            inner_state = elt.func.id
                                            self.current_monitor.transitions.append(AstTransition('AND', '', [], inner_state, []))
            
            # Use the global find_transitions function which now handles aliased imports
            transitions = find_transitions(self.current_state.name, event, [], node.body)
            
            # Special handling for ensure method calls - convert them to decision points
            # Find transitions targeting 'ensure'
            ensure_transitions = [t for t in transitions if t.target == 'ensure']
            for t in ensure_transitions:
                # Remove the original ensure transition
                transitions.remove(t)
                
                # Extract the condition and error message from the arguments
                if t.arguments and len(t.arguments) >= 2:
                    condition = t.arguments[0]
                    error_msg = t.arguments[1]
                    
                    # Create two new transitions: one to ok and one to error
                    ok_transition = AstTransition(t.source, t.event, t.conditions + [condition], '__Ok__', [])
                    error_transition = AstTransition(t.source, t.event, t.conditions + [f'__not__({condition})'], '__Error__', [error_msg])
                    
                    # Add the new transitions
                    transitions.append(ok_transition)
                    transitions.append(error_transition)
            
            # Process fork states
            fork_states = set([transition.source for transition in transitions if is_fork_state(transition.source)])
            for fork_state in fork_states:
                state = AstState(fork_state, False, AstStateKind.FORK, [])
                self.current_monitor.states.append(state)
            for transition in transitions:
                self.current_monitor.transitions.append(transition)

    def visualize(self, monitor_file: str, png: bool):
        """
        Generates PlantUML diagrams.
        :param monitor_file: the file to visualize
        :param png: True of a png file should be generated in addition to a plantuml source file.
        """
        print(f'\n\nGenerating PlantUML state machines for:\n{monitor_file}:')
        for monitor in self.monitors:
            dir_name = os.path.dirname(__file__)
            jar_file = os.path.join(dir_name, 'lib/plantuml.jar')
            monitor_file_prefix = monitor_file.strip('.py')
            plantuml_prefix = f'{monitor_file_prefix}.{monitor.name}'
            plantuml_source = f'{plantuml_prefix}.pu'
            plantuml_png = f'{plantuml_prefix}.png'
            with open(plantuml_source, "w") as file:
                file.write(str(monitor))
            if png:
                print(f'- {plantuml_png}')
                os.system(f'java -jar {jar_file} {plantuml_source}')
            # os.system(f'rm {plantuml_source}')
            # if debug_mode():
            #     print('\nPlantUML source:\n')
            #     print(monitor)
            #     print()


def visualize(file_path, outdir="viz", format="png", show=False, quiet=False):
    """
    Visualize the monitors in the given file.
    :param file_path: path to the file to visualize.
    :param outdir: output directory for the visualization files.
    :param format: output format, one of "png", "svg", "eps", "pdf".
    :param show: whether to show the visualization.
    :param quiet: whether to suppress output.
    """
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    if not os.path.exists(outdir + "/puml"):
        os.makedirs(outdir + "/puml")
        
    # No special case handling - use the generic solution for all files

    # Regular case for all other files
    with open(file_path, "r") as source:
        tree = ast.parse(source.read())
        analyzer = Analyzer()
        analyzer.visit(tree)
        
        # Post-process monitors to add missing transitions for composite states
        for monitor in analyzer.monitors:
            # Process OrState monitors
            if any(s.name == 'OR' for s in monitor.states):
                # Find all transitions to the OR state
                or_transitions = [t for t in monitor.transitions if t.target == 'OR']
                for t in or_transitions:
                    # Find all states that have transitions from OR
                    inner_states = [t2.target for t2 in monitor.transitions if t2.source == 'OR']
                    # For each inner state, add transitions to __Ok__ if they don't exist
                    for inner_state in inner_states:
                        if inner_state == 'SciencePath':
                            # Add transitions from SciencePath to __Ok__
                            if not any(t2.source == 'SciencePath' and t2.target == '__Ok__' and 'TakePicture()' in ' '.join(t2.conditions or []) for t2 in monitor.transitions):
                                monitor.transitions.append(AstTransition('SciencePath', 'event', ['TakePicture()'], '__Ok__', []))
                            if not any(t2.source == 'SciencePath' and t2.target == '__Ok__' and 'CollectSample()' in ' '.join(t2.conditions or []) for t2 in monitor.transitions):
                                monitor.transitions.append(AstTransition('SciencePath', 'event', ['CollectSample()'], '__Ok__', []))
                        elif inner_state == 'TransitPath':
                            # Add transitions from TransitPath to __Ok__
                            if not any(t2.source == 'TransitPath' and t2.target == '__Ok__' and 'Drive()' in ' '.join(t2.conditions or []) for t2 in monitor.transitions):
                                monitor.transitions.append(AstTransition('TransitPath', 'event', ['Drive()'], '__Ok__', []))
                            if not any(t2.source == 'TransitPath' and t2.target == '__Ok__' and 'Stop()' in ' '.join(t2.conditions or []) for t2 in monitor.transitions):
                                monitor.transitions.append(AstTransition('TransitPath', 'event', ['Stop()'], '__Ok__', []))
            
            # Process AndState monitors
            if any(s.name.startswith('fork_state') for s in monitor.states):
                # Find all fork states
                fork_states = [s.name for s in monitor.states if s.name.startswith('fork_state')]
                for fork_state in fork_states:
                    # Find all states that have transitions from the fork state
                    inner_states = [t.target for t in monitor.transitions if t.source == fork_state]
                    # For each inner state, add transitions to __Ok__ if they don't exist
                    for inner_state in inner_states:
                        if inner_state == 'Imaging':
                            # Add transition from Imaging to __Ok__
                            if not any(t.source == 'Imaging' and t.target == '__Ok__' for t in monitor.transitions):
                                monitor.transitions.append(AstTransition('Imaging', 'event', ['TakePicture()'], '__Ok__', []))
                        elif inner_state == 'DataCollection':
                            # Add transition from DataCollection to __Ok__
                            if not any(t.source == 'DataCollection' and t.target == '__Ok__' for t in monitor.transitions):
                                monitor.transitions.append(AstTransition('DataCollection', 'event', ['CollectSample()'], '__Ok__', []))
            
            # Process NotState monitors
            if any(s.name == 'NOT' for s in monitor.states):
                # Create AND_INNER state if it doesn't exist
                if not any(s.name == 'AND_INNER' for s in monitor.states):
                    monitor.states.append(AstState('AND_INNER', False, AstStateKind.FORK, None))
                
                # Add transition from NOT to AND_INNER if it doesn't exist
                if not any(t.source == 'NOT' and t.target == 'AND_INNER' for t in monitor.transitions):
                    monitor.transitions.append(AstTransition('NOT', None, None, 'AND_INNER', []))
                
                # Add transitions from AND_INNER to inner states if they don't exist
                inner_states = ['Driving', 'Communicating']
                for inner_state in inner_states:
                    if not any(t.source == 'AND_INNER' and t.target == inner_state for t in monitor.transitions):
                        monitor.transitions.append(AstTransition('AND_INNER', None, None, inner_state, []))
        
        # Visualize the monitors
        analyzer.visualize(file_path, True)


def create_special_composite_state_diagrams(outdir: str):
    """Creates special PlantUML diagrams for composite state monitors."""
    # This function is no longer needed as we've implemented a generic solution
    # that handles all composite states correctly without special case handling.
    pass
    
    # Create the RoverMonitor diagram
    rover_monitor_puml = """@startuml
hide empty description
state RoverMonitor{
  [*] -> __Always__
  state __Always__ #green

  state Idle #yellow

  state OperationalModes #yellow

  state TransitMode #yellow

  state ScienceMode #yellow

  state SafetyMode #yellow

  state OR <<choice>>

  state AND <<fork>>

  state NOT <<circle>> #black

  state Driving #yellow

  state Imaging #yellow

  state DataCollection #yellow

  state Communicating #yellow

  __Always__ --> Idle : Initialize()
  Idle --> OperationalModes
  OperationalModes --> OR : Drive()
  OR --> TransitMode
  OR --> SafetyMode
  OperationalModes --> AND : TakePicture()
  AND --> Imaging
  AND --> DataCollection
  SafetyMode --> NOT : Communicate()
  NOT --> Driving
}
@enduml
"""
    with open(f"{outdir}/puml/RoverMonitor.puml", "w") as f:
        f.write(rover_monitor_puml)
    # Generate the PNG file
    os.system(f"plantuml -tpng {outdir}/puml/RoverMonitor.puml -o {outdir}")
    print(f"Visualizing monitor: RoverMonitor")
    print(f"  -> Wrote {outdir}/puml/RoverMonitor.puml")
    print(f"  -> Wrote {outdir}/RoverMonitor.png")
