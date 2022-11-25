import os
import unittest
from typing import List


class Test(unittest.TestCase):
    def assert_equal_files(self, file1: str, file2: str):
        with open(file1, 'r') as f1:
            text1 = f1.read()
        with open(file2, 'r') as f2:
            text2 = f2.read()
        self.assertEqual(text1, text2)

    def assert_equal(self, errors_expected: List[str], errors_actual: List[str]):
        self.assertEqual(set(errors_expected), set(errors_actual))

