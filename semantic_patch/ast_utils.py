"""AST analysis and symbol extraction utilities for semantic-patch."""

import ast
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class SymbolNode:
    name: str
    qualified_name: str
    node_type: str
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    indent_level: int
    docstring: Optional[str] = None
    ast_node: Optional[ast.AST] = None


class SymbolVisitor(ast.NodeVisitor):
    """Traverse AST and catalog symbols with qualified paths and line boundaries."""

    def __init__(self, source_code: str):
        self.source_code = source_code
        self.lines = source_code.splitlines(keepends=True)
        self.symbols: Dict[str, SymbolNode] = {}
        self._scope_stack: List[str] = []

    def _get_indent(self, line_num: int) -> int:
        if 1 <= line_num <= len(self.lines):
            line = self.lines[line_num - 1]
            return len(line) - len(line.lstrip())
        return 0

    def _get_effective_start(self, node: ast.AST) -> Tuple[int, int]:
        """Compute the true start line and col, including leading decorators if any."""
        start_line = getattr(node, "lineno", 1)
        start_col = getattr(node, "col_offset", 0)

        decorators = getattr(node, "decorator_list", [])
        if decorators:
            first_dec = decorators[0]
            dec_line = getattr(first_dec, "lineno", start_line)
            dec_col = getattr(first_dec, "col_offset", start_col)
            if dec_line < start_line:
                start_line = dec_line
                start_col = dec_col

        return start_line, start_col

    def _register(self, node: ast.AST, name: str, node_type: str):
        qname = ".".join(self._scope_stack + [name])
        start_line, start_col = self._get_effective_start(node)
        end_line = getattr(node, "end_lineno", start_line)
        end_col = getattr(node, "end_col_offset", 0)
        indent = self._get_indent(start_line)
        doc = ast.get_docstring(node) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)) else None

        sym = SymbolNode(
            name=name,
            qualified_name=qname,
            node_type=node_type,
            start_line=start_line,
            start_col=start_col,
            end_line=end_line,
            end_col=end_col,
            indent_level=indent,
            docstring=doc,
            ast_node=node,
        )
        self.symbols[qname] = sym

    def visit_ClassDef(self, node: ast.ClassDef):
        self._register(node, node.name, "class")
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._register(node, node.name, "function")
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._register(node, node.name, "async_function")
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_Assign(self, node: ast.Assign):
        # Register top-level or class-level constants/variables
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._register(node, target.id, "variable")
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if isinstance(node.target, ast.Name):
            self._register(node, node.target.id, "annotated_variable")
        self.generic_visit(node)


def parse_symbols(source_code: str) -> Dict[str, SymbolNode]:
    """Parse source code and return a dictionary of qualified symbol names to SymbolNode."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        raise ValueError(f"Failed to parse source syntax: {e}") from e

    visitor = SymbolVisitor(source_code)
    visitor.visit(tree)
    return visitor.symbols


def validate_syntax(source_code: str) -> Tuple[bool, Optional[str]]:
    """Validate that code string forms valid Python syntax."""
    try:
        ast.parse(source_code)
        return True, None
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}"


def find_import_insertion_point(source_code: str) -> int:
    """Find the best 1-indexed line number to insert a new import statement."""
    lines = source_code.splitlines()
    if not lines:
        return 1

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return 1

    last_import_line = 0
    docstring_end_line = 0

    # Check for module docstring
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        docstring_end_line = getattr(tree.body[0], "end_lineno", 1)

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            end_line = getattr(node, "end_lineno", node.lineno)
            if end_line > last_import_line:
                last_import_line = end_line

    if last_import_line > 0:
        return last_import_line + 1

    if docstring_end_line > 0:
        return docstring_end_line + 1

    # After any shebang or coding comments
    idx = 0
    while idx < len(lines) and (lines[idx].startswith("#") or lines[idx].strip() == ""):
        idx += 1
    return idx + 1
