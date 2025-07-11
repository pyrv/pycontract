import pycontract as pc

@pc.data
class Init(pc.Event):
    pass

@pc.data
class A(pc.Event):
    pass

@pc.data
class B(pc.Event):
    pass

@pc.data
class C(pc.Event):
    pass

class DemoMonitor(pc.Monitor):
    """Monitor that returns all four composite types to test visualiser"""
    def transition(self, event):
        match event:
            case Init():
                # returns OrState of two AndStates and a NotState of Sequence
                return pc.OrState(
                    pc.AndState(DemoMonitor.PathA(), DemoMonitor.PathB()),
                    pc.NotState(
                        pc.Sequence(DemoMonitor.PathC(), DemoMonitor.FinalPath())
                    )
                )
        return None

    # ----- inner states -----
    @pc.data
    class PathA(pc.HotState):
        def transition(self, event):
            match event:
                case A():
                    return pc.ok
            return None

    @pc.data
    class PathB(pc.HotState):
        def transition(self, event):
            match event:
                case B():
                    return pc.ok
            return None

    @pc.data
    class PathC(pc.HotState):
        def transition(self, event):
            match event:
                case C():
                    return pc.ok
            return None

    @pc.data
    class FinalPath(pc.HotState):
        def transition(self, event):
            return None

if __name__ == "__main__":
    # quick manual viz
    from pycontract.visualizer import visualize
    visualize(__file__, outdir="viz37")
