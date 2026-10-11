"""Command line interface for semantic-patch."""

import argparse
import sys
from pathlib import Path
from .models import SemanticPatch
from .differ import compute_semantic_diff
from .engine import SemanticPatchEngine
from .ast_utils import parse_symbols, validate_syntax


def cmd_diff(args) -> int:
    orig_path = Path(args.original)
    mod_path = Path(args.modified)

    if not orig_path.exists():
        sys.stderr.write(f"Error: Original file '{orig_path}' not found.\n")
        return 1
    if not mod_path.exists():
        sys.stderr.write(f"Error: Modified file '{mod_path}' not found.\n")
        return 1

    orig_text = orig_path.read_text(encoding="utf-8")
    mod_text = mod_path.read_text(encoding="utf-8")

    patch = compute_semantic_diff(orig_text, mod_text, target_file=str(orig_path.name))

    patch_json = patch.to_json()

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(patch_json, encoding="utf-8")
        print(f"Semantic patch saved to {out_path} ({len(patch.operations)} operations)")
    else:
        print(patch_json)

    return 0


def cmd_apply(args) -> int:
    target_path = Path(args.target)
    patch_path = Path(args.patch)

    if not target_path.exists():
        sys.stderr.write(f"Error: Target file '{target_path}' not found.\n")
        return 1
    if not patch_path.exists():
        sys.stderr.write(f"Error: Patch file '{patch_path}' not found.\n")
        return 1

    target_text = target_path.read_text(encoding="utf-8")
    patch_text = patch_path.read_text(encoding="utf-8")

    patch = SemanticPatch.from_json(patch_text)
    engine = SemanticPatchEngine()

    try:
        updated_text = engine.apply_patch(target_text, patch)
    except Exception as e:
        sys.stderr.write(f"Error applying semantic patch: {e}\n")
        return 1

    if args.in_place:
        target_path.write_text(updated_text, encoding="utf-8")
        print(f"Applied {len(patch.operations)} operation(s) in-place to {target_path}")
    elif args.output:
        out_path = Path(args.output)
        out_path.write_text(updated_text, encoding="utf-8")
        print(f"Applied {len(patch.operations)} operation(s) saved to {out_path}")
    else:
        sys.stdout.write(updated_text)

    return 0


def cmd_verify(args) -> int:
    target_path = Path(args.target)
    patch_path = Path(args.patch)

    if not target_path.exists():
        sys.stderr.write(f"Error: Target file '{target_path}' not found.\n")
        return 1
    if not patch_path.exists():
        sys.stderr.write(f"Error: Patch file '{patch_path}' not found.\n")
        return 1

    target_text = target_path.read_text(encoding="utf-8")
    patch_text = patch_path.read_text(encoding="utf-8")

    patch = SemanticPatch.from_json(patch_text)
    engine = SemanticPatchEngine()

    try:
        updated_text = engine.apply_patch(target_text, patch)
        is_valid, err = validate_syntax(updated_text)
        if not is_valid:
            sys.stderr.write(f"Verification failed: resulting syntax invalid: {err}\n")
            return 1
    except Exception as e:
        sys.stderr.write(f"Verification failed: {e}\n")
        return 1

    print(f"Verification successful: {len(patch.operations)} operation(s) apply cleanly with valid syntax.")
    return 0


def cmd_inspect(args) -> int:
    patch_path = Path(args.patch)
    if not patch_path.exists():
        sys.stderr.write(f"Error: Patch file '{patch_path}' not found.\n")
        return 1

    patch_text = patch_path.read_text(encoding="utf-8")
    patch = SemanticPatch.from_json(patch_text)

    print(f"Semantic Patch: {patch.target_file} (version {patch.version})")
    print(f"Description: {patch.description}")
    print(f"Created: {patch.created_at}")
    print(f"Total Operations: {len(patch.operations)}")
    print("=" * 60)

    for i, op in enumerate(patch.operations, start=1):
        print(f"[{i}] {op.op.value.upper()} -> target: '{op.target}'")
        if op.description:
            print(f"    Note: {op.description}")
        if op.code:
            lines = op.code.strip().splitlines()
            preview = lines[0] if lines else ""
            if len(lines) > 1:
                preview += f" ... ({len(lines)} lines)"
            print(f"    Code: {preview}")
    return 0


def cmd_symbols(args) -> int:
    target_path = Path(args.file)
    if not target_path.exists():
        sys.stderr.write(f"Error: File '{target_path}' not found.\n")
        return 1

    text = target_path.read_text(encoding="utf-8")
    syms = parse_symbols(text)

    print(f"Discovered {len(syms)} symbol(s) in {target_path}:")
    for qname, node in syms.items():
        print(f"  [{node.node_type}] {qname} (lines {node.start_line}-{node.end_line}, indent {node.indent_level})")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="spatch",
        description="Intent-preserving AST patches that never fail on line-shift merge conflicts",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # diff
    p_diff = subparsers.add_parser("diff", help="Generate semantic patch from two files")
    p_diff.add_argument("original", help="Original Python source file")
    p_diff.add_argument("modified", help="Modified Python source file")
    p_diff.add_argument("-o", "--output", help="Output .spatch file path")
    p_diff.set_defaults(func=cmd_diff)

    # apply
    p_apply = subparsers.add_parser("apply", help="Apply semantic patch to target file")
    p_apply.add_argument("target", help="Target Python source file to modify")
    p_apply.add_argument("patch", help="Path to .spatch file")
    p_apply.add_argument("-i", "--in-place", action="store_true", help="Modify file in-place")
    p_apply.add_argument("-o", "--output", help="Write modified code to output file")
    p_apply.set_defaults(func=cmd_apply)

    # verify
    p_verify = subparsers.add_parser("verify", help="Verify patch applicability and syntax without writing")
    p_verify.add_argument("target", help="Target Python source file")
    p_verify.add_argument("patch", help="Path to .spatch file")
    p_verify.set_defaults(func=cmd_verify)

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect operations in a .spatch file")
    p_inspect.add_argument("patch", help="Path to .spatch file")
    p_inspect.set_defaults(func=cmd_inspect)

    # symbols
    p_symbols = subparsers.add_parser("symbols", help="List AST symbols in a Python file")
    p_symbols.add_argument("file", help="Python source file to inspect")
    p_symbols.set_defaults(func=cmd_symbols)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
