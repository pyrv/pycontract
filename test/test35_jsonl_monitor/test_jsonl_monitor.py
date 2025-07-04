import json
import os
import unittest
from pycontract import *

@dataclass
class Start:
    pass

@dataclass
class Log:
    time: int
    data: str

@dataclass
class End:
    pass

class LoggingMonitor(Monitor):
    def transition(self, event):
        match event:
            case Log(time, data):
                return self.ok_message(
                    {"time": time, 
                    "data": data}
                )

class JsonlMonitorTest(unittest.TestCase):
    def setUp(self):
        Monitor.reset()
        self.log_file = "pycontract_log.jsonl"
        set_jsonl(self.log_file)
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

    def no_tearDown(self):
        Monitor.reset()
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        set_jsonl(None) # Disable logging for other tests

    def test_monitor_jsonl_output(self):
        monitor = LoggingMonitor()
        trace = [
            Start(),
            Log(10, "data1"),
            Log(20, "data2"),
            End()
        ]
        monitor.verify(trace)

        self.assertTrue(os.path.exists(self.log_file))

        with open(self.log_file, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)
            logged_data = json.loads(lines[0])
            expected_data = {"time": 10, "data": "data1"}
            self.assertEqual(logged_data, expected_data)
            logged_data = json.loads(lines[1])
            expected_data = {"time": 20, "data": "data2"}
            self.assertEqual(logged_data, expected_data)

if __name__ == '__main__':
    unittest.main()
