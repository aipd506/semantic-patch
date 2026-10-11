# semantic-patch

Intent-preserving AST patches that never fail on line-shift merge conflicts.

Standard `patch` and `git apply` operate on strict line offsets (`@@ -14,7 +14,9 @@`). When another commit or pull request inserts lines upstream, standard patches fail with rejected hunks (`.rej` files), breaking automated AI agent workflows and developer rebases.

`semantic-patch` (`spatch`) operates directly on the Abstract Syntax Tree (AST). It targets functions, methods, classes, and statements by qualified symbol path. Even if 1,000 lines of unrelated code or comments are inserted above a function, `spatch` resolves the symbol and applies the patch cleanly.

## Key Capabilities

1. Line-Shift Immunity: Applies changes cleanly regardless of how many lines were added, moved, or deleted elsewhere in the file.
2. Auto-Reindentation: Modifies methods and nested blocks while automatically conforming to target indentation scope.
3. Syntax Integrity Guarantee: Re-parses AST and validates syntax after every operation.
4. Round-Trip Differ: Computes AST differences between two files and emits clean `.spatch` JSON manifests.
5. Zero External Dependencies: Pure Python standard library with zero runtime dependencies.

## Installation

```bash
pip install semantic-patch
```

Or install locally in editable mode:

```bash
git clone https://github.com/aipd506/semantic-patch.git
cd semantic-patch
pip install -e .
```

## Quick Start

### 1. Generate a Semantic Patch

```bash
spatch diff original.py modified.py -o feature.spatch
```

### 2. Inspect the Semantic Patch

```bash
spatch inspect feature.spatch
```

Example output:
```text
Semantic Patch: original.py (version 0.1.0)
Description: Semantic diff containing 2 operation(s)
Total Operations: 2
============================================================
[1] INSERT_IMPORT -> target: ''
    Note: Add import: import hashlib
[2] REPLACE_SYMBOL -> target: 'AuthService.authenticate'
    Note: Update symbol AuthService.authenticate
```

### 3. Verify Before Applying

```bash
spatch verify current_production.py feature.spatch
```

### 4. Apply In-Place

```bash
spatch apply current_production.py feature.spatch --in-place
```

### 5. Inspect Symbols in Any Source File

```bash
spatch symbols service.py
```

## Supported AST Operations

1. `replace_symbol`: Replaces a function, method, or class with new code, adapting indentation.
2. `insert_after`: Inserts a new definition or statement immediately after a target symbol.
3. `insert_before`: Inserts a definition before a target symbol.
4. `delete_symbol`: Safely deletes a symbol, preserving block syntax integrity.
5. `append_child`: Appends code into a class or function body.
6. `insert_import`: Automatically places imports at top of file, respecting module docstrings.

## License

Apache-2.0
