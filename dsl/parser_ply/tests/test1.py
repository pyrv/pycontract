import unittest

from dsl.parser_ply.pyco import PyContractModule
from pycontract import set_debug, Monitor

class TestCase(unittest.TestCase):
    def has_errors(self, monitor: Monitor, *errors: list[str]):
        messages = monitor.get_all_message_texts()
        self.assertTrue(
            len(errors) == len(messages) and all(
                any(
                    all(error_fragment in message for error_fragment in error)
                    for message in messages
                )
                for error in errors
            )
        )

class TestParser(TestCase):
    def test_1(self):
        spec = """
        events Exec {
          Command(name: str, time: int, number: int,msg: str)
          Complete(name: str, time: int, number: int)
        }
        
        monitor M[Exec] {
          case Command(name=n?, number=x?): Seen(n,x)
          hot Seen(name: str, number: int) {
            veto Command(number=number)
            case Complete(name=name, number=number): ok
          }
        }
        """
        pycomod = PyContractModule(spec)
        mod = pycomod.module
        code = pycomod.code
        print(code)
        m = mod.M()
        set_debug(True)
        m.verify([
            mod.Command(name="A", time=0, number=1, msg="A commanded"),
            mod.Command(name="A", time=1, number=1, msg="A commanded"),
            mod.Command(name="B", time=2, number=2, msg="B commanded"),
            mod.Complete(name="B", time=3, number=2),
            mod.Command(name="C", time=4, number=3, msg="C commanded"),
        ])

        self.has_errors(m,
                        ["error transition", "state Seen('A', 1)", "event 2"],
                        ["HOT STATE", "Seen('C', 3)"],
                        ["HOT STATE", "Seen('A', 1)"]
                        )

