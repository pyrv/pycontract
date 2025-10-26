from dataclasses import dataclass
import pycontract as pc

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
