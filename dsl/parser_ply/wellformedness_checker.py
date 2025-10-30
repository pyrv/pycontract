
# wellformedness_checker.py
from __future__ import annotations
from visitor import Visitor
from ast_nodes import *


class WellformednessChecker(Visitor):
    """
    Performs static wellformedness checks on a PYCO specification:
      - Duplicate event, monitor, or state names
      - Unknown events or states
      - Ill-typed or invalid arguments
      - Unbound variable references (name used but never bound via n?)
      - Initial state constraints (no params, at most one)
    """

    def __init__(self):
        self.errors: list[str] = []
        self.event_table: dict[str, dict[str, TypeKind]] = {}
        self.current_monitor: Monitor | None = None
        self.current_state_names: set[str] = set()
        self.bound_vars: set[str] = set()

    # -------------------------------------------------------
    # Utilities
    # -------------------------------------------------------

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.errors.append(f"Warning: {msg}")

    def check(self, prog: Program) -> list[str]:
        """Entry point: run all checks on a Program."""
        self.visit(prog)
        return self.errors

    # -------------------------------------------------------
    # Program / Events / Monitors
    # -------------------------------------------------------

    def visit_Program(self, prog: Program):
        # ---- Event collection ----
        for ed in prog.events:
            if isinstance(ed, MultiEventDef):
                for sig in ed.sigs:
                    if sig.name in self.event_table:
                        self.error(f"Duplicate event name '{sig.name}'.")
                    self.event_table[sig.name] = {p.name: p.typ for p in sig.params}
            elif isinstance(ed, OneEventDef):
                sig = ed.sig
                if sig.name in self.event_table:
                    self.error(f"Duplicate event name '{sig.name}'.")
                self.event_table[sig.name] = {p.name: p.typ for p in sig.params}

        # ---- Monitors ----
        monitor_names = set()
        for m in prog.monitors:
            if m.name in monitor_names:
                self.error(f"Duplicate monitor name '{m.name}'.")
            monitor_names.add(m.name)
            self.visit(m)

    # -------------------------------------------------------
    # Monitors and States
    # -------------------------------------------------------

    def visit_Monitor(self, m: Monitor):
        self.current_monitor = m
        self.current_state_names = {s.name for s in m.states}

        for st in m.states:
            if st.initial:
                if st.params:
                    self.error(f"Initial state '{st.name}' cannot have parameters.")
            self.visit(st)

        # refresh known state names (in case new ones were added dynamically)
        self.current_state_names = {s.name for s in m.states}

        for tr in m.transitions:
            self.visit(tr)

        # ---- Reachability check ----
        defined = {s.name for s in m.states}
        reachable = self._find_reachable_states(m)
        unreachable = defined - reachable
        for sname in sorted(unreachable):
            self.error(f"Unreachable state '{sname}' in monitor '{m.name}'.")

    def visit_StateDef(self, s: StateDef):
        # state parameters define local variables
        old_bound = set(self.bound_vars)
        self.bound_vars = {p.name for p in s.params}
        if s.body:
            self.visit(s.body)
        self.bound_vars = old_bound

    def visit_StateBody(self, b: StateBody):
        for t in b.transitions:
            self.visit(t)

    # -------------------------------------------------------
    # Transitions: Case / Veto
    # -------------------------------------------------------

    def visit_Case(self, c: Case):
        if c.pat.name not in self.event_table:
            self.error(f"Unknown event '{c.pat.name}' in case pattern.")
            field_types = {}
        else:
            field_types = self.event_table[c.pat.name]

        # --- positional argument arity check ---
        n_pos = sum(isinstance(ap, ArgPatPos) for ap in c.pat.args)
        n_named = sum(isinstance(ap, ArgPatNamed) for ap in c.pat.args)
        if n_pos > 0 and n_named > 0:
            self.error(
                f"Mixed positional and named arguments in pattern for event '{c.pat.name}'."
            )
        elif n_pos > 0:
            declared_arity = len(field_types)
            if n_pos != declared_arity:
                self.error(
                    f"Event '{c.pat.name}' expects {declared_arity} positional arguments, "
                    f"but {n_pos} given."
                )

        # local env for ? bindings
        local_bound = set(self.bound_vars)

        # pattern argument checking
        seen_args = set()
        for ap in c.pat.args:
            if isinstance(ap, ArgPatNamed):
                name = ap.name
                if name in seen_args:
                    self.error(f"Duplicate argument '{name}' in event pattern '{c.pat.name}'.")
                seen_args.add(name)
                if name not in field_types:
                    self.error(f"Unknown field '{name}' in event '{c.pat.name}'.")
                self._check_valuepat(ap.value, local_bound)
            elif isinstance(ap, ArgPatPos):
                self._check_valuepat(ap.value, local_bound)
            elif isinstance(ap, ArgPatWild):
                pass

        # update env with any new ? bindings
        new_bound = {v.name[:-1] for v in self._collect_qmarks(c.pat.args)}

        # ---- shadowing warnings ----
        # (a) shadowing state parameters (bound_vars are the state params of the current state)
        for nb in new_bound:
            if nb in self.bound_vars:
                self.warn(
                    f"Variable '{nb}' introduced by '?' in case pattern shadows a state parameter "
                    f"in monitor '{self.current_monitor.name}'."
                )

        # (b) shadowing event field names for this event
        event_fields = set(field_types.keys())
        for nb in new_bound:
            if nb in event_fields:
                self.warn(
                    f"Variable '{nb}' introduced by '?' in case pattern reuses an event field "
                    f"name of '{c.pat.name}', which may be confusing."
                )

        local_bound |= new_bound

        # check condition
        if c.pat.cond:
            self._check_expr(c.pat.cond, local_bound)

        # check targets with updated env
        for tgt in (c.targets or []):
            self._check_target(tgt, local_bound)

    def visit_Veto(self, v: Veto):
        if v.pat.name not in self.event_table:
            self.error(f"Unknown event '{v.pat.name}' in veto pattern.")
            field_types = {}
        else:
            field_types = self.event_table[v.pat.name]

        # --- positional argument arity check ---
        n_pos = sum(isinstance(ap, ArgPatPos) for ap in v.pat.args)
        n_named = sum(isinstance(ap, ArgPatNamed) for ap in v.pat.args)
        if n_pos > 0 and n_named > 0:
            self.error(
                f"Mixed positional and named arguments in veto for event '{v.pat.name}'."
            )
        elif n_pos > 0:
            declared_arity = len(field_types)
            if n_pos != declared_arity:
                self.error(
                    f"Event '{v.pat.name}' expects {declared_arity} positional arguments, "
                    f"but {n_pos} given."
                )

        # warn if a '?'-binding shadows event field names (even though veto has no targets)
        for ap in v.pat.args:
            if isinstance(ap, (ArgPatNamed, ArgPatPos)) and isinstance(ap.value, ValuePatNameQ):
                nb = ap.value.name[:-1]
                if nb in field_types:
                    self.warn(
                        f"Variable '{nb}' introduced by '?' in veto pattern reuses an event field "
                        f"name of '{v.pat.name}', which may be confusing."
                    )

        local_bound = set(self.bound_vars)
        for ap in v.pat.args:
            if isinstance(ap, ArgPatNamed):
                if ap.name not in field_types:
                    self.error(f"Unknown field '{ap.name}' in event '{v.pat.name}'.")
                self._check_valuepat(ap.value, local_bound)
            elif isinstance(ap, ArgPatPos):
                self._check_valuepat(ap.value, local_bound)

    # -------------------------------------------------------
    # Target checking
    # -------------------------------------------------------

    def _check_target(self, tgt: Target, bound: set[str]):
        """Check that target references and argument lists are valid."""

        known = self.current_state_names  # snapshot of known state names

        # --- State instance target --------------------------------------------
        if isinstance(tgt, TgtStateInstance):
            if tgt.name not in known:
                self.error(
                    f"Unknown state target '{tgt.name}' in monitor "
                    f"'{self.current_monitor.name}'."
                )
                return

            # Retrieve the corresponding state definition
            st = next(
                (s for s in self.current_monitor.states if s.name == tgt.name),
                None
            )
            if not st:
                return

            param_names = [p.name for p in st.params]
            n_pos = sum(isinstance(a, ArgPos) for a in tgt.args)
            n_named = sum(isinstance(a, ArgNamed) for a in tgt.args)

            # 1) Mixing positional and named args
            if n_pos > 0 and n_named > 0:
                self.error(
                    f"Target '{tgt.name}' mixes positional and named arguments "
                    f"in monitor '{self.current_monitor.name}'."
                )
                return

            # 2) Positional: must match arity exactly
            if n_pos > 0:
                if n_pos != len(param_names):
                    self.error(
                        f"Target '{tgt.name}' expects {len(param_names)} positional arguments "
                        f"but {n_pos} given in monitor '{self.current_monitor.name}'."
                    )
                return

            # 3) Named: must provide all and only declared parameters
            if n_named > 0:
                seen = set()
                for a in tgt.args:
                    if isinstance(a, ArgNamed):
                        if a.name not in param_names:
                            self.error(
                                f"Unknown parameter '{a.name}' in target '{tgt.name}' "
                                f"of monitor '{self.current_monitor.name}'."
                            )
                        if a.name in seen:
                            self.error(
                                f"Duplicate named argument '{a.name}' in target '{tgt.name}' "
                                f"of monitor '{self.current_monitor.name}'."
                            )
                        seen.add(a.name)

                missing = set(param_names) - seen
                extra = seen - set(param_names)
                if missing:
                    self.error(
                        f"Target '{tgt.name}' in monitor '{self.current_monitor.name}' "
                        f"is missing parameters {sorted(missing)}."
                    )
                if extra:
                    self.error(
                        f"Target '{tgt.name}' in monitor '{self.current_monitor.name}' "
                        f"has unexpected parameters {sorted(extra)}."
                    )
                return

        # --- Composite target (and/or/seq) ------------------------------------
        elif isinstance(tgt, TgtComposite):
            for t in tgt.targets:
                self._check_target(t, bound)

        # --- Negation target ---------------------------------------------------
        elif isinstance(tgt, TgtNot):
            self._check_target(tgt.inner, bound)

        # --- Sequence target ---------------------------------------------------
        elif isinstance(tgt, TargetSeqThen):
            if tgt.then:
                self._check_target(tgt.then, bound)

        # --- Other atomic targets (ok, error, etc.) ----------------------------
        else:
            pass

    # -------------------------------------------------------
    # Reachability analysis (extra semantic check)
    # -------------------------------------------------------

    def _collect_referenced_states(self, t: Target, acc: set[str]):
        """Collect names of state targets appearing anywhere in a target expression."""
        if isinstance(t, TgtStateInstance):
            acc.add(t.name)
        elif isinstance(t, TgtComposite):
            for tt in t.targets:
                self._collect_referenced_states(tt, acc)
        elif isinstance(t, TgtNot):
            self._collect_referenced_states(t.inner, acc)
        elif isinstance(t, TargetSeqThen):
            if t.then:
                self._collect_referenced_states(t.then, acc)

    def _find_reachable_states(self, m: Monitor) -> set[str]:
        """Return the set of all state names referenced in transitions or initial roots."""
        reachable: set[str] = {s.name for s in m.states if s.initial}
        for tr in m.transitions:
            if isinstance(tr, Case) and tr.targets:
                for tgt in tr.targets:
                    self._collect_referenced_states(tgt, reachable)
            elif isinstance(tr, Veto):
                pass  # vetoes don't create transitions
        for s in m.states:
            if s.body:
                for tr in s.body.transitions:
                    if isinstance(tr, Case) and tr.targets:
                        for tgt in tr.targets:
                            self._collect_referenced_states(tgt, reachable)
        return reachable

    # -------------------------------------------------------
    # Expressions / Patterns helpers
    # -------------------------------------------------------

    def _collect_qmarks(self, args: list[ArgPat]) -> list[ValuePatNameQ]:
        out = []
        for a in args:
            if isinstance(a, (ArgPatNamed, ArgPatPos)) and isinstance(a.value, ValuePatNameQ):
                out.append(a.value)
        return out

    def _check_valuepat(self, v: ValuePat, bound: set[str]):
        """Ensure variables are properly bound."""
        if isinstance(v, ValuePatName):
            if v.name not in bound:
                self.error(f"Unbound variable '{v.name}' used in pattern.")
        elif isinstance(v, ValuePatNameQ):
            pass  # defines a new variable
        # literals are fine

    def _check_expr(self, e: Expr, bound: set[str]):
        """Walk expressions for variable usage and semantic checks."""

        if isinstance(e, Var):
            name = e.name
            # Bound variable names are okay
            if name in bound:
                return
            # Allow references to known events or states (for advanced uses)
            if name in self.event_table or name in self.current_state_names:
                return
            # Everything else is unknown
            self.error(f"Unknown identifier '{name}' in expression.")

        elif isinstance(e, Num) or isinstance(e, Str):
            # Literals are fine
            return

        elif isinstance(e, BinOp):
            self._check_expr(e.left, bound)
            self._check_expr(e.right, bound)

        elif isinstance(e, UnOp):
            self._check_expr(e.expr, bound)

        elif isinstance(e, Call):
            for a in e.args:
                if isinstance(a, ArgNamed):
                    self._check_expr(a.expr, bound)
                elif isinstance(a, ArgPos):
                    self._check_expr(a.expr, bound)

        elif isinstance(e, Exists):
            # --- Validate referenced state name ---
            if e.var not in self.current_state_names:
                self.error(
                    f"Unknown state '{e.var}' referenced in exists-expression "
                    f"of monitor '{self.current_monitor.name}'."
                )
                return

            # --- Retrieve that state’s parameter list ---
            st = next((s for s in self.current_monitor.states if s.name == e.var), None)
            if not st:
                return
            param_names = [p.name for p in st.params]

            n_pos = sum(isinstance(ap, ArgPatPos) for ap in (e.argpats or []))
            n_named = sum(isinstance(ap, ArgPatNamed) for ap in (e.argpats or []))

            # 1) No mixing positional/named arguments
            if n_pos > 0 and n_named > 0:
                self.error(
                    f"Exists-expression for state '{e.var}' mixes positional and named arguments "
                    f"in monitor '{self.current_monitor.name}'."
                )
                return

            # 2) Positional arguments → exact arity
            if n_pos > 0:
                if n_pos != len(param_names):
                    self.error(
                        f"Exists-expression for state '{e.var}' expects {len(param_names)} "
                        f"positional arguments but {n_pos} given "
                        f"in monitor '{self.current_monitor.name}'."
                    )

            # 3) Named arguments → all must be declared parameters
            if n_named > 0:
                seen = set()
                for ap in e.argpats:
                    if isinstance(ap, ArgPatNamed):
                        if ap.name not in param_names:
                            self.error(
                                f"Unknown parameter '{ap.name}' in exists-expression "
                                f"for state '{e.var}' in monitor '{self.current_monitor.name}'."
                            )
                        if ap.name in seen:
                            self.error(
                                f"Duplicate argument '{ap.name}' in exists-expression "
                                f"for state '{e.var}' in monitor '{self.current_monitor.name}'."
                            )
                        seen.add(ap.name)

            # 4) Check all ValuePats for bound variables
            for ap in e.argpats or []:
                if isinstance(ap, ArgPatNamed):
                    self._check_valuepat(ap.value, bound)
                elif isinstance(ap, ArgPatPos):
                    self._check_valuepat(ap.value, bound)

            # 5) Check the optional 'where' clause
            if e.where:
                self._check_expr(e.where, bound)
        else:
            # If we later add new Expr types, we can log unknowns
            pass
