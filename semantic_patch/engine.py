"""Semantic patch application engine."""

import ast
from typing import List, Tuple, Optional
from .models import SemanticPatch, PatchOperation, OperationType
from .ast_utils import parse_symbols, validate_syntax, find_import_insertion_point, SymbolNode


class SemanticPatchEngine:
    """Applies semantic AST operations cleanly to source text."""

    def __init__(self):
        pass

    @staticmethod
    def adjust_indentation(code: str, target_indent: int) -> str:
        """Adjust indentation of code block to match target indentation."""
        lines = code.splitlines()
        if not lines:
            return ""

        # Find minimum non-empty line indent in the code
        non_empty = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
        base_indent = min(non_empty) if non_empty else 0

        adjusted_lines = []
        for line in lines:
            if not line.strip():
                adjusted_lines.append("")
                continue
            curr_indent = len(line) - len(line.lstrip())
            stripped = line.lstrip()
            new_indent = target_indent + (curr_indent - base_indent)
            adjusted_lines.append(" " * max(0, new_indent) + stripped)

        return "\n".join(adjusted_lines)

    def apply_operation(self, source_code: str, op: PatchOperation) -> str:
        """Apply a single patch operation to source_code and return new source_code."""
        if op.op == OperationType.INSERT_IMPORT:
            return self._apply_insert_import(source_code, op)

        symbols = parse_symbols(source_code)
        target_sym = symbols.get(op.target)

        if not target_sym:
            available = list(symbols.keys())
            raise KeyError(
                f"Target symbol '{op.target}' not found in source. Available symbols: {available}"
            )

        if op.op == OperationType.REPLACE_SYMBOL:
            return self._apply_replace(source_code, target_sym, op.code)
        elif op.op == OperationType.INSERT_AFTER:
            return self._apply_insert_after(source_code, target_sym, op.code)
        elif op.op == OperationType.INSERT_BEFORE:
            return self._apply_insert_before(source_code, target_sym, op.code)
        elif op.op == OperationType.DELETE_SYMBOL:
            return self._apply_delete(source_code, target_sym)
        elif op.op == OperationType.APPEND_CHILD:
            return self._apply_append_child(source_code, target_sym, op.code)
        else:
            raise ValueError(f"Unsupported operation type: {op.op}")

    def _apply_replace(self, source: str, sym: SymbolNode, new_code: str) -> str:
        lines = source.splitlines(keepends=True)
        # Determine target indentation from the original symbol
        target_indent = sym.indent_level
        adjusted_code = self.adjust_indentation(new_code, target_indent)
        if not adjusted_code.endswith("\n"):
            adjusted_code += "\n"

        # Lines are 1-indexed. Replace [sym.start_line - 1 : sym.end_line]
        before = lines[: sym.start_line - 1]
        after = lines[sym.end_line :]

        result = "".join(before) + adjusted_code + "".join(after)
        is_valid, err = validate_syntax(result)
        if not is_valid:
            raise ValueError(f"Applying replace to '{sym.qualified_name}' created invalid syntax: {err}")
        return result

    def _apply_insert_after(self, source: str, sym: SymbolNode, new_code: str) -> str:
        lines = source.splitlines(keepends=True)
        target_indent = sym.indent_level
        adjusted_code = self.adjust_indentation(new_code, target_indent)

        # Spacing
        spacing = "\n\n" if target_indent == 0 else "\n"
        insertion = spacing + adjusted_code
        if not insertion.endswith("\n"):
            insertion += "\n"

        before = lines[: sym.end_line]
        after = lines[sym.end_line :]

        result = "".join(before) + insertion + "".join(after)
        is_valid, err = validate_syntax(result)
        if not is_valid:
            raise ValueError(f"Applying insert_after '{sym.qualified_name}' created invalid syntax: {err}")
        return result

    def _apply_insert_before(self, source: str, sym: SymbolNode, new_code: str) -> str:
        lines = source.splitlines(keepends=True)
        target_indent = sym.indent_level
        adjusted_code = self.adjust_indentation(new_code, target_indent)

        spacing = "\n\n" if target_indent == 0 else "\n"
        insertion = adjusted_code + spacing

        before = lines[: sym.start_line - 1]
        after = lines[sym.start_line - 1 :]

        result = "".join(before) + insertion + "".join(after)
        is_valid, err = validate_syntax(result)
        if not is_valid:
            raise ValueError(f"Applying insert_before '{sym.qualified_name}' created invalid syntax: {err}")
        return result

    def _apply_delete(self, source: str, sym: SymbolNode) -> str:
        lines = source.splitlines(keepends=True)
        before = lines[: sym.start_line - 1]
        after = lines[sym.end_line :]

        result = "".join(before) + "".join(after)
        is_valid, err = validate_syntax(result)
        if not is_valid:
            # Check if substituting pass satisfies empty block requirements (e.g. class or def body)
            fallback_result = "".join(before) + (" " * sym.indent_level + "pass\n") + "".join(after)
            is_fb_valid, _ = validate_syntax(fallback_result)
            if is_fb_valid:
                return fallback_result
            raise ValueError(f"Applying delete to '{sym.qualified_name}' created invalid syntax: {err}")
        return result

    def _apply_append_child(self, source: str, sym: SymbolNode, new_code: str) -> str:
        lines = source.splitlines(keepends=True)
        child_indent = sym.indent_level + 4
        adjusted_code = self.adjust_indentation(new_code, child_indent)
        insertion = "\n" + adjusted_code
        if not insertion.endswith("\n"):
            insertion += "\n"

        before = lines[: sym.end_line]
        after = lines[sym.end_line :]

        result = "".join(before) + insertion + "".join(after)
        is_valid, err = validate_syntax(result)
        if not is_valid:
            raise ValueError(f"Applying append_child to '{sym.qualified_name}' created invalid syntax: {err}")
        return result

    def _apply_insert_import(self, source: str, op: PatchOperation) -> str:
        import_stmt = op.code.strip()
        if import_stmt in source:
            # Already imported
            return source

        insertion_line = find_import_insertion_point(source)
        lines = source.splitlines(keepends=True)

        stmt = import_stmt + "\n"
        if insertion_line <= len(lines):
            before = lines[: insertion_line - 1]
            after = lines[insertion_line - 1 :]
            result = "".join(before) + stmt + "".join(after)
        else:
            result = "".join(lines) + stmt

        is_valid, err = validate_syntax(result)
        if not is_valid:
            raise ValueError(f"Applying insert_import created invalid syntax: {err}")
        return result

    def apply_patch(self, source_code: str, patch: SemanticPatch) -> str:
        """Apply all operations in a SemanticPatch sequentially, re-indexing AST between ops."""
        current = source_code
        for idx, op in enumerate(patch.operations, start=1):
            try:
                current = self.apply_operation(current, op)
            except Exception as e:
                raise RuntimeError(f"Failed applying operation {idx} ({op.op.value} on '{op.target}'): {e}") from e
        return current
