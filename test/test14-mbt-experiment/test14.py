
from pycontract import *
from enum import Enum, auto
from random import randrange # https://docs.python.org/3/library/random.html
from multiprocessing import Process, Queue # https://docs.python.org/3/library/multiprocessing.html

"""
Experiment with model-based testing.

The script checks the following:

  output command turn-on-radio
    observe dispatch turn-on-radio
    observe complete turn-on-radio
  output command send
      in parallel:
        observe dispatch send with a message size
        observe repeatedly size times: send package
        observe finished sending
      and
        observe log-message  
    observe complete send
"""

"""
Issues illuminated:
- the spec is big, some more temporal logic like would be good
- missing a join operator, here we use a counter to count terminated
  processes.
"""


class Cmd(Enum):
    TURN_ON_RADIO = auto()
    SEND = auto()


class Evr(Enum):
    SEND_PACKAGE = auto()
    FINISHED_SENDING = auto()
    LOG_MESSAGE = auto()


class Tester(Monitor):
    def __init__(self, to_app):
        super().__init__()
        self.to_app = to_app
        self.commands_terminated = 0

    def send(self, cmd):
        print(f'... monitor sending command {cmd}')
        self.to_app.put(cmd)

    @initial
    class Start(State):
        def transition(self, event):
            match event:
                case 'start':
                    self.send({'command': Cmd.TURN_ON_RADIO})
                    return self.DispatchTurnOnRadio()

    class DispatchTurnOnRadio(HotState):
        def transition(self, event):
            match event:
                case {'dispatch': Cmd.TURN_ON_RADIO}:
                    return self.CompleteTurnOnRadio()

    class CompleteTurnOnRadio(HotState):
        def transition(self, event):
            match event:
                case {'complete': Cmd.TURN_ON_RADIO}:
                    self.send({'command': Cmd.SEND})
                    return self.DispatchSend()

    class DispatchSend(HotState):
        def transition(self, event):
            match event:
                case {'dispatch': Cmd.SEND, 'size': size}:
                    return [
                        self.LogMessage(),
                        self.SendPackages(size),
                        self.CompleteSend()
                    ]

    class LogMessage(HotState):
        def transition(self, event):
            match event:
                case {'evr': Evr.LOG_MESSAGE}:
                    self.monitor.commands_terminated += 1
                    return ok

    @data
    class SendPackages(HotState):
        size: str

        def transition(self, event):
            match event:
                case {'evr': Evr.SEND_PACKAGE}:
                    if self.size > 0:
                        return self.SendPackages(self.size - 1)
                    else:
                        return error(f'more packages sent than needed')
                case {'evr': Evr.FINISHED_SENDING}:
                    if self.size == 0:
                        self.monitor.commands_terminated += 1
                        return ok
                    else:
                        return error(f'not enough packages sent')

    class CompleteSend(HotState):
        def transition(self, event):
            match event:
                case {'complete': Cmd.SEND}:
                    self.send('stop')
                    if self.monitor.commands_terminated == 2:
                        return ok
                    else:
                        return error(f'commands terminate without all being done {self.monitor.commands_terminated}')


def tester(from_app, to_app):
    observer = Tester(to_app)
    set_debug(True)
    observer.eval('start')
    while True:
        print('??? tester ready to receive event')
        event = from_app.get()
        print(f'??? tester receives {event}')
        match event:
            case 'stop':
                observer.end()
                break
            case _:
                print(f'??? tester sending event to monitor {event}')
                observer.eval(event)


def application(from_obs, to_obs):
    def send(evr):
        print(f'!!! application sending evr {evr}')
        to_obs.put(evr)

    while True:
        print(f'!!! application ready to receive command')
        command = from_obs.get()
        print(f'!!! application received command {command}')
        match command:
            case 'stop':
                send('stop')
                break
            case {'command': Cmd.TURN_ON_RADIO}:
                send({'dispatch': Cmd.TURN_ON_RADIO})
                send({'complete': Cmd.TURN_ON_RADIO})
            case {'command': Cmd.SEND}:
                size = 3
                send({'dispatch': Cmd.SEND, 'size': size})
                send({'evr': Evr.LOG_MESSAGE})
                for p in range(size):
                    send({'evr': Evr.SEND_PACKAGE})
                send({'evr': Evr.FINISHED_SENDING})
                send({'complete': Cmd.SEND})


if __name__ == '__main__':
    visualize(__file__, True)
    to_app = Queue()
    to_obs = Queue()
    app = Process(target=application, args=(to_app, to_obs))
    obs = Process(target=tester, args=(to_obs, to_app))
    app.start()
    obs.start()
    app.join()
    obs.join()
