import json
import os
import unittest
from pycontract import *

class JsonlLoggingTest(unittest.TestCase):
    def setUp(self):
        Monitor.reset()
        self.log_file = Monitor.jsonl_filename
        if self.log_file and os.path.exists(self.log_file):
            os.remove(self.log_file)

    def tearDown(self):
        Monitor.reset()
        if self.log_file and os.path.exists(self.log_file):
           os.remove(self.log_file)

    def test_jsonl_output(self):
        monitor = Monitor()
        test_data = {"key": "value", "number": 42}
        monitor.report_ok(f"json{json.dumps(test_data)}")
        x = 88
        monitor.report_ok(f'json{{"kaj": "value", "number": {x}}}')
        self.assertTrue(os.path.exists(self.log_file))

        with open(self.log_file, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)
            logged_data = json.loads(lines[0])
            self.assertEqual(logged_data, test_data)
            logged_data = json.loads(lines[1])
            self.assertEqual(logged_data, {"kaj": "value", "number": 88})

if __name__ == '__main__':
    unittest.main()
