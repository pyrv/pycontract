# parser_ply.py
# PLY-based parser matching the given Lark grammar and producing the provided AST nodes.
# Requires: pip install ply
# Expects ast_nodes.py in the same directory.

from __future__ import annotations
import re
from pathlib import Path

import ply.lex as lex
import ply.yacc as yacc

from dsl.parser_ply.ast_nodes import *

# -----------------------------
# Lexer
# -----------------------------
reserved = {
    'event': 'EVENT',
    'events': 'EVENTS',
    'monitor': 'MONITOR',
    'include': 'INCLUDE',
    'ignore': 'IGNORE',
    'state': 'STATE',
    'hot': 'HOTSTATE',
    'next': 'NEXTSTATE',
    'hotnext': 'HOTNEXTSTATE',
    'always': 'ALWAYSSTATE',
    'initial': 'INITIAL',
    'case': 'CASE',
    'veto': 'VETO',
    'ok': 'OK',
    'error': 'ERROR',
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT',
    'seq': 'SEQ',
    'if': 'IF',
    'where': 'WHERE',
    'exists': 'EXISTS',
    'call': 'CALL',
    'assert': 'ASSERT',
    'okif': 'OKIF',
    'int': 'TYPE_INT',
    'float': 'TYPE_FLOAT',
    'str': 'TYPE_STR'
}

tokens = [
    'NAME', 'NAMEQ',
    'NUMBER', 'STRING',
    'PYCODE',

    # punctuation / operators
    'LE', 'GE', 'LT', 'GT', 'PLUS', 'MINUS', 'TIMES', 'DIV',
    'EQUAL', 'NOTEQUAL', 'QMARK', 'BANG', 'UNDERSCORE',

    # keywords (will be produced by NAME via reserved lookup)
    'EVENT','EVENTS','MONITOR','INCLUDE','IGNORE','STATE','HOTSTATE','NEXTSTATE',
    'HOTNEXTSTATE','ALWAYSSTATE','INITIAL','CASE','VETO','OK','ERROR','AND','OR',
    'NOT','SEQ','IF','WHERE','EXISTS','CALL','ASSERT','OKIF','TYPE_INT','TYPE_FLOAT','TYPE_STR',
]  # noqa: E231

# Use literals for simple single-char delimiters
literals = ['{','}','(',')','[',']',',',':']

# --- Simple tokens
t_LE       = r'<='
t_GE       = r'>='
t_LT       = r'<'
t_GT       = r'>'
t_PLUS     = r'\+'
t_MINUS    = r'-'
t_TIMES    = r'\*'
t_DIV      = r'/'
t_EQUAL    = r'='
t_NOTEQUAL = r'!='
t_QMARK    = r'\?'
t_BANG     = r'!'
t_UNDERSCORE = r'_'

def t_NUMBER(t):
    r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
    return t

def t_comment_block(t):
    r'(\"\"\"(.|\n)*?\"\"\"|\'\'\'(.|\n)*?\'\'\')'
    # keep line numbers correct
    t.lexer.lineno += t.value.count('\n')
    pass

def t_STRING(t):
    r'\"([^\\\n]|(\\.))*?\"'
    t.value = t.value  # keep the quotes per your AST design (Str.value: str)
    return t

def t_NAMEQ(t):
    r'[A-Za-z_][A-Za-z_0-9]*\?'
    return t

def t_PYCODE(t):
    r'\{\:[\s\S]*?\:\}'
    t.lexer.lineno += t.value.count('\n')   # keep error lines accurate
    t.value = t.value
    return t

def t_NAME(t):
    r'[A-Za-z_][A-Za-z_0-9]*'
    t.type = reserved.get(t.value, 'NAME')
    return t

def t_comment_line(t):
    r'\#[^\n]*'
    pass

t_ignore = ' \t\r'
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    raise SyntaxError(f"Illegal character {t.value!r} at line {t.lexer.lineno}")

lexer = lex.lex(reflags=re.DOTALL | re.MULTILINE)

# -----------------------------
# Helpers
# -----------------------------
def as_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]

def first(x, default=None):
    return x[0] if x else default

def _msg_opt(p):
    # message: '(' STRING ')'
    # Returns Optional[str]
    return p[2] if p is not None else None

# -----------------------------
# Precedence (lowest -> highest)
# -----------------------------

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('nonassoc', 'LT','LE','GT','GE','EQUAL','NOTEQUAL'),
    ('left', 'PLUS','MINUS'),
    ('left', 'TIMES','DIV'),
    ('right', 'UMINUS'),
)

# -----------------------------
# Grammar
# -----------------------------

def p_program(p):
    """program : eventdefs monitors"""
    p[0] = Program(events=as_list(p[1]), monitors=as_list(p[2]))

def p_eventdefs_many(p):
    """eventdefs : eventdefs eventdef"""
    p[0] = as_list(p[1]) + [p[2]]

def p_eventdefs_empty(p):
    """eventdefs : """
    p[0] = []

def p_monitors_many(p):
    """monitors : monitors monitor"""
    p[0] = as_list(p[1]) + [p[2]]

def p_monitors_empty(p):
    """monitors : """
    p[0] = []

def p_eventdef_one(p):
    """eventdef : oneeventdef"""
    p[0] = p[1]

def p_eventdef_multi(p):
    """eventdef : multieventdef"""
    p[0] = p[1]

def p_oneeventdef(p):
    """oneeventdef : EVENT eventsignature"""
    p[0] = OneEventDef(sig=p[2])

def p_eventsignature(p):
    """eventsignature : NAME parameters_opt"""
    p[0] = EventSig(name=p[1], params=p[2])

def p_parameters_opt(p):
    """parameters_opt : parameters
                      | """
    p[0] = p[1] if len(p) == 2 else []

def p_multieventdef(p):
    """multieventdef : EVENTS NAME '{' eventsignatures '}'"""
    p[0] = MultiEventDef(group=p[2], sigs=p[4])

def p_eventsignatures_many(p):
    """eventsignatures : eventsignatures eventsignature"""
    p[0] = as_list(p[1]) + [p[2]]

def p_eventsignatures_one(p):
    """eventsignatures : eventsignature"""
    p[0] = [p[1]]

def p_parameters(p):
    """parameters : '(' param_list ')'"""
    p[0] = p[2]

def p_param_list_many(p):
    """param_list : param_list ',' param"""
    p[0] = as_list(p[1]) + [p[3]]

def p_param_list_one(p):
    """param_list : param"""
    p[0] = [p[1]]

def p_param(p):
    """param : NAME ':' type"""
    p[0] = Param(name=p[1], typ=p[3])

def p_type(p):
    """type : TYPE_INT
            | TYPE_FLOAT
            | TYPE_STR"""
    p[0] = {'int':  TypeKind.INT,
            'float':TypeKind.FLOAT,
            'str':  TypeKind.STR}[p[1]]

def p_monitor(p):
    """monitor : IGNORE_opt MONITOR NAME typeparam_opt '{' include_opt PYCODE_opt transitions states '}'"""
    ignore = p[1]
    typeparam = p[4]
    include = p[6]
    pycode = p[7]
    transitions = p[8]
    states = p[9]
    p[0] = Monitor(
        ignore=bool(ignore),
        name=p[3],
        typeparam=typeparam,
        include=include,
        pycode=pycode,
        transitions=transitions,
        states=states
    )

def p_IGNORE_opt(p):
    """IGNORE_opt : IGNORE
                  | """
    p[0] = True if (len(p) == 2) else False

def p_typeparam_opt(p):
    """typeparam_opt : '[' NAME ']'
                     | """
    p[0] = p[2] if len(p) == 4 else None

def p_include_opt(p):
    """include_opt : INCLUDE name_list
                   | """
    p[0] = p[2] if len(p) == 3 else []

def p_name_list_many(p):
    """name_list : name_list ',' NAME"""
    p[0] = as_list(p[1]) + [p[3]]

def p_name_list_one(p):
    """name_list : NAME"""
    p[0] = [p[1]]

def p_PYCODE_opt(p):
    """PYCODE_opt : PYCODE
                  | """
    p[0] = p[1] if len(p) == 2 else None

def p_transitions_many(p):
    """transitions : transitions transition"""
    p[0] = as_list(p[1]) + [p[2]]

def p_transitions_empty(p):
    """transitions : """
    p[0] = []

def p_states_many(p):
    """states : states state"""
    p[0] = as_list(p[1]) + [p[2]]

def p_states_empty(p):
    """states : """
    p[0] = []

def p_transition_case(p):
    """transition : case"""
    p[0] = p[1]

def p_transition_veto(p):
    """transition : veto"""
    p[0] = p[1]

def p_case(p):
    """case : CASE eventpat case_colon_opt statements targetstates"""
    p[0] = Case(pat=p[2], statements=p[4], targets=p[5])

def p_case_colon_opt(p):
    """case_colon_opt : ':'
                      | """
    p[0] = None

def p_veto(p):
    """veto : VETO eventpat"""
    p[0] = Veto(pat=p[2])

def p_eventpat(p):
    """eventpat : NAME argumentpats_opt condition_opt"""
    p[0] = EventPat(name=p[1], args=p[2], cond=p[3])

def p_argumentpats_opt(p):
    """argumentpats_opt : '(' argpat_list_opt ')'
                        | """
    p[0] = p[2] if len(p) == 4 else []

def p_argpat_list_opt(p):
    """argpat_list_opt : argpat_list
                       | """
    p[0] = p[1] if len(p) == 2 else []

def p_argpat_list_many(p):
    """argpat_list : argpat_list ',' argpat"""
    p[0] = as_list(p[1]) + [p[3]]

def p_argpat_list_one(p):
    """argpat_list : argpat"""
    p[0] = [p[1]]

def p_argpat_named(p):
    """argpat : NAME EQUAL valuepat"""
    p[0] = ArgPatNamed(name=p[1], value=p[3])

def p_argpat_pos(p):
    """argpat : valuepat"""
    p[0] = ArgPatPos(value=p[1])

def p_argpat_wild(p):
    """argpat : UNDERSCORE"""
    p[0] = ArgPatWild()

def p_valuepat_name(p):
    """valuepat : NAME"""
    p[0] = ValuePatName(name=p[1])

def p_valuepat_nameq(p):
    """valuepat : NAMEQ"""
    p[0] = ValuePatNameQ(name=p[1][:-1])

def p_valuepat_num(p):
    """valuepat : NUMBER"""
    p[0] = ValuePatNum(value=p[1])

def p_valuepat_negnum(p):
    """valuepat : MINUS NUMBER"""
    p[0] = ValuePatNum(value='-' + p[2])

def p_valuepat_str(p):
    """valuepat : STRING"""
    p[0] = ValuePatStr(value=p[1])

def p_condition_opt(p):
    """condition_opt : IF '(' expr ')'
                     | """
    p[0] = p[3] if len(p) == 5 else None

def p_statements_many(p):
    """statements : statements statement"""
    p[0] = as_list(p[1]) + [p[2]]

def p_statements_empty(p):
    """statements : """
    p[0] = []

def p_statement_call(p):
    """statement : CALL func_call"""
    p[0] = StmtCall(call=p[2])

def p_statement_assert(p):
    """statement : ASSERT '(' expr ')'"""
    p[0] = StmtAssert(expr=p[3])

def p_statement_emit(p):
    """statement : NAME BANG event"""
    p[0] = StmtEmit(channel=p[1], event=p[3])

def p_statement_py(p):
    """statement : PYCODE"""
    p[0] = StmtPy(code=p[1])

def p_event(p):
    """event : NAME arguments_opt"""
    p[0] = Event(name=p[1], args=p[2] or [])

def p_arguments_opt(p):
    """arguments_opt : '(' arg_list_opt ')'
                     | """
    p[0] = p[2] if len(p) == 4 else []

def p_arg_list_opt(p):
    """arg_list_opt : arg_list
                    | """
    p[0] = p[1] if len(p) == 2 else []

def p_arg_list_many(p):
    """arg_list : arg_list ',' arg"""
    p[0] = as_list(p[1]) + [p[3]]

def p_arg_list_one(p):
    """arg_list : arg"""
    p[0] = [p[1]]

def p_arg_named(p):
    """arg : NAME EQUAL expr"""
    p[0] = ArgNamed(name=p[1], expr=p[3])

def p_arg_pos(p):
    """arg : expr"""
    p[0] = ArgPos(expr=p[1])

def p_targetstates_many(p):
    """targetstates : targetstates ',' targetstate"""
    p[0] = p[1] + [p[3]]

def p_targetstates_one(p):
    """targetstates : targetstate"""
    p[0] = [p[1]]

def p_targetstates_empty(p):
    """targetstates :"""
    p[0] = []

def p_targetstate_seq_then(p):
    """targetstate : eventsequence atomictargetstate_opt"""
    p[0] = TargetSeqThen(seq=p[1], then=p[2])

def p_atomictargetstate_opt(p):
    """atomictargetstate_opt : atomictargetstate
                             | """
    p[0] = p[1] if len(p) == 2 else None

def p_targetstate_atomic(p):
    """targetstate : atomictargetstate"""
    p[0] = p[1]

def p_eventsequence(p):
    """eventsequence : '[' eventspecs ']'"""
    p[0] = EventSeq(specs=p[2])

def p_eventspecs_many(p):
    """eventspecs : eventspecs eventspec"""
    p[0] = as_list(p[1]) + [p[2]]

def p_eventspecs_one(p):
    """eventspecs : eventspec"""
    p[0] = [p[1]]

def p_eventspec(p):
    """eventspec : eventspec_prefix_opt eventpat"""
    p[0] = EventSpec(prefix=p[1], pat=p[2])

def p_eventspec_prefix_opt(p):
    """eventspec_prefix_opt : QMARK
                            | BANG
                            | """
    p[0] = Prefix.QMARK if len(p)==2 and p[1]=='?' else (
           Prefix.BANG  if len(p)==2 and p[1]=='!'else None)

def p_atomictarget_stateinstance(p):
    """atomictargetstate : stateinstance"""
    p[0] = TgtStateInstance(name=p[1][0], args=p[1][1])

def p_atomictarget_ok(p):
    """atomictargetstate : OK message_opt"""
    p[0] = TgtOk(message=p[2])

def p_atomictarget_okif(p):
    """atomictargetstate : OKIF '(' expr ')' message_opt"""
    p[0] = TgtOkIf(cond=p[3], message=p[5])

def p_atomictarget_error(p):
    """atomictargetstate : ERROR message_opt"""
    p[0] = TgtError(message=p[2])

def p_atomictarget_inlined(p):
    """atomictargetstate : inlinedstate"""
    p[0] = p[1]

def p_atomictarget_composite(p):
    """atomictargetstate : compositestate"""
    p[0] = p[1]

def p_atomictarget_compositenot(p):
    """atomictargetstate : compositenotstate"""
    p[0] = p[1]

def p_message_opt(p):
    """message_opt : '(' STRING ')'
                   | """
    p[0] = p[2] if len(p) == 4 else None

def p_stateinstance(p):
    """stateinstance : NAME arguments_opt"""
    p[0] = (p[1], p[2] or [])

def p_inlinedstate(p):
    """inlinedstate : statetype statebody"""
    p[0] = TgtInlined(stype=p[1], body=p[2])

def p_compositestate(p):
    """compositestate : composer '[' targetstates ']'"""
    p[0] = TgtComposite(kind=p[1], targets=p[3])

def p_composer(p):
    """composer : AND
                | OR
                | SEQ"""
    p[0] = {'and': CompositeKind.AND,
            'or':  CompositeKind.OR,
            'seq': CompositeKind.SEQ}[p[1]]

def p_compositenotstate(p):
    """compositenotstate : NOT targetstate"""
    p[0] = TgtNot(inner=p[2])

def p_state(p):
    """state : INITIAL_opt statetype NAME parameters_opt statebody_opt"""
    p[0] = StateDef(
        initial=bool(p[1]),
        stype=p[2],
        name=p[3],
        params=p[4],
        body=p[5]
    )

def p_INITIAL_opt(p):
    """INITIAL_opt : INITIAL
                   | """
    p[0] = True if len(p) == 2 else False

def p_statetype(p):
    """statetype : STATE
                 | HOTSTATE
                 | NEXTSTATE
                 | HOTNEXTSTATE
                 | ALWAYSSTATE"""
    p[0] = p[1]

def p_statebody(p):
    """statebody : '{' transitions '}'"""
    p[0] = StateBody(transitions=p[2])

def p_statebody_opt(p):
    """statebody_opt : statebody
                     | """
    p[0] = p[1] if len(p) == 2 else None

def p_expr_bin(p):
    """expr : expr PLUS expr
            | expr MINUS expr
            | expr TIMES expr
            | expr DIV expr
            | expr LT expr
            | expr LE expr
            | expr GT expr
            | expr GE expr
            | expr EQUAL expr
            | expr NOTEQUAL expr
            | expr AND expr
            | expr OR expr"""
    op_tok = p.slice[2].type
    if   op_tok == 'AND':      op = 'and'
    elif op_tok == 'OR':       op = 'or'
    elif op_tok == 'LT':       op = '<'
    elif op_tok == 'LE':       op = '<='
    elif op_tok == 'GT':       op = '>'
    elif op_tok == 'GE':       op = '>='
    elif op_tok == 'EQUAL':    op = '='
    elif op_tok == 'NOTEQUAL': op = '!='
    elif op_tok == 'PLUS':     op = '+'
    elif op_tok == 'MINUS':    op = '-'
    elif op_tok == 'TIMES':    op = '*'
    elif op_tok == 'DIV':      op = '/'
    else:
        raise AssertionError(f"Unhandled operator token {op_tok}")
    p[0] = BinOp(op=op, left=p[1], right=p[3])

def p_expr_not(p):
    """expr : NOT expr"""
    p[0] = UnOp(op='not', expr=p[2])

def p_expr_unary_minus(p):
    """expr : MINUS expr %prec UMINUS"""
    p[0] = UnOp(op='-', expr=p[2])

def p_expr_group(p):
    """expr : '(' expr ')'"""
    p[0] = p[2]

def p_expr_exists(p):
    """expr : EXISTS NAME argumentpats_exists_opt where_opt"""
    p[0] = Exists(var=p[2], argpats=p[3], where=p[4])

def p_argumentpats_exists_opt(p):
    """argumentpats_exists_opt : '(' argpat_list_opt ')'
                               | """
    p[0] = p[2] if len(p) == 4 else []

def p_where_opt(p):
    """where_opt : WHERE '(' expr ')'
                 | """
    p[0] = p[3] if len(p) == 5 else None

def p_expr_call(p):
    """expr : func_call"""
    p[0] = p[1]

def p_expr_num(p):
    """expr : NUMBER"""
    p[0] = Num(value=p[1])

def p_expr_str(p):
    """expr : STRING"""
    p[0] = Str(value=p[1])

def p_expr_var(p):
    """expr : NAME"""
    p[0] = Var(name=p[1])

def p_expr_pycode(p):
    """expr : PYCODE"""
    p[0] = Str(value=p[1])  # or a dedicated node if you prefer

# func_call: NAME '(' arg_list_opt ')'
def p_func_call(p):
    """func_call : NAME '(' arg_list_opt ')'"""
    p[0] = Call(name=p[1], args=p[3] or [])

# -----------------------------
# Error handler
# -----------------------------

def p_error(p):
    if p is None:
        raise SyntaxError("Unexpected end of input")
    raise SyntaxError(f"Syntax error at {getattr(p,'value',None)!r} (type={p.type}) line={p.lineno}")

# -----------------------------
# Public API
# -----------------------------

def make_parser():
    return yacc.yacc(start='program', debug=False, write_tables=False)

def parse(text: str) -> Program:
    lx = lexer
    lx.input(text)
    parser = make_parser()
    return parser.parse(lexer=lx)

# -----------------------------
# Main
# -----------------------------

if __name__ == "__main__":
    import os
    import sys
    import json
    import dataclasses
    from typing import Any

    # --- IDE-friendly defaults ---
    USE_STDIN   = False                  # set True if you want stdin when no args
    PRINT_JSON  = False                  # set True to emit JSON
    SAMPLE_PATH = os.path.join(os.path.dirname(__file__), "sample.dsl")

    HERE = Path(__file__).resolve().parent
    SPEC = "monitor.mon"
    #SPEC = "demo1.mon"
    #SPEC = "demo2.mon"
    SAMPLE_PATH = HERE / "examples" / SPEC

    def to_dict(obj: Any):
        if dataclasses.is_dataclass(obj):
            return {k: to_dict(v) for k, v in dataclasses.asdict(obj).items()}
        if isinstance(obj, (list, tuple)):
            return [to_dict(x) for x in obj]
        if isinstance(obj, dict):
            return {k: to_dict(v) for k, v in obj.items()}
        return obj

    def pretty(obj: Any, indent: int = 0):
        pad = "  " * indent
        if dataclasses.is_dataclass(obj):
            cls = obj.__class__.__name__
            print(f"{pad}{cls}(")
            for field in dataclasses.fields(obj):
                name = field.name
                value = getattr(obj, name)
                print(f"{pad}  {name}=")
                pretty(value, indent + 2)
            print(f"{pad})")
        elif isinstance(obj, list):
            print(f"{pad}[")
            for item in obj:
                pretty(item, indent + 1)
            print(f"{pad}]")
        elif isinstance(obj, dict):
            print(f"{pad}{{")
            for k, v in obj.items():
                print(f"{pad}  {k!r}:")
                pretty(v, indent + 2)
            print(f"{pad}}}")
        else:
            print(f"{pad}{obj!r}")

    def load_text() -> str:
        # 1) Explicit file argument wins
        if len(sys.argv) >= 2 and sys.argv[1] != "--":
            with open(sys.argv[1], "r", encoding="utf-8") as f:
                return f.read()
        # 2) If a sample file exists alongside the parser, use it
        if os.path.isfile(SAMPLE_PATH):
            with open(SAMPLE_PATH, "r", encoding="utf-8") as f:
                return f.read()
        # 3) If configured to use stdin (and not attached to a TTY), read it
        if USE_STDIN and not sys.stdin.isatty():
            return sys.stdin.read()
        # 4) Fallback to demo (no hang in IDE)
        assert False

    try:
        text = load_text()
        program = parse(text)
        if PRINT_JSON:
            print(json.dumps(to_dict(program), indent=2))
        else:
            pretty(program)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
