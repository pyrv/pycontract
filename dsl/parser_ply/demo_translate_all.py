from parser_ply import parse
from desugar_inline_to_explicit import DesugarInlineToExplicit
from pyco_to_pycontract import PyContractTranslator

text = r'''
events Exec {
  Command(name: str, time: int, number: int)
  Dispatch(name: str, time: int, number: int)
  DispatchFailure(name: str, time: int, number: int)
  ExecutionFailure(name: str, time: int, number: int)
  Complete(name: str, time: int, number: int)
}

monitor M2 {
  case Command(name = n?, number = x?): hot {
    veto DispatchFailure(name=n, number=x)
    case Dispatch(name=n, number=x): hot {
      veto ExecutionFailure(name=n, number=x)
      case Complete(name=n, number=x): state {
        veto Complete(name=n, number=x)
      }
    }
  }
}

monitor M3 {
  case Command(name = n?, number = x?): state {
    case Complete(name=n, number=x): ok
  }
}
'''

if __name__ == "__main__":
    prog = parse(text)
    des = DesugarInlineToExplicit(prog)
    prog2 = des.transform_program(prog)
    code = PyContractTranslator().translate_program(prog2)
    print(code)
