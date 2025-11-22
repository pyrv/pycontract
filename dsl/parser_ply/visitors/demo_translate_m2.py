from dsl.parser_ply.parser_ply import parse
from dsl.parser_ply.desugar_inline_to_explicit import DesugarInlineToExplicit
from dsl.parser_ply.pyco_to_pycontract import PyContractTranslator

text = r'''
event Ping(time: int)
event Pong(time: int)

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
'''

if __name__ == "__main__":
    prog = parse(text)
    m2 = DesugarInlineToExplicit(prog).transform_program(prog)
    code = PyContractTranslator().translate_program(m2)
    print(code)
