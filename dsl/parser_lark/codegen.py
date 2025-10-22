# codegen.py
from __future__ import annotations
import ast
from functools import singledispatchmethod
from typing import List

from ast_nodes import (
    # program / monitors / events
    Program, Monitor, EventDef, OneEventDef, MultiEventDef, EventSig, Param,
    # transitions & states
    Transition, Case, Veto, StateDef, StateBody,
    # targets
    TargetList, Target, TargetSeqThen, AtomicTarget,
    TgtStateInstance, TgtOk, TgtOkIf, TgtError, TgtInlined, TgtComposite, TgtNot,
    EventSeq, EventSpec, EventPat,
    # statements
    Stmt, StmtCall, StmtAssert, StmtEmit, StmtPy, Event,
    # arguments / patterns
    Arg, ArgPos, ArgNamed, ArgPat, ArgPatPos, ArgPatNamed, ArgPatWild, ValuePat,
    # expressions
    Expr, Num, Str, Var, Call, BinOp, UnOp, Compare, Exists,
)

# ----------------------------
# Codegen: DSL -> Python (PyContract)
# ----------------------------

class CodegenPyContract:
    """
    Visitor that converts the AST into Python code (string),
    targeting PyContract-style runtime. All concrete runtime calls
    (Ok, Error, Goto, And/Or/Seq, etc.) are placeholders here — wire
    them to your actual API once you decide the mapping.
    """

    # ----------------- public API -----------------
    def translate(self, prog: Program) -> str:
        module = self._module(self.visit(prog))
        return ast.unparse(module)

    # ----------------- helpers -----------------

    def _coerce_eventpat(self, pat) -> EventPat:
        if isinstance(pat, EventPat):
            return pat
        if isinstance(pat, (str, Token)):
            # name only, no args/cond
            return EventPat(str(pat), None, None)
        raise TypeError(f"Expected EventPat/str/Token for event pattern, got {type(pat).__name__}")

    def _module(self, body_stmts: List[ast.stmt]) -> ast.Module:
        # Preamble imports — adjust to your real runtime
        preamble: List[ast.stmt] = [
            ast.ImportFrom(module="pycontract", names=[ast.alias(name="contract")], level=0),
        ]
        return ast.Module(body=preamble + body_stmts, type_ignores=[])

    def _const(self, v) -> ast.expr:
        return ast.Constant(v)

    def _name(self, s: str) -> ast.Name:
        return ast.Name(id=s, ctx=ast.Load())

    def _method(self, self_name: str, attr: str) -> ast.Attribute:
        return ast.Attribute(value=self._name(self_name), attr=attr, ctx=ast.Load())

    def _class(self, name: str, bases: List[ast.expr], body: List[ast.stmt]) -> ast.ClassDef:
        return ast.ClassDef(name=name, bases=bases, keywords=[], body=body or [ast.Pass()], decorator_list=[])

    def _def(self, name: str, args: List[str], body: List[ast.stmt]) -> ast.FunctionDef:
        return ast.FunctionDef(
            name=name,
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg=a) for a in args],
                kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=body or [ast.Pass()],
            decorator_list=[]
        )

    def _strip_quotes(self, s: str) -> str:
        return s[1:-1] if len(s) >= 2 and s[0] in "'\"" and s[-1] == s[0] else s

    def _coerce_num(self, s: str):
        # simple number coercion
        try:
            if s.isdigit() or (s.startswith('-') and s[1:].isdigit()):
                return int(s)
            return float(s)
        except Exception:
            return s  # fallback to string if parsing fails

    # ----------------- visitor -----------------

    @singledispatchmethod
    def visit(self, node):
        raise TypeError(f"No codegen for node type: {type(node).__name__}")

    # ---------- Program ----------

    @visit.register
    def _(self, node: Program) -> List[ast.stmt]:
        body: List[ast.stmt] = []
        # Events (can be emitted as stubs or registration)
        for e in node.events:
            body.extend(self.visit(e))
        # Monitors as classes
        for m in node.monitors:
            body.extend(self.visit(m))
        return body

    # ---------- Events ----------

    @visit.register
    def _(self, node: OneEventDef) -> List[ast.stmt]:
        sig: EventSig = node.sig
        name = sig.name
        params = sig.params or []
        # Example: emit simple annotated names (or register in map)
        out: List[ast.stmt] = []
        for prm in params:
            if not isinstance(prm, Param):
                continue
            typ = prm.typ  # 'int'|'float'|'str'
            out.append(ast.AnnAssign(
                target=ast.Name(id=f"{name}_{prm.name}", ctx=ast.Store()),
                annotation=ast.Name(id=typ, ctx=ast.Load()),
                value=None,
                simple=1
            ))
        return out

    @visit.register
    def _(self, node: MultiEventDef) -> List[ast.stmt]:
        out: List[ast.stmt] = []
        for sig in node.sigs:
            out.extend(self.visit(OneEventDef(sig)))
        return out

    # ---------- Monitor (maps to a class) ----------

    @visit.register
    def _(self, node: Monitor) -> List[ast.stmt]:
        bases = [ast.Attribute(value=self._name("contract"), attr="Monitor", ctx=ast.Load())]
        body: List[ast.stmt] = []

        # Optional attributes
        if node.include:
            body.append(ast.Assign(
                targets=[ast.Name(id="include", ctx=ast.Store())],
                value=ast.List(elts=[self._const(s) for s in node.include], ctx=ast.Load())
            ))
        if node.typeparam:
            body.append(ast.Assign(
                targets=[ast.Name(id="typeparam", ctx=ast.Store())],
                value=self._const(node.typeparam)
            ))
        if node.pycode:
            # Store or execute custom code — placeholder stores it as a doc expr in init hook
            body.append(self._def("_init_pycode", ["self"], [ast.Expr(self._const(node.pycode))]))

        # Emit transitions (methods) and states (nested methods)
        for t in node.transitions:
            body.extend(self.visit(t))
        for s in node.states:
            body.extend(self.visit(s))

        cls = self._class(node.name, bases, body)
        return [cls]

    # ---------- Transitions ----------

    @visit.register
    def _(self, node: Case) -> list[ast.stmt]:
        ev = self._coerce_eventpat(node.pat)

        # be robust if ev.name is a Token instead of str
        try:
            ev_name_str = ev.name if isinstance(ev.name, str) else str(ev.name)
        except Exception:
            ev_name_str = "event"  # last-resort fallback

        fname = f"on_{ev_name_str}"

        # Build method args from pattern args (named keep their names, positionals get arg1, arg2, ...)
        args = ["self"]
        if ev.args:
            pos_idx = 1
            for ap in ev.args:
                if isinstance(ap, ArgPatNamed):
                    args.append(ap.name)
                else:
                    args.append(f"arg{pos_idx}")
                    pos_idx += 1

        body: list[ast.stmt] = []

        # condition guard (if present)
        if ev.cond:
            body.append(ast.If(
                test=self.visit(ev.cond),
                body=[ast.Pass()],
                orelse=[ast.Return(value=self._const(None))]
            ))

        # statements in the case block
        for st in node.statements:
            body.extend(self.visit(st))

        # return targets descriptor (placeholder API)
        if node.targets:
            tgt = self._emit_targets(node.targets)
            body.append(ast.Return(value=tgt))
        else:
            body.append(ast.Pass())

        return [self._def(fname, args, body)]

    @visit.register
    def _(self, node: Veto) -> List[ast.stmt]:
        # veto_<event> method — placeholder returns True to veto
        ev = self._coerce_eventpat(node.pat)
        fname = f"veto_{ev.name}"
        # optional condition could drive the return value; simple stub for now
        return [self._def(fname, ["self"], [ast.Return(self._const(True))])]

    # ---------- States ----------

    @visit.register
    def _(self, node: StateDef) -> List[ast.stmt]:
        fname = f"state_{node.name}"
        body: List[ast.stmt] = []
        if node.body:
            for t in node.body.transitions:
                body.extend(self.visit(t))
        # You may want to attach metadata (initial, type) as attributes
        hdr = [
            ast.Assign(targets=[ast.Name(id="_stype", ctx=ast.Store())], value=self._const(node.stype)),
            ast.Assign(targets=[ast.Name(id="_initial", ctx=ast.Store())], value=self._const(node.initial)),
        ]
        return hdr + [self._def(fname, ["self"], body or [ast.Pass()])]

    # ---------- Statements ----------

    @visit.register
    def _(self, node: StmtCall) -> List[ast.stmt]:
        return [ast.Expr(self.visit(node.call))]

    @visit.register
    def _(self, node: StmtAssert) -> List[ast.stmt]:
        return [ast.Assert(test=self.visit(node.expr), msg=None)]

    @visit.register
    def _(self, node: StmtEmit) -> List[ast.stmt]:
        # Placeholder: self.emit('channel', Event(...))
        return [ast.Expr(ast.Call(
            func=self._method("self", "emit"),
            args=[self._const(node.channel), self._event_expr(node.event)],
            keywords=[],
        ))]

    @visit.register
    def _(self, node: StmtPy) -> List[ast.stmt]:
        # Safer to keep as literal; or exec in a controlled hook if you need execution
        return [ast.Expr(self._const(node.code))]

    # ---------- Event & args ----------

    def _event_expr(self, ev: Event) -> ast.expr:
        pos_args: list[ast.expr] = []
        kw_args: list[ast.keyword] = []
        for a in ev.args:
            if isinstance(a, ArgNamed):
                kw_args.append(ast.keyword(arg=a.name, value=self.visit(a.expr)))
            elif isinstance(a, ArgPos):
                pos_args.append(self.visit(a.expr))
            elif isinstance(a, Expr):
                pos_args.append(self.visit(a))
            else:
                pos_args.append(self._const(a))
        return ast.Call(func=self._name(ev.name), args=pos_args, keywords=kw_args)

    @visit.register
    def _(self, node: ArgPos) -> ast.expr:
        return self.visit(node.expr)

    @visit.register
    def _(self, node: ArgNamed) -> ast.keyword:
        return ast.keyword(arg=node.name, value=self.visit(node.expr))

    # ---------- Targets (descriptor placeholders) ----------

    def _emit_targets(self, tlist: TargetList) -> ast.expr:
        return ast.Tuple(elts=[self.visit(t) for t in tlist.items], ctx=ast.Load())

    @visit.register
    def _(self, node: TargetSeqThen) -> ast.expr:
        # SeqThen(event_seq, maybe_atomic)
        return ast.Call(
            func=self._name("SeqThen"),
            args=[
                self.visit(node.seq),
                self.visit(node.then) if node.then else self._const(None)
            ],
            keywords=[]
        )

    @visit.register
    def _(self, node: TgtStateInstance) -> ast.expr:
        # Goto('S', **kwargs)
        kws = []
        for a in node.args:
            if isinstance(a, ArgNamed):
                kws.append(ast.keyword(arg=a.name, value=self.visit(a.expr)))
        return ast.Call(func=self._name("Goto"), args=[self._const(node.name)], keywords=kws)

    @visit.register
    def _(self, node: TgtOk) -> ast.expr:
        return ast.Call(func=self._name("Ok"), args=[self._const(node.message) if node.message else self._const(None)], keywords=[])

    @visit.register
    def _(self, node: TgtOkIf) -> ast.expr:
        return ast.Call(func=self._name("OkIf"),
                        args=[self.visit(node.cond),
                              self._const(node.message) if node.message else self._const(None)],
                        keywords=[])

    @visit.register
    def _(self, node: TgtError) -> ast.expr:
        return ast.Call(func=self._name("Error"), args=[self._const(node.message) if node.message else self._const(None)], keywords=[])

    @visit.register
    def _(self, node: TgtInlined) -> ast.expr:
        return ast.Call(func=self._name("InlineState"),
                        args=[self._const(node.stype),
                              self.visit(node.body) if node.body else self._const(None)],
                        keywords=[])

    @visit.register
    def _(self, node: TgtComposite) -> ast.expr:
        # And/Or/Seq([...])
        ctor = node.kind.capitalize()  # 'and'|'or'|'seq' -> 'And'|'Or'|'Seq'
        return ast.Call(func=self._name(ctor), args=[self._emit_targets(node.targets)], keywords=[])

    @visit.register
    def _(self, node: TgtNot) -> ast.expr:
        return ast.Call(func=self._name("Not"), args=[self.visit(node.inner)], keywords=[])

    @visit.register
    def _(self, node: EventSeq) -> ast.expr:
        return ast.List(elts=[self.visit(s) for s in node.specs], ctx=ast.Load())

    @visit.register
    def _(self, node: EventSpec) -> ast.expr:
        # (prefix, eventpat)
        return ast.Tuple(elts=[self._const(node.prefix), self.visit(self._coerce_eventpat(node.pat))], ctx=ast.Load())

    @visit.register
    def _(self, node: EventPat) -> ast.expr:
        # Represent as ("name", [argpats] | None, cond | None)
        args = self.visit(node.args) if node.args else self._const(None)
        cond = self.visit(node.cond) if node.cond else self._const(None)
        return ast.Tuple(elts=[self._const(node.name), args, cond], ctx=ast.Load())

    @visit.register
    def _(self, node: list) -> ast.expr:  # argpat lists or general lists
        return ast.List(elts=[self.visit(x) for x in node], ctx=ast.Load())

    @visit.register
    def _(self, node: ArgPatNamed) -> ast.expr:
        return ast.Tuple(elts=[self._const("named"), self._const(node.name), self.visit(node.value)], ctx=ast.Load())

    @visit.register
    def _(self, node: ArgPatPos) -> ast.expr:
        return ast.Tuple(elts=[self._const("pos"), self.visit(node.value)], ctx=ast.Load())

    @visit.register
    def _(self, node: ArgPatWild) -> ast.expr:
        return ast.Tuple(elts=[self._const("wild")], ctx=ast.Load())

    @visit.register
    def _(self, node: ValuePat) -> ast.expr:
        return ast.Tuple(elts=[self._const(node.kind), self._const(node.value)], ctx=ast.Load())

    # ---------- State body ----------
    @visit.register
    def _(self, node: StateBody) -> ast.expr:
        # Represent as an empty list (content emitted via transitions above)
        return ast.List(elts=[], ctx=ast.Load())

    # ---------- Expressions ----------

    @visit.register
    def _(self, node: Num) -> ast.expr:
        return self._const(self._coerce_num(node.value))

    @visit.register
    def _(self, node: Str) -> ast.expr:
        return self._const(self._strip_quotes(node.value))

    @visit.register
    def _(self, node: Var) -> ast.expr:
        return self._name(node.name)

    @visit.register
    def _(self, node: Call) -> ast.expr:
        pos: list[ast.expr] = []
        kw: list[ast.keyword] = []
        for a in node.args:
            if isinstance(a, ArgNamed):
                kw.append(ast.keyword(arg=a.name, value=self.visit(a.expr)))
            elif isinstance(a, ArgPos):
                pos.append(self.visit(a.expr))
            elif isinstance(a, Expr):
                # allow bare Expr as a positional arg
                pos.append(self.visit(a))
            else:
                # last-resort: literal like str/int/float
                pos.append(self._const(a))
        return ast.Call(func=self._name(node.name), args=pos, keywords=kw)

    @visit.register
    def _(self, node: BinOp) -> ast.expr:
        return ast.BinOp(left=self.visit(node.left), op=self._binop(node.op), right=self.visit(node.right))

    @visit.register
    def _(self, node: UnOp) -> ast.expr:
        return ast.UnaryOp(op=self._unop(node.op), operand=self.visit(node.expr))

    @visit.register
    def _(self, node: Compare) -> ast.expr:
        if node.op is None:
            return self.visit(node.left)
        return ast.Compare(left=self.visit(node.left), ops=[self._cmpop(node.op)], comparators=[self.visit(node.right)])

    @visit.register
    def _(self, node: Exists) -> ast.expr:
        # Placeholder exists(var, argpats, where)
        return ast.Call(
            func=self._name("exists"),
            args=[
                self._name(node.var),
                self.visit(node.argpats) if node.argpats else self._const(None),
                self.visit(node.where) if node.where else self._const(None),
            ],
            keywords=[]
        )

    # --- operator helpers ---
    def _binop(self, op: str):
        return {
            '+': ast.Add(), '-': ast.Sub(), '*': ast.Mult(), '/': ast.Div(),
            'and': ast.And(), 'or': ast.Or()
        }[op]

    def _unop(self, op: str):
        return {'-': ast.USub(), 'not': ast.Not()}[op]

    def _cmpop(self, op: str):
        return {
            '<': ast.Lt(), '<=': ast.LtE(), '>': ast.Gt(), '>=': ast.GtE(),
            '==': ast.Eq(), '!=': ast.NotEq()
        }[op]
