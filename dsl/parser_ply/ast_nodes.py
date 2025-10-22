# ast_nodes.py

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Union

# ---------- Expressions ----------

class Expr: ...

@dataclass
class Num(Expr): value: str

@dataclass
class Str(Expr): value: str

@dataclass
class Var(Expr): name: str

@dataclass
class Call(Expr):
    name: str
    args: List[Arg]

@dataclass
class BinOp(Expr):
    op: str
    left: Expr
    right: Expr

@dataclass
class UnOp(Expr):
    op: str
    expr: Expr

@dataclass
class Compare(Expr):
    left: Expr
    op: Optional[str]     # None means just `left`
    right: Optional[Expr]

@dataclass
class Exists(Expr):
    var: str
    argpats: Optional[List['ArgPat']]
    where: Optional[Expr]

# ---------- Args / Patterns ----------

class Arg: ...

@dataclass
class ArgNamed(Arg): name: str; expr: Expr

@dataclass
class ArgPos(Arg): expr: Expr

class ArgPat: ...

@dataclass
class ArgPatNamed(ArgPat): name: str; value: ValuePat

@dataclass
class ArgPatPos(ArgPat): value: ValuePat

@dataclass
class ArgPatWild(ArgPat): pass

@dataclass
class ValuePat:
    kind: str   # 'name'|'nameq'|'num'|'str'
    value: str

# ---------- Events, statements ----------

@dataclass
class Event:
    name: str
    args: List[Arg]

class Stmt: ...

@dataclass
class StmtCall(Stmt): call: Call

@dataclass
class StmtAssert(Stmt): expr: Expr

@dataclass
class StmtEmit(Stmt): channel: str; event: Event

@dataclass
class StmtPy(Stmt): code: str

# ---------- Targets / sequences ----------

@dataclass
class EventSpec:
    prefix: Optional[str]     # '?' or '!' or None
    pat: EventPat

@dataclass
class EventSeq:
    specs: List[EventSpec]

class Target: ...

class AtomicTarget(Target): ...

@dataclass
class TgtStateInstance(AtomicTarget): name: str; args: List[Arg]

@dataclass
class TgtOk(AtomicTarget): message: Optional[str]

@dataclass
class TgtOkIf(AtomicTarget): cond: Expr; message: Optional[str]

@dataclass
class TgtError(AtomicTarget): message: Optional[str]

@dataclass
class TgtInlined(AtomicTarget): stype: str; body: StateBody

@dataclass
class TgtComposite(AtomicTarget): kind: str; targets: TargetList   # 'and'|'or'|'seq'

@dataclass
class TgtNot(AtomicTarget): inner: Target

@dataclass
class TargetSeqThen(Target):
    seq: EventSeq
    then: Optional[AtomicTarget]

@dataclass
class TargetList:
    items: List[Target]

# ---------- Event patterns / transitions ----------

@dataclass
class EventPat:
    name: str
    args: Optional[List[ArgPat]]
    cond: Optional[Expr]

class Transition: ...

@dataclass
class Case(Transition):
    pat: EventPat
    statements: List[Stmt]
    targets: Optional[TargetList]

@dataclass
class Veto(Transition):
    pat: EventPat

# ---------- States ----------

@dataclass
class StateBody:
    transitions: List[Transition]

@dataclass
class Param:
    name: str
    typ: str  # 'int'|'float'|'str'

@dataclass
class StateDef:
    initial: bool
    stype: str   # 'state'|'hot'|'next'|'notnext'|'always'
    name: str
    params: Optional[List[Param]]
    body: Optional[StateBody]

# ---------- Events section ----------

class EventDef: ...

@dataclass
class EventSig:
    name: str
    params: Optional[List[Param]]

@dataclass
class OneEventDef(EventDef): sig: EventSig

@dataclass
class MultiEventDef(EventDef): group: str; sigs: List[EventSig]

# ---------- Monitor / Program ----------

@dataclass
class Monitor:
    ignore: bool
    name: str
    typeparam: Optional[str]
    include: Optional[List[str]]
    pycode: Optional[str]
    transitions: List[Transition]
    states: List[StateDef]

@dataclass
class Program:
    events: List[EventDef]
    monitors: List[Monitor]
