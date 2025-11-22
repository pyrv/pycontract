
# pyco.py

from dsl.parser_ply.pyco import monitor_module

if __name__ == "__main__":
    spec = """
    eventss Exec {
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
        """

    print("begin")
    mod = monitor_module(spec)
    m = mod.M1()
    m.eval(mod.Command(name="ACQ", time=0, number=1))
    m.eval(mod.Dispatch(name="ACQ", time=1, number=1))
    m.eval(mod.Complete(name="ACQ", time=2, number=1))
    m.eval(mod.Command(name="NAV", time=0, number=42))
    m.eval(mod.DispatchFailure(name="NAV", time=1, number=42))
    m.end()
    print("end")