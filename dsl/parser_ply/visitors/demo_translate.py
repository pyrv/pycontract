# demo_translate.py
from dsl.parser_ply.parser_ply import parse
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
  case Command(name = n?, number = x?): Commanded(n,x)

  initial state Hello {
    veto DispatchFailure
  }

  hot Commanded(name: str, number: int) {
   veto DispatchFailure(name=name, number=number)
   case Dispatch(name=name, number=number): or [Dispatched(name, number), Completed(name, number)]
  }

  hot Dispatched(name: str, number: int) {
    veto ExecutionFailure(name=name, number=number)
    case Complete(name=name, number=number): Completed(name, number)
  }

  state Completed(name: str, number: int) {
    veto Complete(name=name, number=number)
  }
}
'''

"""
from parser_ply import parse
from wellformedness_checker import WellformednessChecker

prog = parse(open("my_monitor.pyco").read())
checker = WellformednessChecker()
errors = checker.check(prog)

if errors:
    print("Errors:")
    for e in errors:
        print("  -", e)
else:
    print("✅ Specification is well-formed")

"""

if __name__ == '__main__':
    prog = parse(text)
    mon = prog.monitors[0]
    gen = PyContractTranslator()
    print(gen.translate_program(prog))
