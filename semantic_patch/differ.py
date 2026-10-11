"""Diff engine generating SemanticPatch from original and modified sources."""

import ast
from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple
from .models import SemanticPatch, PatchOperation, OperationType
from .ast_utils import parse_symbols, SymbolNode


def extract_symbol_code(source: str, sym: SymbolNode) -> str:
    """Extract raw source lines for a symbol."""
    lines = source.splitlines()
    if 1 <= sym.start_line <= len(lines):
        end = min(sym.end_line, len(lines))
        return "\n".join(lines[sym.start_line - 1 : end])
    return ""


def extract_imports(source: str) -> List[str]:
    """Extract top-level import statements as strings."""
    lines = source.splitlines()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    import_stmts = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            start = getattr(node, "lineno", 1) - 1
            end = getattr(node, "end_lineno", start + 1)
            stmt = "\n".join(lines[start:end]).strip()
            if stmt and stmt not in import_stmts:
                import_stmts.append(stmt)
    return import_stmts


def compute_semantic_diff(orig_source: str, mod_source: str, target_file: str = "") -> SemanticPatch:
    """Compute semantic difference between two versions of Python code."""
    orig_syms = parse_symbols(orig_source)
    mod_syms = parse_symbols(mod_source)

    operations: List[PatchOperation] = []

    # 1. Detect missing or new imports
    orig_imports = set(extract_imports(orig_source))
    mod_imports = extract_imports(mod_source)
    for imp in mod_imports:
        if imp not in orig_imports:
            operations.append(
                PatchOperation(
                    op=OperationType.INSERT_IMPORT,
                    target="",
                    code=imp,
                    description=f"Add import: {imp}",
                )
            )

    # 2. Check for deleted symbols
    for qname, orig_node in orig_syms.items():
        if qname not in mod_syms:
            operations.append(
                PatchOperation(
                    op=OperationType.DELETE_SYMBOL,
                    target=qname,
                    description=f"Delete symbol {qname}",
                )
            )

    # 3. Check for modified symbols (exist in both)
    for qname, mod_node in mod_syms.items():
        if qname in orig_syms:
            orig_node = orig_syms[qname]
            orig_code = extract_symbol_code(orig_source, orig_node).strip()
            mod_code = extract_symbol_code(mod_source, mod_node).strip()

            if orig_code != mod_code:
                operations.append(
                    PatchOperation(
                        op=OperationType.REPLACE_SYMBOL,
                        target=qname,
                        code=mod_code,
                        description=f"Update symbol {qname}",
                    )
                )

    # 4. Check for added symbols (exist in mod but not orig)
    mod_order = list(mod_syms.keys())
    for idx, qname in enumerate(mod_order):
        if qname not in orig_syms:
            mod_node = mod_syms[qname]
            code = extract_symbol_code(mod_source, mod_node)

            # Try to place after the preceding symbol if present in orig
            preceding_target = None
            for p_idx in range(idx - 1, -1, -1):
                prev_name = mod_order[p_idx]
                if prev_name in orig_syms:
                    preceding_target = prev_name
                    break

            if preceding_target:
                operations.append(
                    PatchOperation(
                        op=OperationType.INSERT_AFTER,
                        target=preceding_target,
                        code=code,
                        description=f"Insert {qname} after {preceding_target}",
                    )
                )
            else:
                # Try placing before subsequent symbol
                next_target = None
                for n_idx in range(idx + 1, len(mod_order)):
                    nxt_name = mod_order[n_idx]
                    if nxt_name in orig_syms:
                        next_target = nxt_name
                        break

                if next_target:
                    operations.append(
                        PatchOperation(
                            op=OperationType.INSERT_BEFORE,
                            target=next_target,
                            code=code,
                            description=f"Insert {qname} before {next_target}",
                        )
                    )
                else:
                    # Top-level fallback or append
                    operations.append(
                        PatchOperation(
                            op=OperationType.INSERT_AFTER,
                            target=list(orig_syms.keys())[-1] if orig_syms else "",
                            code=code,
                            description=f"Insert {qname}",
                        )
                    )

    now_iso = datetime.now(timezone.utc).isoformat()
    return SemanticPatch(
        target_file=target_file,
        operations=operations,
        description=f"Semantic diff containing {len(operations)} operation(s)",
        created_at=now_iso,
    )
