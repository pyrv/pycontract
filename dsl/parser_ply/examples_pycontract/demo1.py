from typing import Optional, List

import pycontract as pc
from dataclasses import dataclass

"""
Requirement:

After a Command is issued with a name and a number,
no DispatchFailure should occur with that name and number,
until a Dispatch occurs with that name and number,
after which no ExecutionFailure should occur with that name and number,
until a Complete occurs with that name and number,
after which no other Complete should occur with that name and number.
"""

"""
events Exec {
  Command(name: str, time: int, number: int)
  Dispatch(name: str, time: int, number: int)
  DispatchFailure(name: str, time: int, number: int)
  ExecutionFailure(name: str, time: int, number: int)
  Complete(name: str, time: int, number: int)
}
"""

@dataclass
class Exec:
    name: str
    time: int
    number: int

@dataclass
class Command(Exec): ...

@dataclass
class Dispatch(Exec): ...

@dataclass
class DispatchFailure(Exec): ...

@dataclass
class ExecutionFailure(Exec): ...

@dataclass
class Complete(Exec): ...

"""
monitor M1 {
  case Command(name = n?, number = x?): Commanded(n,x)

  hot Commanded(name: str, number: int) {
   veto DispatchFailure(name=name, number=number)
   case Dispatch(name=name, number=number): Dispatched(name, number)
  }

  hot Dispatched(name: str, number: str) {
    veto ExecutionFailure(name=name, number=number)
    case Complete(name=name, number=number): Completed(name, number)
  }

  state Completed(name: str, number: int) {
    veto Complete(name=name, number=number)
  }
}
"""

class M1(pc.Monitor):
    def transition(self, event):
        match event:
            case Command(name=n, number=x):
                return M1.Commanded(n, x)

    @pc.data
    class Commanded(pc.HotState):
        name: str
        number: int

        def transition(self, event):
            match event:
                case DispatchFailure(name=self.name, number=self.number):
                    return pc.error()
                case Dispatch(name=self.name, number=self.number):
                    return M1.Dispatched(self.name, self.number)

    @pc.data
    class Dispatched(pc.HotState):
        name: str
        number: int

        def transition(self, event):
            match event:
                case ExecutionFailure(name=self.name, number=self.number):
                    return pc.error()
                case Complete(name=self.name, number=self.number):
                    return M1.Completed(self.name, self.number)

    @pc.data
    class Completed(pc.State):
        name: str
        number: int

        def transition(self, event):
            match event:
                case Complete(name=self.name, number=self.number):
                    return pc.error()

if __name__ == '__main__':
    m = M1()
    pc.set_debug(True)
    trace = [
        Command("A", 10, 1),
        Command("B", 20, 2),
        Command("C", 30, 3),
        DispatchFailure("A", 40, 1),
        Dispatch("B", 50, 2),
        ExecutionFailure("B", 60, 2),
        Complete("C", 70, 3),
        Complete("D", 80, 3)

    ]
    m.verify(trace)


"""
monitor M2 {
  case Command(name = n?, number = x?): hot {
    veto DispatchFailure(name=n, number=x)
    case Dispatch(name=n, number=n): hot {
      veto ExecutionFailure(name=n, number=x)
      case Complete(name=n, number=n): state {
        veto Complete(name=n, number=n)
      }
    }
  }
}

monitor M3 {
  case Command(name = n?, number = x?): [
    !DispatchFailure(name=n, number=x)
     Dispatch(name=n, number=n)
    !ExecutionFailure(name=n, number=x)
     Complete(name=n, number=n)
    !Complete(name=n, number=n)]
}
"""