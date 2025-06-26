from pycontract import *

# Events
@data
class A:
    x: int

@data
class B:
    x: int

@data
class C:
    x: int

@data
class D:
    x: int

@data
class E:
    x: int

@data
class F:
    x: int

class OrMonitor(Monitor):
    """
    A monitor to test OrState logic.
    After A(x), it expects one of two sequences:
    1. B(x) then C(x), but not D(x) in between.
    2. D(x) then E(x), but not F(x) in between.
    """

    def transition(self, event):
        match event:
            case A(x):
                return OrState(
                    OrMonitor.Expect_B_NotD_C(x),
                    OrMonitor.Expect_D_NotF_E(x)
                )

    @data
    class Expect_B_NotD_C(HotState):
        x: int

        def transition(self, event):
            match event:
                case B(self.x):
                    return OrMonitor.Expect_NotD_C(self.x)

    @data
    class Expect_NotD_C(HotState):
        x: int

        def transition(self, event):
            match event:
                case D(self.x):
                    return error("D is not allowed in this branch")
                case C(self.x):
                    return ok

    @data
    class Expect_D_NotF_E(HotState):
        x: int

        def transition(self, event):
            match event:
                case D(self.x):
                    return OrMonitor.Expect_NotF_E(self.x)

    @data
    class Expect_NotF_E(HotState):
        x: int

        def transition(self, event):
            match event:
                case F(self.x):
                    return error("F is not allowed in this branch")
                case E(self.x):
                    return ok

if __name__ == '__main__':
    set_debug(True)
    print("run_monitor...")
    m = OrMonitor()
    
    # This trace will cause a safety violation (red) in the second branch
    # and leave the first branch in a hot state (yellow).
    trace = [A(1), D(1), F(1)]    
    m.verify(trace)

