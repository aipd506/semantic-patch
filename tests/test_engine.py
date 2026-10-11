"""Unit tests for SemanticPatchEngine operations and line-shift immunity."""

import unittest
from semantic_patch.engine import SemanticPatchEngine
from semantic_patch.models import SemanticPatch, PatchOperation, OperationType
from semantic_patch.ast_utils import parse_symbols, validate_syntax

BASE_CODE = '''def greet(name: str) -> str:
    return f"Hello, {name}!"

class Greeter:
    def format_title(self, name: str) -> str:
        return name.title()

def main():
    print(greet("world"))
'''


class TestSemanticPatchEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SemanticPatchEngine()

    def test_replace_function(self):
        op = PatchOperation(
            op=OperationType.REPLACE_SYMBOL,
            target="greet",
            code='def greet(name: str) -> str:\n    return f"Greetings, {name.strip()}!"',
        )
        patch = SemanticPatch(operations=[op])
        result = self.engine.apply_patch(BASE_CODE, patch)

        self.assertIn("Greetings, {name.strip()}!", result)
        valid, err = validate_syntax(result)
        self.assertTrue(valid, err)

    def test_replace_class_method_reindent(self):
        # Pass method with 0-indentation, engine must automatically re-indent to 4 spaces
        op = PatchOperation(
            op=OperationType.REPLACE_SYMBOL,
            target="Greeter.format_title",
            code='def format_title(self, name: str) -> str:\n    return name.upper()',
        )
        patch = SemanticPatch(operations=[op])
        result = self.engine.apply_patch(BASE_CODE, patch)

        self.assertIn("    def format_title(self, name: str) -> str:\n        return name.upper()", result)
        valid, err = validate_syntax(result)
        self.assertTrue(valid, err)

    def test_insert_after(self):
        op = PatchOperation(
            op=OperationType.INSERT_AFTER,
            target="greet",
            code='def farewell(name: str) -> str:\n    return f"Goodbye, {name}!"',
        )
        patch = SemanticPatch(operations=[op])
        result = self.engine.apply_patch(BASE_CODE, patch)

        self.assertIn("def farewell(name: str)", result)
        syms = parse_symbols(result)
        self.assertIn("farewell", syms)
        self.assertIn("greet", syms)

    def test_insert_before(self):
        op = PatchOperation(
            op=OperationType.INSERT_BEFORE,
            target="main",
            code='def prepare():\n    pass',
        )
        patch = SemanticPatch(operations=[op])
        result = self.engine.apply_patch(BASE_CODE, patch)

        syms = parse_symbols(result)
        self.assertIn("prepare", syms)
        self.assertTrue(syms["prepare"].start_line < syms["main"].start_line)

    def test_delete_symbol(self):
        op = PatchOperation(
            op=OperationType.DELETE_SYMBOL,
            target="Greeter.format_title",
        )
        patch = SemanticPatch(operations=[op])
        result = self.engine.apply_patch(BASE_CODE, patch)

        syms = parse_symbols(result)
        self.assertNotIn("Greeter.format_title", syms)
        self.assertIn("Greeter", syms)

    def test_line_shift_immunity(self):
        """CRITICAL: Line-shift conflict immunity test.
        If an upstream developer inserts 50 lines of comments at line 1,
        traditional git apply / patch fails with reject hunk.
        semantic-patch continues to resolve the symbol and applies with 100% precision.
        """
        # Inject 50 lines at the top of BASE_CODE
        drift_lines = "\n".join([f"# Unrelated upstream shift line {i}" for i in range(50)]) + "\n"
        drifted_code = drift_lines + BASE_CODE

        op = PatchOperation(
            op=OperationType.REPLACE_SYMBOL,
            target="main",
            code='def main():\n    print("patched cleanly despite 50-line drift")',
        )
        patch = SemanticPatch(operations=[op])
        result = self.engine.apply_patch(drifted_code, patch)

        self.assertIn("patched cleanly despite 50-line drift", result)
        self.assertIn("# Unrelated upstream shift line 49", result)
        valid, err = validate_syntax(result)
        self.assertTrue(valid, err)

    def test_insert_import(self):
        op = PatchOperation(
            op=OperationType.INSERT_IMPORT,
            target="",
            code="import logging",
        )
        patch = SemanticPatch(operations=[op])
        result = self.engine.apply_patch(BASE_CODE, patch)

        self.assertTrue(result.startswith("import logging\n"))
        valid, err = validate_syntax(result)
        self.assertTrue(valid, err)


if __name__ == "__main__":
    unittest.main()
