# pyco_to_pycontract.py
from visitor import Visitor
from ast_nodes import *
import textwrap

class PyContractTranslator(Visitor):
    def __init__(self):
        self.lines = []
        self.indent = 0
        self.in_state = False
        self.mon_name = "Monitor"  # default

    def emit(self, line=""):
        self.lines.append("    " * self.indent + line)

    def result(self):
        return "\n".join(self.lines)

    def translate_program(self, prog: Program) -> str:
        """Generate full PyContract code (events + monitors) from a Program node."""
        self.lines, self.indent = [], 0
        self.emit("from dataclasses import dataclass")
        self.emit("import pycontract as pc")
        self.emit("")
        self.emit_events(prog.events)
        for m in prog.monitors:
            self.visit(m)
            self.emit("")
        return self.result()

    def emit_events(self, evdefs: list[EventDef]):
        """Emit Python dataclasses for event definitions (grouped or single)."""

        def py_type(tk: TypeKind) -> str:
            return {"int": "int", "float": "float", "str": "str"}[tk.value]

        for ed in evdefs:
            # --- grouped events:  events Exec { Command(...) ... }
            if isinstance(ed, MultiEventDef):
                group = ed.group
                base_sig = ed.sigs[0]
                self.emit("@dataclass")
                self.emit(f"class {group}:")
                self.indent += 1
                if base_sig.params:
                    for p in base_sig.params:
                        self.emit(f"{p.name}: {py_type(p.typ)}")
                else:
                    self.emit("pass")
                self.indent -= 1
                self.emit("")

                # subclasses
                for sig in ed.sigs:
                    self.emit("@dataclass")
                    self.emit(f"class {sig.name}({group}): ...")
                self.emit("")

            # --- single event:  event Command(name: str, time: int)
            elif isinstance(ed, OneEventDef):
                sig = ed.sig
                self.emit("@dataclass")
                self.emit(f"class {sig.name}:")
                self.indent += 1
                if sig.params:
                    for p in sig.params:
                        self.emit(f"{p.name}: {py_type(p.typ)}")
                else:
                    self.emit("pass")
                self.indent -= 1
                self.emit("")

        self.emit("")  # blank line at end

    def pat_value_rhs(self, vpat):
        # n?  → a bare variable name "n" (bind fresh)
        # n   → state field "self.n" (when in a state), else just "n"
        if isinstance(vpat, ValuePatNameQ):
            return vpat.name
        if isinstance(vpat, ValuePatName):
            return f"self.{vpat.name}" if self.in_state else vpat.name
        if isinstance(vpat, ValuePatNum):
            return vpat.value
        if isinstance(vpat, ValuePatStr):
            return vpat.value
        return "?"

    def indent_block(self, s: str, prefix: str) -> str:
        """Indent every line of s by prefix (for nested multi-line expressions)."""
        if not s:
            return prefix
        lines = s.splitlines()
        return "\n".join(prefix + line for line in lines)

    def format_composite(self, op: str, inner_exprs: list[str], base_prefix: str) -> str:
        """
        Pretty-format a composite op over inner_exprs, aligned to base_prefix.

        - If 0 args: op()
        - If 1 arg : op(arg)
        - Else     : op(\n<base>    arg1,\n<base>    arg2,\n<base>)
                     and each arg can itself be multiline; we re-indent it.
        """
        if len(inner_exprs) == 0:
            return f"{op}()"
        if len(inner_exprs) == 1:
            return f"{op}({inner_exprs[0]})"

        ind = base_prefix + "    "
        inner = ",\n".join(self.indent_block(e, ind) for e in inner_exprs)
        return f"{op}(\n{inner}\n{base_prefix})"

    def translate_target(self, tgt: Target):
        """Translate a Target node to PyContract code lines."""
        if isinstance(tgt, TgtStateInstance):
            argnames = ", ".join([self.expr_str(arg.expr) for arg in tgt.args])
            self.emit(f"return {self.mon_name}.{tgt.name}({argnames})")

        elif isinstance(tgt, TgtOk):
            msg = f"({tgt.message!r})" if tgt.message else ""
            self.emit(f"return pc.ok{msg}")

        elif isinstance(tgt, TgtError):
            msg = f"({tgt.message!r})" if tgt.message else ""
            self.emit(f"return pc.error{msg}")

        elif isinstance(tgt, TgtComposite):
            # Map composite kinds to PyContract combinators
            if tgt.kind == CompositeKind.AND:
                op = "pc.AndState"
            elif tgt.kind == CompositeKind.OR:
                op = "pc.OrState"
            elif tgt.kind == CompositeKind.SEQ:
                op = "pc.Sequence"
            else:
                op = "# UNKNOWN_COMPOSITE"

            # Build child expressions (structure-only; no base indent)
            args = [self.translate_target_expr(inner) for inner in tgt.targets]

            # Pretty-print with current base indent
            base_prefix = "    " * self.indent
            expr = self.format_composite(op, args, base_prefix)
            self.emit(f"return {expr}")

        elif isinstance(tgt, TgtNot):
            subexpr = self.translate_target_expr(tgt.inner)
            self.emit(f"return pc.NotState({subexpr})")

        elif isinstance(tgt, TargetSeqThen):
            inner_expr = self.translate_target_expr(tgt.then)
            self.emit(f"return pc.Sequence({inner_expr})")

        else:
            self.emit("# TODO: unknown target type")

    def translate_target_expr(self, tgt: Target) -> str:
        """Return a string expression (not emitted) for nested composites.
        NOTE: This returns structure-only (no base indent). The caller is responsible
        for adding base indentation when embedding into a multi-line composite.
        """
        if isinstance(tgt, TgtStateInstance):
            args = ", ".join([self.expr_str(arg.expr) for arg in tgt.args])
            return f"{self.mon_name}.{tgt.name}({args})"

        elif isinstance(tgt, TgtComposite):
            if tgt.kind == CompositeKind.AND:
                op = "pc.AndState"
            elif tgt.kind == CompositeKind.OR:
                op = "pc.OrState"
            elif tgt.kind == CompositeKind.SEQ:
                op = "pc.Sequence"
            else:
                op = "UNKNOWN"

            inner = [self.translate_target_expr(t) for t in tgt.targets]
            # Use empty base prefix here; the parent composite (or translate_target)
            # will indent this block appropriately with format_composite().
            return self.format_composite(op, inner, base_prefix="")

        elif isinstance(tgt, TgtNot):
            inner = self.translate_target_expr(tgt.inner)
            return f"pc.NotState({inner})"

        elif isinstance(tgt, TgtError):
            return "pc.error()"

        elif isinstance(tgt, TgtOk):
            return "pc.ok()"

        else:
            return "pc.UNKNOWN_TARGET()"

    # --- entry point

    def visit_Monitor(self, m: Monitor):
        self.mon_name = m.name
        self.emit(f"class {m.name}(pc.Monitor):")
        self.indent += 1

        # top-level transition (from monitor header cases)
        self.emit("def transition(self, event):")
        self.indent += 1
        self.emit("match event:")
        self.indent += 1
        for tr in m.transitions:
            self.visit(tr)
        self.indent -= 1
        self.indent -= 1

        # generate nested state classes
        for st in m.states:
            self.visit(st)

        self.indent -= 1
        # return self.result()

    # --- transition rules (case/veto)

    def visit_Case(self, c: Case):
        pat = c.pat
        args = []
        for a in pat.args:
            if isinstance(a, ArgPatNamed):
                args.append(f"{a.name}={self.pat_value_rhs(a.value)}")
            elif isinstance(a, ArgPatPos):
                args.append(self.pat_value_rhs(a.value))
        arglist = ", ".join(args)
        guard = f" if {self.expr_str(pat.cond)}" if pat.cond else ""
        self.emit(f"case {pat.name}({arglist}){guard}:")  # <-- guard before colon
        self.indent += 1
        for tgt in (c.targets or []):
            self.translate_target(tgt)
        if not c.targets:
            self.emit("# no target")
        self.indent -= 1

    def visit_Veto(self, v: Veto):
        pat = v.pat
        args = []
        for a in pat.args:
            if isinstance(a, ArgPatNamed):
                args.append(f"{a.name}={self.pat_value_rhs(a.value)}")
            elif isinstance(a, ArgPatPos):
                args.append(self.pat_value_rhs(a.value))
        arglist = ", ".join(args)
        self.emit(f"case {pat.name}({arglist}):")
        self.indent += 1
        self.emit("return pc.error()")
        self.indent -= 1

    def _free_vars_expr(self, e):
        """Return names of variables used in an expression (for filtering)."""
        if e is None:
            return set()
        if isinstance(e, Var):
            return {e.name}
        if isinstance(e, BinOp):
            return self._free_vars_expr(e.left) | self._free_vars_expr(e.right)
        if isinstance(e, UnOp):
            return self._free_vars_expr(e.expr)
        if isinstance(e, Call):
            out = set()
            for a in e.args:
                if isinstance(a, ArgNamed):
                    out |= self._free_vars_expr(a.expr)
                elif isinstance(a, ArgPos):
                    out |= self._free_vars_expr(a.expr)
            return out
        if isinstance(e, Exists):
            out = {e.var}
            if e.where:
                out |= self._free_vars_expr(e.where)
            return out
        return set()

    def expr_str(self, e):
        if isinstance(e, Var):
            return f"self.{e.name}" if self.in_state else e.name
        if isinstance(e, Num):
            return e.value
        if isinstance(e, Str):
            return e.value
        if isinstance(e, Call):
            # add if you support function calls in args
            fun = e.name
            args = ", ".join(self.expr_str_arg(a) for a in e.args)
            return f"{fun}({args})"
        # todo: BinOp/UnOp/Compare if needed
        return "?"

    def expr_str_arg(self, a):
        if isinstance(a, ArgNamed):
            return f"{a.name}={self.expr_str(a.expr)}"
        if isinstance(a, ArgPos):
            return self.expr_str(a.expr)
        return "?"

    # --- states

    # inside class PyContractTranslator(Visitor):

    def _pc_state_base(self, stype: str) -> str:
        """
        Map a PYCO state's `stype` (string) to the corresponding PyContract base class.
        Supports: state, hot, next, hotnext, always.
        Falls back to pc.State if unrecognized or missing.
        """
        if not stype:
            return "pc.State"

        s = stype.strip().lower()
        if s == "state":
            return "pc.State"
        if s == "hot":
            return "pc.HotState"
        if s == "next":
            return "pc.NextState"
        if s == "hotnext":
            return "pc.HotNextState"
        if s == "always":
            return "pc.AlwaysState"

        # fallback for safety
        return "pc.State"

    def visit_StateDef(self, s: StateDef):
        old = self.in_state
        self.in_state = True
        try:
            base = self._pc_state_base(s.stype)

            self.emit("")

            # --- decorators ---
            if s.initial:
                self.emit("@pc.initial")
                self.emit("@pc.data")
            else:
                self.emit("@pc.data")

            # --- class header ---
            self.emit(f"class {s.name}({base}):")

            # --- validation ---
            if s.initial and s.params:
                raise ValueError(
                    f"Initial state '{s.name}' must not have parameters."
                )

            # --- comment (optional) ---
            if hasattr(s, "comment") and s.comment:
                self.emit(f"    # {s.comment}")

            self.indent += 1

            # --- fields ---
            declared = {p.name for p in (s.params or [])}

            # (optional) collect names used in expressions for filtering
            used = set()
            if s.body:
                for tr in s.body.transitions:
                    if isinstance(tr, Case) and tr.pat.cond:
                        used |= self._free_vars_expr(tr.pat.cond)

            # ✅ keep only declared params
            fields = sorted(declared & used) if declared else sorted(declared)

            # emit declared fields only
            for p in s.params or []:
                self.emit(f"{p.name}: {p.typ.value}")
            if s.params:
                self.emit("")

            # --- transition method ---
            self.emit("def transition(self, event):")
            self.indent += 1
            self.emit("match event:")
            self.indent += 1
            for tr in (s.body.transitions if s.body else []):
                self.visit(tr)
            self.indent -= 1
            self.indent -= 1
            self.indent -= 1

        finally:
            self.in_state = old

