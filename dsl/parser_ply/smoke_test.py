# smoke_test.py
from pathlib import Path
import importlib.util, sys
from parser_ply import parse
from pyco_to_pycontract import PyContractTranslator

HERE = Path(__file__).resolve().parent

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

prog = parse(PYCO_SRC)
code = PyContractTranslator().translate_program(prog)
out = HERE / "generated_monitor.py"
out.write_text(code, encoding="utf-8")

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

mod = load_module(out, "generated_monitor")

print("=== HAPPY PATH ===")
m = mod.M1()
s = m.transition(mod.Command(name="ACQ", time=0, number=1))
s = s.transition(mod.Dispatch(name="ACQ", time=1, number=1))
s = s.transition(mod.Complete(name="ACQ", time=2, number=1))

print("\n=== VETO PATH (DispatchFailure) ===")
m2 = mod.M1()
t = m2.transition(mod.Command(name="NAV", time=0, number=42))
t2 = t.transition(mod.DispatchFailure(name="NAV", time=1, number=42))

