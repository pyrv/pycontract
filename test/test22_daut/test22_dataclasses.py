
import json
from pycontract import *

JsonObj = dict[str, object]

################
# JSON Parsing #
################

def parse_json_event(d: JsonObj) -> Event:
    match d["id"]:
        case "dispatch":
            return Dispatch(d["task_id"], d["cmd_nr"], d["cmd_type"])
        case "reply":
            return Reply(d["task_id"], d["cmd_nr"], d["cmd_type"])
        case "complete":
            return Complete(d["task_id"], d["cmd_nr"], d["cmd_type"])
        case _:
            return Other(d)


def parse_json_file(file_path: str) -> list[Event]:
    trace: list[Event] = []
    with open(file_path, 'r') as file:
        data = json.load(file)
        for d in data:
            trace.append(parse_json_event(d))
    return trace


##############
# Event Type #
##############

class Event:
    pass


@data
class Dispatch(Event):
    task_id: int
    cmd_nr: int
    cmd_type: str


@data
class Reply(Event):
    task_id: int
    cmd_nr: int
    cmd_type: str


@data
class Complete(Event):
    task_id: int
    cmd_nr: int
    cmd_type: str


@data
class Other(Event):
    json: dict[str, object]


###########
# Monitor #
###########

"""
Requirement:
1. A START Dispatch must be followed by a START Reply,
   with the same task id and command nr.
2. No Reply should occur in between with the same task id.
3. After the Reply, a START Complete should occur, with the same
   task id and command nr.
4. After START Complete, no more START Completes should occur with
   the same task id and command nr.
"""


class CommandMonitor(Monitor):
    def transition(self, event):
        match event:
            case Dispatch(task_id, cmd_nr, "START"):
                return CommandMonitor.DoReply(task_id, cmd_nr)

    @data
    class DoReply(HotState):
        task_id: int
        cmd_nr: int

        def transition(self, event):
            match event:
                case Dispatch(self.task_id, self.cmd_nr, _):
                    return error()
                case Reply(self.task_id, _, _):
                    return CommandMonitor.DoComplete(self.task_id, self.cmd_nr)

    @data
    class DoComplete(HotState):
        task_id: int
        cmd_nr: int

        def transition(self, event):
            match event:
                case Complete(self.task_id, self.cmd_nr, "START"):
                    return CommandMonitor.DoNotComplete(self.task_id, self.cmd_nr)

    @data
    class DoNotComplete(State):
        task_id: int
        cmd_nr : str

        def transition(self, event):
            match event:
                case Complete(self.task_id, self.cmd_nr, "START"):
                    return error()


if __name__ == '__main__':
    filePath = "file1.json"
    trace = parse_json_file(filePath)
    monitor = CommandMonitor()
    monitor.verify(trace)


