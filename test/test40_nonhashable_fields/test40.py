
from test import utest
from dataclasses import field
import pycontract as pc

"""
Tests that a state with unhashable field results in a proper system exit.
"""

class M(pc.Monitor):
    def transition(self, event):
        return M.S(event, {'e': event})

    @pc.data
    class S(pc.State):
        e: int
        d: dict

class TestExit(utest.Test):
    def test_exit_code(self):
        m = M()
        with self.assertRaises(SystemExit) as cm:
            m.eval(1)
        self.assertEqual(cm.exception.code, 2)

