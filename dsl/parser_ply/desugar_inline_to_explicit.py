# desugar_inline_to_explicit.py
from __future__ import annotations
from dataclasses import replace
from typing import Dict, Set, List, Tuple, Optional

from visitor import Visitor
from ast_nodes import *

class DesugarInlineToExplicit(Visitor):
    """
    Rewrites inline targets (TgtInlined) into explicit named states (StateDef),
    producing an M1-style monitor. It:
      - generates fresh state names,
      - infers state parameters from free variables in the inline body,
      - types those parameters from the events signatures using the current binding env,
      - replaces inline target with TgtStateInstance(newName, params...).
    """

    def __init__(self, prog: Program):
        # Build event type index: event -> {field -> TypeKind}
        self.event_fields: Dict[str, Dict[str, TypeKind]] = {}
        for ed in prog.events:
            if isinstance(ed, MultiEventDef):
                # assume all sigs share same shape (as in your Exec group)
                if ed.sigs and ed.sigs[0].params:
                    f = {p.name: p.typ for p in ed.sigs[0].params}
                else:
                    f = {}
                for sig in ed.sigs:
                    self.event_fields[sig.name] = f
            elif isinstance(ed, OneEventDef):
                sig = ed.sig
                f = {p.name: p.typ for p in (sig.params or [])}
                self.event_fields[sig.name] = f

        self.fresh = 0
        self.curr_mon: Optional[Monitor] = None
        self.generated_states: List[StateDef] = []  # collect per monitor

    # ---- utilities ----------------------------------------------------------

    def fresh_name(self, base: str = "Inline") -> str:
        self.fresh += 1
        return f"{base}_{self.fresh}"

    def env_with_bindings_from_case(
        self, env: Dict[str, TypeKind], pat: EventPat
    ) -> Dict[str, TypeKind]:
        """Extend env with bindings from NAME? patterns in this case."""
        env2 = dict(env)
        field_types = self.event_fields.get(pat.name, {})
        for ap in pat.args or []:
            if isinstance(ap, ArgPatNamed) and isinstance(ap.value, ValuePatNameQ):
                vname = ap.value.name[:-1] if ap.value.name.endswith("?") else ap.value.name
                vtyp = field_types.get(ap.name)
                if vtyp is not None:
                    env2[vname] = vtyp
            elif isinstance(ap, ArgPatPos) and isinstance(ap.value, ValuePatNameQ):
                # positional: map by index if you want; for now we can’t infer -> skip
                pass
        return env2

    def collect_free_vars(
        self, body: StateBody, env: Dict[str, TypeKind]
    ) -> Tuple[List[Param], List[str]]:
        """
        Find free variable names (ValuePatName occurrences) inside inline body that are
        not locally bound by NAME? in that body. Return (params, order).
        """
        bound: Set[str] = set()
        free: Set[str] = set()

        def walk_expr(e: Optional[Expr]):
            if e is None: return
            if isinstance(e, Var):
                # Treat Var occurrences as references; add if not shadowed
                if e.name not in bound:
                    free.add(e.name)
            elif isinstance(e, BinOp):
                walk_expr(e.left); walk_expr(e.right)
            elif isinstance(e, UnOp):
                walk_expr(e.expr)
            elif isinstance(e, Call):
                for a in e.args:
                    if isinstance(a, ArgNamed): walk_expr(a.expr)
                    elif isinstance(a, ArgPos): walk_expr(a.expr)

        def walk_valuepat(v):
            if isinstance(v, ValuePatName):
                # reference to an outer/state variable
                if v.name not in bound:
                    free.add(v.name)
            elif isinstance(v, ValuePatNameQ):
                # local binding; record bound name (strip '?')
                n = v.name[:-1] if v.name.endswith("?") else v.name
                bound.add(n)
            # ValuePatNum/Str: ignore

        def walk_pat_args(args: List[ArgPat]):
            for ap in args or []:
                if isinstance(ap, ArgPatNamed):
                    walk_valuepat(ap.value)
                elif isinstance(ap, ArgPatPos):
                    walk_valuepat(ap.value)
                # ArgPatWild: nothing

        # walk the inline state's body
        for tr in body.transitions:
            if isinstance(tr, Case):
                # bindings introduced here
                walk_pat_args(tr.pat.args)
                walk_expr(tr.pat.cond)
                # statements (assert/call/emit) – skip or add Var scan if you need it
                # nested targets: they may include further inlined states; we don't
                # count their free vars here; those will be handled when we process them.
            elif isinstance(tr, Veto):
                walk_pat_args(tr.pat.args)

        # Order params deterministically (preserve appearance order if desired)
        ordered = [n for n in env.keys() if n in free] + [n for n in sorted(free) if n not in env]
        # Build Param list with types from env (fallback str)
        params: List[Param] = [
            Param(name=n, typ=env.get(n, TypeKind.STR)) for n in ordered
        ]
        return params, ordered

    # ---- main entry for a program/monitor ----------------------------------

    def transform_program(self, prog: Program) -> Program:
        new_monitors: List[Monitor] = []
        for m in prog.monitors:
            self.generated_states = []
            self.curr_mon = m
            nm = self.transform_monitor(m)
            # append any new states we generated
            nm = replace(nm, states=nm.states + list(reversed(self.generated_states)))
            new_monitors.append(nm)
        return Program(events=prog.events, monitors=new_monitors)

    def transform_monitor(self, m: Monitor) -> Monitor:
        # top-level environment is empty (no bound variables yet)
        env: Dict[str, TypeKind] = {}

        # top-level transitions (Cases) may bind variables with ?; pass env into them
        new_transitions: List[Transition] = []
        for tr in m.transitions:
            new_transitions.append(self.transform_transition(tr, env))

        # states: transform their bodies, with state fields considered bound
        new_states: List[StateDef] = []
        for s in m.states:
            # state parameter names/types become bound variables inside that state
            state_env = {p.name: p.typ for p in (s.params or [])}
            new_body = self.transform_statebody(s.body, state_env) if s.body else None
            new_states.append(replace(s, body=new_body))

        return replace(m, transitions=new_transitions, states=new_states)

    # ---- transition / body / targets ---------------------------------------

    def transform_transition(self, tr: Transition, env: Dict[str, TypeKind]) -> Transition:
        if isinstance(tr, Veto):
            # Veto has only a pattern to transform (no targets)
            return tr  # patterns are simple; no change needed
        if isinstance(tr, Case):
            # Extend env with new ? bindings introduced by this pattern
            env2 = self.env_with_bindings_from_case(env, tr.pat)
            # Transform targets (may generate states)
            new_targets = None
            if tr.targets is not None:
                new_targets = [self.transform_target(t, env2) for t in tr.targets]
            # (statements unchanged)
            return replace(tr, targets=new_targets)
        return tr

    def transform_statebody(self, body: StateBody, env: Dict[str, TypeKind]) -> StateBody:
        new_transitions = [self.transform_transition(tr, env) for tr in body.transitions]
        return replace(body, transitions=new_transitions)

    def transform_target(self, tgt: Target, env: Dict[str, TypeKind]) -> Target:
        if isinstance(tgt, TgtInlined):
            # 1) compute params from free variables in this inline body
            params, param_order = self.collect_free_vars(tgt.body, env)
            # 2) make a fresh state name
            base = tgt.stype if tgt.stype in ("hot", "state") else "state"
            new_name = self.fresh_name(base.capitalize())
            # 3) build the explicit StateDef
            stype_text = "hot" if tgt.stype == "hot" else "state"
            new_state = StateDef(
                initial=False,
                stype=stype_text,
                name=new_name,
                params=params,
                body=self.transform_statebody(tgt.body, {**env, **{p.name: p.typ for p in params}})
            )
            new_state.comment = getattr(tgt, "comment", None)
            self.generated_states.append(new_state)
            # 4) replace the inline target with a StateInstance call
            new_args = [ArgPos(expr=Var(name)) for name in param_order]
            return TgtStateInstance(name=new_name, args=new_args)

        elif isinstance(tgt, TgtComposite):
            return TgtComposite(
                kind=tgt.kind,
                targets=[self.transform_target(t, env) for t in tgt.targets]
            )
        elif isinstance(tgt, TgtNot):
            return TgtNot(inner=self.transform_target(tgt.inner, env))
        elif isinstance(tgt, TargetSeqThen):
            # M2 doesn't use sequences as targets; leave as-is or transform then
            return TargetSeqThen(seq=tgt.seq, then=(
                self.transform_target(tgt.then, env) if tgt.then else None
            ))
        # Atomic targets unchanged
        return tgt
