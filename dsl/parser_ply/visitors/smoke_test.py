# smoke_test.py
from pathlib import Path
import importlib.util, sys
import types

from dsl.parser_ply.parser_ply import parse
from dsl.parser_ply.pyco_to_pycontract import PyContractTranslator

PYCO_SRC = r'''
events Exec {
  Command(name: str, time: int, number: int)
  Dispatch(name: str, time: int, number: int)
  DispatchFailure(name: str, time: int, number: int)
  ExecutionFailure(name: str, time: int, number: int)
  Complete(name: str, time: int, number: int)
}
monitor M1 {
  case Command(name = n?, number = x?): Commanded(n,x)

  hot Commanded(name: str, number: int) {
   veto DispatchFailure(name=name, number=number)
   case Dispatch(name=name, number=number): Dispatched(name, number)
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

def load_module_from_file(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def load_module_from_string(code: str, name: str):
    mod = types.ModuleType(name)
    mod.__file__ = f"<{name}>"
    exec(code, mod.__dict__)
    return mod

if __name__ == '__main__':
    FILE=False
    prog = parse(PYCO_SRC)
    code = PyContractTranslator().translate_program(prog)
    if FILE:
        HERE = Path(__file__).resolve().parent
        out = HERE / "generated_monitor.py"
        out.write_text(code, encoding="utf-8")
        mod = load_module_from_file(out, "generated_monitor")
    else:
        mod = load_module_from_string(code, "generated_monitor")

    m = mod.M1()
    m.eval(mod.Command(name="ACQ", time=0, number=1))
    m.eval(mod.Dispatch(name="ACQ", time=1, number=1))
    m.eval(mod.Complete(name="ACQ", time=2, number=1))
    m.eval(mod.Command(name="NAV", time=0, number=42))
    m.eval(mod.DispatchFailure(name="NAV", time=1, number=42))
    m.end()