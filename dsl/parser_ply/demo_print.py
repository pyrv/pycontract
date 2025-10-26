
# demo_print.py
from parser_ply import parse
from visitor import PrintVisitor

text = r'''
events Exec {
  Command(name: str, time: int, number: int)
  Dispatch(name: str, time: int, number: int)
  DispatchFailure(name: str, time: int, number: int)
  ExecutionFailure(name: str, time: int, number: int)
  Complete(name: str, time: int, number: int)
}

monitor M3 {
  case Command(name = n?, number = x?): [
    !DispatchFailure(name=n, number=x)
     Dispatch(name=n, number=n)
    !ExecutionFailure(name=n, number=x)
     Complete(name=n, number=n)
    !Complete(name=n, number=n)]
}
'''

if __name__ == "__main__":
    prog = parse(text)
    PrintVisitor().visit(prog)
