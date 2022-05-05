
from pycontract import *

"""
Examples for RV 2022 paper.
"""


class M1(Monitor):
    """
    Basic property/
    """
    def transition(self, event):
        match event:
            case {'kind': 'acquire', 'thread': thread, 'lock': lock}:
                return self.DoRelease(thread, lock)

    @data
    class DoRelease(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case {'kind': 'acquire', 'thread': thread, 'lock': self.lock} if thread != self.thread:
                    return error('lock acquired by other thread')
                case {'kind': 'release', 'thread': self.thread, 'lock': self.lock}:
                    return ok


class M2(Monitor):
    """
    Expanded to use Always state.
    """
    @initial
    class Start(AlwaysState):
        def transition(self, event):
            match event:
                case {'kind': 'acquire', 'thread': thread, 'lock': lock}:
                    return self.DoRelease(thread, lock)

    @data
    class DoRelease(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case {'kind': 'acquire', 'thread': thread, 'lock': self.lock} if thread != self.thread:
                    return error('lock acquired by other thread')
                case {'kind': 'release', 'thread': self.thread, 'lock': self.lock}:
                    return ok


class M3(Monitor):
    """
    Use of facts.
    """

    def transition(self, event):
        match event:
            case {'kind': 'acquire', 'thread': thread, 'lock': lock}:
                return [self.DoRelease(thread, lock), self.DoNotFree(lock)]
            case {'kind': 'release', 'thread': thread, 'lock': lock} if not self.DoRelease(thread, lock):
                return error(f'thread releases un-acquired or already released lock')

    @data
    class DoRelease(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case {'kind': 'acquire', 'thread': thread, 'lock': self.lock} if thread != self.thread:
                    return error('lock acquired by other thread')
                case {'kind': 'release', 'thread': self.thread, 'lock': self.lock}:
                    return ok

    @data
    class DoNotFree(State):
        lock: int

        def transition(self, event):
            match event:
                case {'kind': 'free', 'memory': self.lock}:
                    return error(f'Lock released after being used')


class M4(Monitor):
    """
    More general predicate on states, use of `exists`
    """

    def transition(self, event):
        match event:
            case {'kind': 'acquire', 'thread': thread, 'lock': lock}:
                return [self.DoRelease(thread, lock), self.DoNotFree(lock)]
            case {'kind': 'release', 'lock': lock} if not self.exists(lambda state: isinstance(state, M4.DoRelease) and state.lock == lock):
                return error(f'thread releases un-acquired or already released lock')

    @data
    class DoRelease(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case {'kind': 'acquire', 'thread': thread, 'lock': self.lock} if thread != self.thread:
                    return error('lock acquired by other thread')
                case {'kind': 'release', 'lock': self.lock}:
                    return ok

    @data
    class DoNotFree(State):
        lock: int

        def transition(self, event):
            match event:
                case {'kind': 'free', 'memory': self.lock}:
                    return error(f'Lock released after being used')


class M5(Monitor):
    """
    Code on transitions.
    """
    def __init__(self):
        super().__init__()
        self.count: int = 0

    def transition(self, event):
        match event:
            case {'kind': 'acquire', 'thread': thread, 'lock': lock} if self.count < 3:
                self.monitor.count += 1
                return self.DoRelease(thread, lock)
            case {'kind': 'acquire'} if self.monitor.count >= 3:
                return error('more that 3 locks acquired')
 
    @data
    class DoRelease(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case {'kind': 'acquire', 'thread': thread, 'lock': self.lock} if thread != self.thread:
                    return error('lock acquired by other thread')
                case {'kind': 'release', 'thread': self.thread, 'lock': self.lock}:
                    self.monitor.count -= 1
                    return ok


class M6(Monitor):
    """
    Indexing and next-states.
    """
    def key(self, event) -> Optional[object]:
        match event:
            case {'task': task}:
                return task

    @initial
    class Idle(NextState):
        def transition(self, event):
            match event:
                case {'kind': 'begin', 'task': task, 'time': time, 'bound': bound}:
                    return self.Running(task, time, bound)

    @data
    class Running(HotNextState):
        task: str
        time: int
        bound: int

        def transition(self, event):
            match event:
                case {'kind': 'end', 'task': self.task, 'time': time}:
                    if time - self.time > self.bound:
                        self.monitor.report_error('too long time passed')
                    return M6.Idle()


class MS(Monitor):
    def __init__(self):
        super().__init__()
        self.monitor_this(M1(), M6())


if __name__ == '__main__':
    # visualize(__file__, True)
    m = M6()
    set_debug(True)
    trace1 = [
        {'kind': 'acquire', 'thread': 'T1', 'lock': 1},
        {'kind': 'acquire', 'thread': 'T1', 'lock': 1},  # double acquisition by same thread: ok
        {'kind': 'release', 'thread': 'T1', 'lock': 1},
        {'kind': 'acquire', 'thread': 'T2', 'lock': 2},
        {'kind': 'acquire', 'thread': 'T3', 'lock': 2},  # double acquisition by other thread: bad
                                                         # missing release of lock 2 by T3: bad
    ]
    trace2 = trace1
    trace3 = trace1 + [
        {'kind': 'release', 'thread': 'T3', 'lock': 3},
        {'kind': 'free', 'memory': 1}
    ]
    trace4 = [
        {'kind': 'acquire', 'thread': 'T1', 'lock': 1},
        {'kind': 'release', 'thread': 'T2', 'lock': 1},
        {'kind': 'release', 'thread': 'T2', 'lock': 2},
    ]
    trace5 = [
        #{'kind': 'acquire', 'thread': 'T1', 'lock': 1},
        #{'kind': 'acquire', 'thread': 'T1', 'lock': 1},  # double acquisition by same thread: ok
        #{'kind': 'release', 'thread': 'T1', 'lock': 1},
        #{'kind': 'acquire', 'thread': 'T2', 'lock': 2},
        #{'kind': 'acquire', 'thread': 'T3', 'lock': 2},  # double acquisition by other thread: bad
        {'kind': 'acquire', 'thread': 'T4', 'lock': 4},
        {'kind': 'acquire', 'thread': 'T5', 'lock': 5},
        {'kind': 'acquire', 'thread': 'T6', 'lock': 6},
        {'kind': 'release', 'thread': 'T6', 'lock': 6},
        {'kind': 'acquire', 'thread': 'T7', 'lock': 7},
        # missing release of lock 2 by T3: bad
    ]
    trace6 = [
        {'kind': 'begin', 'task': 1, 'time': 1000, 'bound': 500},
        {'kind': 'begin', 'task': 2, 'time': 1200, 'bound': 500},
        {'kind': 'begin', 'task': 3, 'time': 1300, 'bound': 1000},
        {'kind': 'end', 'task': 1, 'time': 1400},
        {'kind': 'end', 'task': 2, 'time': 1500},
        {'kind': 'end', 'task': 3, 'time': 1600},
        {'kind': 'end', 'task': 4, 'time': 1700},
        {'kind': 'begin', 'task': 5, 'time': 1800, 'bound': 1000},
        {'kind': 'begin', 'task': 5, 'time': 1800, 'bound': 2000}
    ]
    m.verify(trace6)





