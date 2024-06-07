
import json

from enum import Enum

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


Key = tuple[int, int]


class CommandMonitor:
    def __init__(self):
        self.event_nr: int = 0
        self.do_reply: set[Key] = set()
        self.do_complete: set[Key] = set()
        self.do_not_complete: set[Key] = set()

    def verify(self, trace: list[JsonObj]):
        for event in trace:
            self.event_nr += 1
            self.check(event)
        self.end()

    def end(self):
        for key in self.do_reply:
            self.error(f'at end waiting for {key} reply')
        for key in self.do_complete:
            self.error(f'at end waiting for {key} complete')

    def ensure(self, cond: bool, msg: str = ''):
        if not cond:
            self.error(msg)

    def error(self, msg: str = ''):
        print(f'***error at event {self.event_nr} {msg}')

    def check(self, event):
        # Assumptions:
        # - all events have: id, task_id, cmd_nr, cmd_type.
        # - all events identified by key = (task_id,cmd_nr).
        id = event['id']
        task_id = event['task_id']
        cmd_nr = event['cmd_nr']
        cmd_type = event['cmd_type']
        key = (task_id, cmd_nr)
        match id:
            case "dispatch":
                self.ensure(key not in self.do_reply, f'{key} already dispatched')
                if cmd_type == 'START':
                    self.do_reply.add(key)
            case "reply":
                if key in self.do_reply:
                    self.do_reply.remove(key)
                    self.do_complete.add(key)
            case "complete":
                if cmd_type == 'START':
                    self.ensure(key not in self.do_not_complete, f'{key} already completed')
                    if key in self.do_complete:
                        self.do_complete.remove(key)
                        self.do_not_complete.add(key)


if __name__ == '__main__':
    filePath = "file1.json"
    trace = parse_json_file(filePath)
    monitor = CommandMonitor()
    monitor.verify(trace)


