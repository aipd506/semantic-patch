"""Unit tests for AST analysis and symbol locator utilities."""

import unittest
from semantic_patch.ast_utils import (
    parse_symbols,
    validate_syntax,
    find_import_insertion_point,
)

SAMPLE_CODE = '''"""Module docstring."""

import os
import sys

GLOBAL_LIMIT = 100

def top_function(x: int) -> int:
    """A top level function."""
    return x * 2

class Calculator:
    """A simple calculator."""

    def add(self, a: int, b: int) -> int:
        return a + b

    @property
    def limit(self) -> int:
        return GLOBAL_LIMIT

async def fetch_data(url: str):
    return url
'''


class TestASTUtils(unittest.TestCase):
    def test_parse_symbols(self):
        syms = parse_symbols(SAMPLE_CODE)

        self.assertIn("GLOBAL_LIMIT", syms)
        self.assertIn("top_function", syms)
        self.assertIn("Calculator", syms)
        self.assertIn("Calculator.add", syms)
        self.assertIn("Calculator.limit", syms)
        self.assertIn("fetch_data", syms)

        # Check types
        self.assertEqual(syms["Calculator"].node_type, "class")
        self.assertEqual(syms["Calculator.add"].node_type, "function")
        self.assertEqual(syms["fetch_data"].node_type, "async_function")
        self.assertEqual(syms["GLOBAL_LIMIT"].node_type, "variable")

        # Check indentation
        self.assertEqual(syms["Calculator"].indent_level, 0)
        self.assertEqual(syms["Calculator.add"].indent_level, 4)

    def test_decorated_function_line(self):
        syms = parse_symbols(SAMPLE_CODE)
        limit_sym = syms["Calculator.limit"]
        # Limit has decorator @property, start_line should include the decorator
        lines = SAMPLE_CODE.splitlines()
        dec_line = lines[limit_sym.start_line - 1].strip()
        self.assertEqual(dec_line, "@property")

    def test_validate_syntax(self):
        valid, err = validate_syntax("def foo():\n    return 42\n")
        self.assertTrue(valid)
        self.assertIsNone(err)

        invalid, err = validate_syntax("def foo(:\n    return")
        self.assertFalse(invalid)
        self.assertIsNotNone(err)

    def test_find_import_insertion_point(self):
        line = find_import_insertion_point(SAMPLE_CODE)
        # Should be placed after 'import sys'
        lines = SAMPLE_CODE.splitlines()
        self.assertTrue(line > 3)
        self.assertTrue(lines[line - 2].startswith("import sys"))


if __name__ == "__main__":
    unittest.main()
