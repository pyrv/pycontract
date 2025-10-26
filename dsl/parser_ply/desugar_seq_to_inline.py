from __future__ import annotations
from dataclasses import replace
from typing import List, Optional, Dict

from visitor import Visitor
from ast_nodes import *

class DesugarSeqToInline(Visitor):
    """
    Rewrites TargetSeqThen (M3 timeline shorthand) into nested inline states (M2).
    Rule of thumb:
      - Prefix '!' = veto in current state
      - First positive event = case ... -> next state
      - States before the last positive event are 'hot', final is 'state'
    """

    # ---- public entry points ----
    def transform_program(self, prog: Program) -> Program:
        new_monitors = [self.transform_monitor(m) for m in prog.monitors]
        return Program(events=prog.events, monitors=new_monitors)

    def transform_monitor(self, m: Monitor) -> Monitor:
        new_transitions = [self.transform_transition(t) for t in m.transitions]
        new_states = [self.transform_state(s) for s in m.states]
        return replace(m, transitions=new_transitions, states=new_states)

    # ---- nodes ----
    def transform_state(self, s: StateDef) -> StateDef:
        nb = self.transform_statebody(s.body) if s.body else None
        return replace(s, body=nb)

    def transform_statebody(self, b: Optional[StateBody]) -> Optional[StateBody]:
        if b is None: return None
        return replace(b, transitions=[self.transform_transition(t) for t in b.transitions])

    def transform_transition(self, t: Transition) -> Transition:
        if isinstance(t, Case):
            # rewrite targets (if any)
            if t.targets is None:
                return t
            new_targets: List[Target] = [self.transform_target(x) for x in t.targets]
            return replace(t, targets=new_targets)
        elif isinstance(t, Veto):
            return t
        return t

    def transform_target(self, tgt: Target) -> Target:
        if isinstance(tgt, TargetSeqThen):
            # Convert sequence to a single inline target
            inlined = self.seq_to_inline(tgt.seq.specs)
            # If there is a trailing 'then' atomic target, attach it as the single target of the last state.
            if tgt.then is not None:
                # Attach by appending to the deepest state's case
                inlined = self.attach_then_to_deepest(inlined, tgt.then)
            return inlined
        elif isinstance(tgt, TgtComposite):
            return TgtComposite(kind=tgt.kind, targets=[self.transform_target(x) for x in tgt.targets])
        elif isinstance(tgt, TgtNot):
            return TgtNot(inner=self.transform_target(tgt.inner))
        else:
            return tgt  # atomic targets unchanged

    # ---- sequence → inline states core ----

    def seq_to_inline(self, specs: List[EventSpec]) -> TgtInlined:
        """
        Turn a list of EventSpec into nested TgtInlined:
          hot { veto* ; case POS: <recurse> } ... final state { veto* }

        Extended semantics:
        - plain event  → hot (must eventually occur)
        - !event       → veto rule (forbidden while in state)
        - ?event       → optional trigger (cold state)
        - supports sequences starting with veto
        """
        # Empty sequence → trivial cold state
        if not specs:
            return self.make_inline_state(stype="state", vetoes=[], next_inline=None)

        # --- Identify structure of this stage
        vetoes: List[EventSpec] = []
        pos: Optional[EventSpec] = None
        rest: List[EventSpec] = []

        for i, sp in enumerate(specs):
            if sp.prefix == Prefix.BANG:
                # leading veto: add to current state
                if pos is None:
                    vetoes.append(sp)
                else:
                    rest.append(sp)
            elif sp.prefix == Prefix.QMARK:
                # conditional trigger (optional)
                pos = sp
                rest = specs[i + 1:]
                break
            else:
                # normal positive trigger
                if pos is None:
                    pos = sp
                else:
                    rest.append(sp)

        # --- Only vetoes (no further positive)
        if pos is None:
            return self.make_inline_state(stype="state", vetoes=vetoes, next_inline=None)

        # --- Determine next inline recursively
        next_inline = self.seq_to_inline(rest) if rest else None

        # --- Choose hot/cold type
        if pos.prefix == Prefix.QMARK:
            stype_here = "state"  # cold (optional trigger)
            comment = f"# optional branch triggered by ?{pos.pat.name}"
        else:
            stype_here = "hot"  # normal (must eventually happen)
            comment = f"# required event {pos.pat.name}"

        # --- Construct inline block
        inline = self.make_inline_state(
            stype=stype_here,
            vetoes=vetoes,
            next_inline=(pos, next_inline),
        )

        # add helpful comment (for debugging / pretty output)
        inline.comment = comment
        return inline

    def make_inline_state(self, stype: str, vetoes: List[EventSpec],
                          next_inline: Optional[tuple]) -> TgtInlined:
        """Utility to build a TgtInlined node."""
        # body construction simplified; integrate with your AST builder
        transitions = []

        # veto transitions
        for v in vetoes:
            transitions.append(Veto(v.pat))

        # case transition if there is a positive/conditional trigger
        if next_inline:
            pos, nxt = next_inline
            transitions.append(
                Case(
                    pat=pos.pat,
                    statements=[],
                    targets=[nxt] if nxt else [],
                )
            )

        return TgtInlined(stype=stype, body=StateBody(transitions=transitions))

    def attach_then_to_deepest(self, inl: TgtInlined, then_tgt: Target) -> TgtInlined:
        """
        Walk to the deepest inline state's positive branch and attach 'then_tgt'
        as its final target.
        """
        # Clone current inline
        stype = inl.stype
        new_transitions: List[Transition] = []
        attached = False

        for tr in inl.body.transitions:
            if isinstance(tr, Case) and tr.targets:
                # Dive if the (single) target is another inline
                if len(tr.targets) == 1 and isinstance(tr.targets[0], TgtInlined):
                    child = self.attach_then_to_deepest(tr.targets[0], then_tgt)
                    new_transitions.append(replace(tr, targets=[child]))
                    attached = True
                else:
                    # attach here (append)
                    new_targets = list(tr.targets) + [then_tgt]
                    new_transitions.append(replace(tr, targets=new_targets))
                    attached = True
            else:
                new_transitions.append(tr)

        if not attached:
            # No case with targets found → add a dummy case that goes to 'then'
            # (corner case; usually sequences have at least one positive)
            new_transitions.append(
                Case(pat=EventPat(name="__epsilon", args=[], cond=None),
                     statements=[], targets=[then_tgt])
            )

        return TgtInlined(stype=stype, body=StateBody(transitions=new_transitions))
