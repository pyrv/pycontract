from typing import Optional

from pycontract import *

"""
Examples for RV 2022 paper.
"""


@data
class Acquire:
    thread: str
    lock: int


@data
class Release:
    thread: str
    lock: int


@data
class Free:
    memory: int


class M1(Monitor):
    """
    Basic property/
    """
    def transition(self, event):
        match event:
            case Acquire(thread, lock):
                return M1.DoRelease(thread, lock)

    @data
    class DoRelease(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Acquire(thread, self.lock) if thread != self.thread:
                    return error('double acquisition')
                case Release(self.thread, self.lock):
                    return ok


class M1Expanded(Monitor):
    """
    Expanded to use Always state.
    """
    @initial
    class Start(AlwaysState):
        def transition(self, event):
            match event:
                case Acquire(thread, lock):
                    return M2.DoRelease(thread, lock)

    @data
    class DoRelease(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Acquire(thread, self.lock) if thread != self.thread:
                    return error('double acquisition')
                case Release(self.thread, self.lock):
                    return ok


class M2(Monitor):
    """
    Use of facts, counting.
    """

    def __init__(self, limit: int):
        super().__init__()
        self.count: int = 0
        self.limit = limit

    def __str__(self):
        result = f'{self.count}\n'
        result += super().__str__()
        return result

    def transition(self, event):
        match event:
            case Acquire(thread, lock) if not self.exists(lambda state: isinstance(state, M2.DoRelease) and state.lock == lock):
                if self.monitor.count < self.limit:
                    self.monitor.count += 1
                    return [M2.DoRelease(thread, lock), M2.DoNotFree(lock)]
                else:
                    return error(f'limit reached, count = {self.count} ')
            case Release(thread, lock) if not M2.DoRelease(thread, lock):
                return error(f'thread releases un-acquired or already released lock')

    @data
    class DoRelease(HotState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Acquire(_, self.lock):
                    return [error('lock acquired by other thread'), self]
                case Release(self.thread, self.lock):
                    self.monitor.count -= 1
                    return ok

    @data
    class DoNotFree(State):
        lock: int

        def transition(self, event):
            match event:
                case Free(self.lock):
                    return error(f'Lock released after being used')


class M3(Monitor):
    """
    Indexing and next-states.
    """

    def key(self, event) -> Optional[object]:
        match event:
            case Acquire(_, lock) | Release(_, lock):
                return lock

    @initial
    class Idle(NextState):
        def transition(self, event):
            match event:
                case Acquire(thread, lock):
                    return M3.DoRelease(thread, lock)

    @data
    class DoRelease(HotNextState):
        thread: str
        lock: int

        def transition(self, event):
            match event:
                case Release(self.thread, self.lock):
                    return M3.Idle()


class M4(Monitor):
    def __init__(self):
        super().__init__()
        self.monitor_this(M1(), M3())


if __name__ == '__main__':
    # visualize(__file__, True)
    set_debug(True)
    trace1 = [
        Acquire('T1', 1),
        Acquire('T1', 1),  # double acquisition by same thread: ok
        Release('T1', 1),
        Acquire('T2', 2),
        Acquire('T3', 2),  # double acquisition by other thread: bad
                                                         # missing release of lock 2 by T3: bad
    ]
    trace2 = trace1 + [
        Release('T3', 3),
        Free(1)
    ]
    trace3 = [
        Acquire('T1', 1),
        Release('T2', 1),
        Release('T2', 2),
    ]
    trace4 = [
        Acquire('T1', 1),
        Acquire('T1', 1),  # double acquisition by same thread: ok
        Release('T1', 1),
        Acquire('T2', 2),
        Acquire('T3', 2),  # double acquisition by other thread: bad
        Acquire('T4', 4),
        Acquire('T5', 5),
        Acquire('T6', 6),
        Release('T6', 6),
        Acquire('T7', 7),
        # missing release of lock 2 by T3: bad
    ]
    trace5 = [
        Acquire('T1', 1),
        Acquire('T2', 2),
        Release('T1', 1),
        Release('T2', 2),
        Release('T3', 3),
        Acquire('T4', 4),
        Acquire('T5', 4),
        Acquire('T6', 5)
    ]
    trace = [
        Acquire('T1', 1),
        Acquire('T2', 2),
        Acquire('T1', 2),
        Release('T1', 2)
    ]
    m = M1()
    m.verify(trace)





