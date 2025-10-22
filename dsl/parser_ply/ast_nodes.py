# ast_nodes.py

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Union
from enum import Enum

#----------- Enumerated types -----

class Prefix(Enum):
    QMARK = "?"
    BANG  = "!"

class CompositeKind(Enum):
    AND = "and"
    OR  = "or"
    SEQ = "seq"

class TypeKind(Enum):
    INT   = "int"
    FLOAT = "float"
    STR   = "str"

#----------- Expressions ----------

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
class Exists(Expr):
    var: str
    argpats: List[ArgPat]
    where: Optional[Expr]

#---------- Args / Patterns ----------

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

class ValuePat: ...

@dataclass
class ValuePatName:
    name: str

@dataclass
class ValuePatNameQ:
    name: str

@dataclass
class ValuePatNum:
    value: str

@dataclass
class ValuePatStr:
    value: str

#---------- Events, statements ----------

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

#---------- Targets / sequences ----------

@dataclass
class EventSpec:
    prefix: Optional[Prefix]
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
class TgtComposite(AtomicTarget):
    kind: CompositeKind
    targets: List[Target]

@dataclass
class TgtNot(AtomicTarget): inner: Target

@dataclass
class TargetSeqThen(Target):
    seq: EventSeq
    then: Optional[AtomicTarget]

#---------- Event patterns / transitions ----------

@dataclass
class EventPat:
    name: str
    args: List[ArgPat]
    cond: Optional[Expr]

class Transition: ...

@dataclass
class Case(Transition):
    pat: EventPat
    statements: List[Stmt]
    targets: List[Target]

@dataclass
class Veto(Transition):
    pat: EventPat

#---------- States ----------

@dataclass
class StateBody:
    transitions: List[Transition]

@dataclass
class Param:
    name: str
    typ: TypeKind

@dataclass
class StateDef:
    initial: bool
    stype: str
    name: str
    params: List[Param]
    body: Optional[StateBody]

#---------- Events section ----------

class EventDef: ...

@dataclass
class EventSig:
    name: str
    params: List[Param]

@dataclass
class OneEventDef(EventDef): sig: EventSig

@dataclass
class MultiEventDef(EventDef): group: str; sigs: List[EventSig]

#---------- Monitor / Program ----------

@dataclass
class Monitor:
    ignore: bool
    name: str
    typeparam: Optional[str]
    include: List[str]
    pycode: Optional[str]
    transitions: List[Transition]
    states: List[StateDef]

@dataclass
class Program:
    events: List[EventDef]
    monitors: List[Monitor]
