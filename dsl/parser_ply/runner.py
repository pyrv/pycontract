# runner.py

from parser_ply import parse
from wellformedness_checker import WellformednessChecker
from desugar_seq_to_inline import DesugarSeqToInline
from desugar_inline_to_explicit import DesugarInlineToExplicit
from pyco_to_pycontract import PyContractTranslator
import pycontract as pc

class Monitor:
    def __init__(self, spec: str, debug: bool = False):
        self.spec = spec
        self.module = None
        self.errors = []

        # parsing:
        prog = parse(self.spec)
        prog = DesugarSeqToInline().transform_program(prog)
        prog = DesugarInlineToExplicit(prog).transform_program(prog)
        checker = WellformednessChecker()
        self.errors = checker.check(prog)
        if self.errors:
            raise ValueError("Specification not well-formed:\n  " + "\n  ".join(self.errors))
        print("✅ Specification is well-formed")
        code = PyContractTranslator().translate_program(prog)
        if debug:
            print("Generated code:\n", code)

        # loading monitor:
        ns = {}
        exec(code, ns)
        # pick first monitor class in the generated code
        self.module = next(v for v in ns.values() if isinstance(v, type) and issubclass(v, pc.Monitor))

    def verify(self, events: list):
        """Run the monitor over a sequence of event objects."""
        mon = self.module()
        for e in events:
            mon = mon.step(e)
        return mon
