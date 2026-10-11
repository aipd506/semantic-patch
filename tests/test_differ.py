"""Unit tests for semantic differ and round-trip patch generation."""

import unittest
from semantic_patch.differ import compute_semantic_diff
from semantic_patch.engine import SemanticPatchEngine
from semantic_patch.models import OperationType

ORIGINAL = '''import math

def calculate(x: int) -> float:
    return math.sqrt(x)

def unused():
    pass
'''

MODIFIED = '''import math
import sys

def calculate(x: int) -> float:
    if x < 0:
        raise ValueError("Must be positive")
    return math.sqrt(x)

def new_helper():
    return True
'''


class TestDiffer(unittest.TestCase):
    def test_diff_detects_changes(self):
        patch = compute_semantic_diff(ORIGINAL, MODIFIED, target_file="sample.py")

        ops = patch.operations
        op_types = [o.op for o in ops]

        # Should detect:
        # 1. INSERT_IMPORT 'import sys'
        # 2. DELETE_SYMBOL 'unused'
        # 3. REPLACE_SYMBOL 'calculate'
        # 4. INSERT_AFTER or INSERT_BEFORE for 'new_helper'
        self.assertIn(OperationType.INSERT_IMPORT, op_types)
        self.assertIn(OperationType.DELETE_SYMBOL, op_types)
        self.assertIn(OperationType.REPLACE_SYMBOL, op_types)

        # Check target of REPLACE_SYMBOL
        replace_op = next(o for o in ops if o.op == OperationType.REPLACE_SYMBOL)
        self.assertEqual(replace_op.target, "calculate")
        self.assertIn('raise ValueError("Must be positive")', replace_op.code)

    def test_diff_and_apply_roundtrip(self):
        patch = compute_semantic_diff(ORIGINAL, MODIFIED, target_file="sample.py")
        engine = SemanticPatchEngine()
        patched_code = engine.apply_patch(ORIGINAL, patch)

        # Verify that all elements in modified are present in patched
        self.assertIn("import sys", patched_code)
        self.assertIn('raise ValueError("Must be positive")', patched_code)
        self.assertIn("def new_helper():", patched_code)
        self.assertNotIn("def unused():", patched_code)


if __name__ == "__main__":
    unittest.main()
