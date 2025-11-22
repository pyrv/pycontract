from pprint import pprint

from dsl.parser_ply.parser_ply import parse
from dsl.parser_ply.wellformedness_checker import WellformednessChecker
from dsl.parser_ply.desugar_seq_to_inline import DesugarSeqToInline
from dsl.parser_ply.desugar_inline_to_explicit import DesugarInlineToExplicit
from dsl.parser_ply.pyco_to_pycontract import PyContractTranslator

text = r'''
events Exec {
  Command(name: str, time: int, number: int)
  Dispatch(name: str, time: int, number: int)
  DispatchFailure(name: str, time: int, number: int)
  ExecutionFailure(name: str, time: int, number: int)
  Complete(name: str, time: int, number: int)
}

monitor M1 {
  case Command(name = n?): Running(n)
  
  state Running(name:str) {
    veto Command(name=name)
  }
}

monitor M3 {
  case Command(name = n?, number = x?): [
    ?DispatchFailure(name=n, number=x)
    !DispatchFailure(name=n, number=x)
     Dispatch(name=n, number=n)
    !ExecutionFailure(name=n, number=x)
     Complete(name=n, number=n)
    !Complete(name=n, number=n)
  ] 
}
'''

if __name__ == "__main__":
    prog = parse(text)
    prog = DesugarSeqToInline().transform_program(prog)
    prog = DesugarInlineToExplicit(prog).transform_program(prog)
    checker = WellformednessChecker()
    errors = checker.check(prog)
    if errors:
        print("Errors:")
        for e in errors:
            print("  -", e)
    else:
        print("✅ Specification is well-formed")
        code = PyContractTranslator().translate_program(prog)
        print(code)
