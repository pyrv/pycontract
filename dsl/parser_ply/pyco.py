# runner.py
import sys
import types
from pathlib import Path
from typing import Optional
import uuid

from dsl.parser_ply.parser_ply import parse
from dsl.parser_ply.wellformedness_checker import WellformednessChecker
from dsl.parser_ply.desugar_seq_to_inline import DesugarSeqToInline
from dsl.parser_ply.desugar_inline_to_explicit import DesugarInlineToExplicit
from dsl.parser_ply.pyco_to_pycontract import PyContractTranslator

def load_module_from_string(code: str, name: str):
    mod = types.ModuleType(name)
    mod.__file__ = f"<{name}>"
    exec(code, mod.__dict__)
    return mod

class PyContractModule:
    def __init__(self, spec: str, debug: bool = False, write_file: Optional[str] = None):
        self.spec = spec
        self.code = None
        self.module = None
        self.errors = []

        try:
            prog = parse(self.spec)
        except SyntaxError as e:
            raise ValueError(f"Syntax error in specification: {e}") from e
        prog = DesugarSeqToInline().transform_program(prog)
        prog = DesugarInlineToExplicit(prog).transform_program(prog)

        checker = WellformednessChecker()
        self.errors = checker.check(prog)
        if self.errors:
            raise ValueError("Specification not well-formed:\n  " + "\n  ".join(self.errors))
        print("\n✅ Specification is well-formed")

        self.code = PyContractTranslator().translate_program(prog)
        if debug:
            print("Generated code:\n", self.code)
        print("✅ Translation to Python ok")

        if write_file:
            HERE = Path(__file__).resolve().parent
            out = HERE / write_file
            out.write_text(self.code, encoding="utf-8")

        name = f"generated_monitor_{uuid.uuid4().hex[:8]}"
        self.module = load_module_from_string(self.code, name)
        print(f"✅ Generated module {name}\n")
        sys.modules[name] = self.module

def monitor_module(spec: str, debug: bool = False, write_file: Optional[str] = None):
    return PyContractModule(spec, debug, write_file).module

