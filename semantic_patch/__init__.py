"""semantic-patch: Intent-preserving AST patches that never fail on line-shift merge conflicts."""

from .models import SemanticPatch, PatchOperation, OperationType
from .ast_utils import parse_symbols, validate_syntax, SymbolNode
from .engine import SemanticPatchEngine
from .differ import compute_semantic_diff

__version__ = "0.1.0"
__all__ = [
    "SemanticPatch",
    "PatchOperation",
    "OperationType",
    "parse_symbols",
    "validate_syntax",
    "SymbolNode",
    "SemanticPatchEngine",
    "compute_semantic_diff",
]
