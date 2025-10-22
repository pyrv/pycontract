# transform.py
from __future__ import annotations
from typing import List, Optional
from lark import Transformer, Token, Tree
from ast_nodes import *

def tval(x) -> str:
    return str(x)

class ASTBuilder(Transformer):
    # ---------- token normalizers ----------
    def PYCODE(self, tok: Token): return str(tok)
    def NAME(self, tok: Token):   return str(tok)
    def NUMBER(self, tok: Token): return str(tok)
    def STRING(self, tok: Token): return str(tok)

    # ---------- root ----------
    def start(self, items):
        events: List[EventDef] = []
        monitors: List[Monitor] = []
        for it in items:
            if isinstance(it, EventDef):
                events.append(it)
            else:
                monitors.append(it)
        return Program(events, monitors)

    # ---------- events ----------
    def eventdef_one(self, items):   # from: eventdef: oneeventdef -> eventdef_one
        return items[0]

    def one_eventdef(self, items):   # from: oneeventdef: EVENT eventsignature -> one_eventdef
        # items = [Token('EVENT'), EventSig]
        return OneEventDef(items[1])

    def eventdef_multi(self, items): # from: eventdef: multieventdef -> eventdef_multi
        return items[0]

    def multi_eventdef(self, items): # from: multieventdef: EVENTS NAME LBRACE eventsignature+ RBRACE
        # items = [Token('EVENTS'), group_name(str), Token('LBRACE'), EventSig..., Token('RBRACE')]
        group = items[1]
        sigs  = [it for it in items if isinstance(it, EventSig)]
        return MultiEventDef(group, sigs)

    def event_sig(self, items):
        name   = tval(items[0])
        params = items[1] if len(items) > 1 else None
        return EventSig(name, params)

    def params(self, items):      return items[0]
    def param_list(self, items):  return items
    def param(self, items):       return Param(tval(items[0]), items[1])
    def type_int(self, _):        return 'int'
    def type_float(self, _):      return 'float'
    def type_str(self, _):        return 'str'

    # ---------- monitor ----------
    def monitor(self, items):
        # Robust classifier (no brittle index-walking)
        ignore = False
        name: Optional[str] = None
        typeparam: Optional[str] = None
        include: Optional[List[str]] = None
        pycode: Optional[str] = None
        transitions: List[Transition] = []
        states: List[StateDef] = []

        saw_monitor = False
        for it in items:
            if isinstance(it, Token):
                if it.type == 'IGNORE':
                    ignore = True
                elif it.type == 'MONITOR':
                    saw_monitor = True
                elif it.type == 'NAME' and saw_monitor and name is None:
                    name = str(it)
                # skip braces/tokens otherwise
            elif isinstance(it, str):
                # either typeparam (plain name) or top-level PYCODE
                if it.startswith('{:'):
                    pycode = it
                else:
                    typeparam = it
            elif isinstance(it, list) and (not it or isinstance(it[0], str)):
                include = it
            elif isinstance(it, (Case, Veto)):
                transitions.append(it)
            elif isinstance(it, StateDef):
                states.append(it)

        return Monitor(ignore, name, typeparam, include, pycode, transitions, states)

    def typeparam(self, items): return tval(items[0])
    def include(self, items):   return items[0]
    def name_list(self, items): return [tval(x) for x in items]

    # ---------- transitions ----------
    def transition_case(self, items): return items[0]
    def transition_veto(self, items): return items[0]

    def case(self, items):
        # CASE eventpat COLON? statement* targetstate_list?
        i = 0
        if isinstance(items[i], Token) and items[i].type == 'CASE':
            i += 1
        pat = items[i];
        i += 1
        if i < len(items) and isinstance(items[i], Token) and items[i].type == 'COLON':
            i += 1
        stmts, targets = [], None
        for it in items[i:]:
            if isinstance(it, Stmt):
                stmts.append(it)
            elif isinstance(it, TargetList):
                targets = it
            elif isinstance(it, list) and (not it or isinstance(it[0], (AtomicTarget, TargetSeqThen))):
                targets = TargetList(it)
        return Case(pat, stmts, targets)

    def veto(self, items):
        i = 0
        if isinstance(items[i], Token) and items[i].type == 'VETO':
            i += 1
        return Veto(items[i])

    # ---------- event patterns ----------
    def event_pat(self, items):
        name = tval(items[0]); args=None; cond=None
        for it in items[1:]:
            if isinstance(it, list):
                args = it
            elif isinstance(it, Expr):
                cond = it
        return EventPat(name, args, cond)

    def arg_pats(self, items):     return items[0] if items else []
    def argpat_list(self, items):  return items

    # ArgPat* keep ValuePat directly
    def argpat_named(self, items): return ArgPatNamed(tval(items[0]), items[1])
    def argpat_pos(self, items):   return ArgPatPos(items[0])
    def argpat_wild(self, _):      return ArgPatWild()

    # valuepat -> ValuePat(kind, value)
    def vpat_name(self,  items): return ValuePat('name',  tval(items[0]))
    def vpat_nameq(self, items): return ValuePat('nameq', tval(items[0]))
    def vpat_num(self,   items): return ValuePat('num',   tval(items[0]))
    def vpat_str(self,   items): return ValuePat('str',   tval(items[0]))

    def cond_if(self, items): return items[0]

    # ---------- statements ----------
    def stmt_call(self, items):   return StmtCall(items[0])
    def stmt_assert(self, items): return StmtAssert(items[0])
    def stmt_emit(self, items):   return StmtEmit(tval(items[0]), items[1])
    def stmt_py(self, items):     return StmtPy(tval(items[0]))

    def event(self, items):
        name = tval(items[0])
        args = items[1] if len(items) > 1 else []
        return Event(name, args)

    def args(self, items):     return items[0] if items else []
    def arg_list(self, items): return items
    def arg_named(self, items):return ArgNamed(tval(items[0]), items[1])
    def arg_pos(self, items):  return ArgPos(items[0])

    # ---------- targets / states ----------
    def tgt_stateinstance(self, items):
        return items[0]

    def tgt_ok(self, items):
        return items[0]

    def tgt_error(self, items):
        return items[0]

    def tgt_inlined(self, items):
        return items[0]

    def tgt_composite(self, items):
        return items[0]

    def tgt_composite_not(self, items):
        return items[0]

    def target_list(self, items):
        # items may look like: [Target, Token('COMMA'), Target, Token('COMMA'), ...]
        cleaned = []
        for it in items:
            if isinstance(it, (AtomicTarget, TargetSeqThen)):
                cleaned.append(it)
            # ignore commas and any other tokens
            # (if any wrapper Trees remain, they should already be unwrapped by tgt_* methods)
        return TargetList(cleaned)

    def targetstate(self, items):   # unwrap wrapper node
        return items[0]

    def target_atomic(self, items): # atomictargetstate -> AtomicTarget
        return items[0]

    def target_seq_then(self, items):
        seq  = items[0]
        then = items[1] if len(items) > 1 else None
        return TargetSeqThen(seq, then)

    def event_seq(self, items):
        # keep only the EventSpec children (drop LBRACKET/RBRACKET tokens)
        specs = [it for it in items if isinstance(it, EventSpec)]
        return EventSeq(specs)

    def event_spec(self, items):
        if len(items) == 2:
            return EventSpec(tval(items[0]), items[1])  # '?' or '!'
        return EventSpec(None, items[0])

    # atomic target builders
    def state_instance(self, items):
        name = tval(items[0]); args = items[1] if len(items) > 1 else []
        return TgtStateInstance(name, args)

    def ok_simple(self, items):
        # children: Token('OK'), optional message(str)
        msg = None
        for it in items:
            if not isinstance(it, Token):  # message already a str via message()
                msg = tval(it)
        return TgtOk(msg)

    def ok_if(self, items):
        # children: Token('OKIF'), Token('LPAREN'), expr, Token('RPAREN'), optional message(str)
        cond = None
        msg = None
        for it in items:
            if isinstance(it, Expr):
                cond = it
            elif not isinstance(it, Token):  # message is a str (from message())
                msg = tval(it)
        return TgtOkIf(cond, msg)

    def error(self, items):
        msg = tval(items[0]) if items else None
        return TgtError(msg)

    def message(self, items): return tval(items[0])

    def state_inlined(self, items):
        stype, body = items
        return TgtInlined(stype, body)

    def state_composite(self, items):
        # composer LBRACKET targetstate_list RBRACKET
        kind = items[0]  # 'and' | 'or' | 'seq'
        tlist = None
        for it in items[1:]:
            if isinstance(it, TargetList):
                tlist = it
                break
            if isinstance(it, list) and (not it or isinstance(it[0], (AtomicTarget, TargetSeqThen))):
                tlist = TargetList(it)
                break
        if tlist is None:
            tlist = TargetList([])
        return TgtComposite(kind, tlist)

    def state_not(self, items):
        # NOT targetstate
        return TgtNot(items[1])

    def comp_and(self, _): return 'and'
    def comp_or(self, _):  return 'or'
    def comp_seq(self, _): return 'seq'

    # ---------- state definitions ----------

    def state_def(self, items):
        # items for: INITIAL? statetype NAME parameters? statebody?
        i = 0
        initial = False
        if i < len(items) and isinstance(items[i], Token) and items[i].type == 'INITIAL':
            initial = True
            i += 1

        stype = items[i];
        i += 1  # from st_state/st_hot/... -> 'state'|'hot'|...
        name = tval(items[i]);
        i += 1  # NAME -> str via NAME()

        params = None
        if i < len(items) and isinstance(items[i], list) and (
                not items[i] or isinstance(items[i][0], Param)
        ):
            params = items[i]
            i += 1

        body = None
        if i < len(items) and isinstance(items[i], StateBody):
            body = items[i]

        return StateDef(initial, stype, name, params, body)

    # ---------- expressions ----------
    def expr(self, items):   return items[0]

    def op_or(self, items):  return BinOp('or',  items[0], items[1])
    def op_and(self, items): return BinOp('and', items[0], items[1])
    def op_not(self, items): return UnOp('not',  items[0])

    def compare(self, items):
        if len(items) == 1:
            return Compare(items[0], None, None)
        left, op_tok, right = items
        return Compare(left, tval(op_tok), right)

    def add(self, items): return BinOp('+', items[0], items[1])
    def sub(self, items): return BinOp('-', items[0], items[1])
    def mul(self, items): return BinOp('*', items[0], items[1])
    def div(self, items): return BinOp('/', items[0], items[1])
    def neg(self, items): return UnOp('-', items[0])

    def num(self, items): return Num(tval(items[0]))
    def str(self, items): return Str(tval(items[0]))
    def var(self, items): return Var(tval(items[0]))

    def func_call(self, items):
        return Call(tval(items[0]), items[1])

    def call(self, items):   # primary_expr -> call
        return items[0]

    def pycode(self, items): # primary_expr -> PYCODE
        return Str(tval(items[0]))  # or keep as raw string if preferred

    def exists(self, items):
        # EXISTS NAME argumentpats? (WHERE expr)?
        var = tval(items[0]); argp=None; where=None
        for it in items[1:]:
            if isinstance(it, list): argp = it
            elif isinstance(it, Expr): where = it
        return Exists(var, argp, where)

    def group(self, items):  return items[0]
