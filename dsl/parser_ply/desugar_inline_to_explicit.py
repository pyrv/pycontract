# desugar_inline_to_explicit.py
from __future__ import annotations
from dataclasses import replace
from typing import Dict, Set, List, Tuple, Optional

from dsl.parser_ply.visitor import Visitor
from dsl.parser_ply.ast_nodes import *

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
        Collect *free* variable names used inside an inline state's BODY that should
        become parameters of the freshly generated explicit state.

        IMPORTANT:
          • We only collect names from *pattern arguments* (ValuePatName),
            NOT from `if` conditions (pat.cond) or statements.
            This prevents accidental captures like `exits` from `if (exits)`.
          • Names bound locally by NAME? (ValuePatNameQ) are excluded.
          • We filter out reserved/keyword-ish names and non-identifiers.
          • Parameter types come from `env` when available; otherwise default to str.
        """
        bound: Set[str] = set()  # names introduced via NAME? in this inline body
        free: Set[str] = set()  # candidate free names to become state params

        RESERVED = {
            "if", "else", "and", "or", "not",
            "exists", "ok", "error",
            "True", "False", "None"
        }

        def see_valuepat(v: ValuePat):
            if isinstance(v, ValuePatNameQ):
                # Local binding (strip '?'): becomes bound, not a param
                n = v.name[:-1] if v.name.endswith("?") else v.name
                bound.add(n)
            elif isinstance(v, ValuePatName):
                # Reference to an outer name → candidate free var (unless already bound)
                if v.name not in bound:
                    free.add(v.name)
            # ValuePatNum/Str: ignore

        def see_pat_args(args: List[ArgPat]):
            for ap in args or []:
                if isinstance(ap, ArgPatNamed):
                    see_valuepat(ap.value)
                elif isinstance(ap, ArgPatPos):
                    see_valuepat(ap.value)
                # ArgPatWild: ignore

        # Walk only pattern arguments of transitions inside the inline body.
        # DO NOT inspect tr.pat.cond or statements — those can reference arbitrary
        # flags/expressions and must not auto-become state parameters.
        for tr in body.transitions:
            if isinstance(tr, Case):
                see_pat_args(tr.pat.args)
            elif isinstance(tr, Veto):
                see_pat_args(tr.pat.args)

        # Determine deterministic order:
        #  - keep variables that already exist in env in env-order first,
        #  - then the rest alphabetically.
        ordered = [n for n in env.keys() if n in free] + [n for n in sorted(free) if n not in env]

        # Filter out obviously invalid names (keywords, non-identifiers, etc.)
        filtered = [n for n in ordered if n.isidentifier() and n not in RESERVED]

        # Build Param list with types from env (fallback to str)
        params: List[Param] = [Param(name=n, typ=env.get(n, TypeKind.STR)) for n in filtered]
        return params, filtered

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
