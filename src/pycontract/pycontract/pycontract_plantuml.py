import os

from .pycontract_core import *
import ast
from enum import Enum


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


def next_fork_state() -> str:
    """
    Allocates a new fork state.
    :return: the new fork state.
    """
    global fork_state_counter
    fork_state_counter += 1
    return f'fork_state{fork_state_counter}'


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


def find_transitions(source_state: str, event: str, conditions: List[str], stmts: List[ast.stmt], number: int = None) -> List["AstTransition"]:
    """
    Returns a list of transitions from a given program point in a transition function.
    :param source_state: the source state of the transition.
    :param event: the event. Initially the argument to the transition function, but can change
        due to pattern matching, where the patterns become the events.
    :param conditions: the conditions collected so far along the current path.
    :param stmts: the next list of statements to explore. It picks the last of
    these and explores from there on.
    :param number: number of case entry in encountered match-statement. Only used if more than one entry.
    :return: the transitions collected.
    """
    if not stmts:
        return []
    stmt = stmts[-1] # get the last statement
    if isinstance(stmt, ast.Return):
        # Return(expr? value)
        returned_expr = stmt.value
        if isinstance(returned_expr, ast.Call):
            # Call(expr func, expr* args, keyword* keywords)
            called_thing = returned_expr.func
            if isinstance(called_thing, ast.Attribute):
                # Attribute(expr value, identifier attr, expr_context ctx)
                target_state: ast.identifier = called_thing.attr
            else:
                # Name(identifier id, expr_context ctx)
                target_state: ast.identifier = called_thing.id
            args: List[str] = [ast.unparse(arg) for arg in returned_expr.args]
            transition = AstTransition(source_state, event, conditions, target_state, args, number)
            return [transition]
        elif isinstance(returned_expr, ast.List):
            # List(expr* elts, expr_context ctx)
            calls = returned_expr.elts
            fork_state = next_fork_state()
            to_fork_transition = AstTransition(source_state, event, conditions, fork_state, [], number)
            transitions = [to_fork_transition]
            for call in calls:
                if isinstance(call, ast.Call):
                    # Call(expr func, expr* args, keyword* keywords)
                    called_thing = call.func
                    if isinstance(called_thing, ast.Attribute):
                        # Attribute(expr value, identifier attr, expr_context ctx)
                        target_state: ast.identifier = called_thing.attr
                    else:
                        # Name(identifier id, expr_context ctx)
                        target_state: ast.identifier = called_thing.id
                    args: List[str] = [ast.unparse(arg) for arg in call.args]
                    transition = AstTransition(fork_state, None, None, target_state, args)
                    transitions += [transition]
            return transitions
        elif isinstance(returned_expr, ast.Name) and returned_expr.id == 'ok':
            transition = AstTransition(source_state, event, conditions, returned_expr.id, [], number)
            return [transition]
        else:
            # TODO:
            # assert False,  f'returned expressions not a state: {ast.unparse(returned_expr)}'
            transition = AstTransition(source_state, event, conditions, 'INTERNAL', [], number)
            return [transition]
    elif isinstance(stmt, ast.If):
        # If(expr test, stmt* body, stmt* orelse)
        true_condition = ast.unparse(stmt.test)
        false_condition = f'__not__({true_condition})'
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
    FORK = 8


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
        if self.kind == AstStateKind.NEXT or self.kind == AstStateKind.HOTNEXT or self.kind == AstStateKind.ALWAYSNEXT:
            result += f'  state "{self.name} **next**" as {self.name}'
        else:
            result += f'  state {self.name}'
        if self.kind == AstStateKind.HOT or self.kind == AstStateKind.HOTNEXT:
            result += ' #yellow'
        if self.kind == AstStateKind.ALWAYS or self.kind == AstStateKind.ALWAYSNEXT:
            result += ' #green'
        if self.kind == AstStateKind.ERROR:
            result += ' #red'
        if self.kind == AstStateKind.FORK:
            result += ' <<fork>>'
        if self.parameters:
            result += f' : {self.parameters}'
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

    def __str__(self):
        result = '@startuml\n'
        # result += '!theme plain\n'
        result += f'state {self.name}' + '{\n'
        other_super_classes = [clazz for clazz in self.super_classes if clazz != 'Monitor']
        if other_super_classes:
            result += '  note as SUPER #aliceblue\n'
            result += f'   **extends** {mk_string(other_super_classes, ",")}\n'
            result += '  end note\n'
        if self.key:
            result += '  note as KEYNOTE\n'
            result += f'   {self.key}\n'
            result += '  end note\n'
        for state in self.states:
            result += f'{state}\n'
        for tran in self.transitions:
            result += f'{tran}\n'
        result += '}\n'
        result += '@enduml'
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

    def extends_monitor(self, bases: List[str]) -> bool:
        """
        Returns True if 'Monitor' is amongst a list of super classes.
        :param bases: the direct super classes.
        :return: True if 'Monitor' is amongst the super classes.
        """
        return 'Monitor' in bases or exists(self.monitors)(lambda m: m.name in bases)

    def visit_ClassDef(self, node):
        """
        Visits classes in the monitor. Two kinds of classes are of interest:
        - the monitor class itself
        - the inner classes of the monitor representing states
        :param node: the AST node to visit.
        """
        bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
        if self.extends_monitor(bases):
            self.current_monitor = AstMonitor(node.name, bases)
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
        else:
            if extends_state(bases):
                decorators = [name.id for name in node.decorator_list]
                init = 'initial' in decorators
                data_class = 'data' in decorators
                kind = get_kind(bases)
                init_functions = [f for f in node.body if isinstance(f,ast.FunctionDef) and f.name == '__init__']
                params = None
                if init_functions:
                    # handle parameters in __init__ function
                    init_function = init_functions[0]
                    args = [param.strip() for param in ast.unparse(init_function.args).split(',')[1:]]
                    params = mk_string(args, '\\n')
                elif data_class:
                    # handle parameters in data class
                    args = get_args_from_dataclass_body(node.body)
                    params = mk_string(args, '\\n')
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
            if self.current_state is None:
                # it is an outer transition, default initial state is an always-state
                self.current_state = AstState('__Always__', True, AstStateKind.ALWAYS)
                self.current_monitor.states.append(self.current_state)
            event = node.args.args[1].arg
            transitions = find_transitions(self.current_state.name, event, [], node.body)
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


def visualize(monitor_file: str, png: bool = True):
    """
    Generates PlantUML diagrams from monitors in file.
    :param monitor_file: Python script containing monitors.
    :param png: True of a png file should be generated in addition to a plantuml source file.
    """
    with open(monitor_file, "r") as source:
        tree = ast.parse(source.read())
        analyzer = Analyzer()
        analyzer.visit(tree)
        analyzer.visualize(monitor_file, png)



