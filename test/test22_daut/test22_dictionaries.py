
import json
from pycontract import *


JsonObj = dict[str, object]


################
# JSON Parsing #
################

def parse_json_file(file_path: str) -> list[JsonObj]:
    with open(file_path, 'r') as file:
        trace = json.load(file)
    return trace


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
            case {'id': 'dispatch', 'task_id': task_id, 'cmd_nr': cmd_nr, 'cmd_type': 'START'}:
                return CommandMonitor.DoReply(task_id, cmd_nr)

    @data
    class DoReply(HotState):
        task_id: int
        cmd_nr: int

        def transition(self, event):
            match event:
                case {'id': 'dispatch', 'task_id': self.task_id, 'cmd_nr': self.cmd_nr}:
                    return error()
                case {'id': 'reply', 'task_id': self.task_id}:
                    return CommandMonitor.DoComplete(self.task_id, self.cmd_nr)

    @data
    class DoComplete(HotState):
        task_id: int
        cmd_nr: int

        def transition(self, event):
            match event:
                case {'id': 'complete', 'task_id': self.task_id, 'cmd_nr': self.cmd_nr, 'cmd_type': 'START'}:
                    return CommandMonitor.DoNotComplete(self.task_id, self.cmd_nr)

    @data
    class DoNotComplete(State):
        task_id: int
        cmd_nr : str

        def transition(self, event):
            match event:
                case {'id': 'complete', 'task_id': self.task_id, 'cmd_nr': self.cmd_nr, 'cmd_type': 'START'}:
                    return error()


if __name__ == '__main__':
    # visualize(__file__, True)
    filePath = "file1.json"
    trace = parse_json_file(filePath)
    monitor = CommandMonitor()
    monitor.verify(trace)


