"""Data models for semantic-patch."""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any
import json


class OperationType(str, Enum):
    REPLACE_SYMBOL = "replace_symbol"
    INSERT_AFTER = "insert_after"
    INSERT_BEFORE = "insert_before"
    DELETE_SYMBOL = "delete_symbol"
    APPEND_CHILD = "append_child"
    INSERT_IMPORT = "insert_import"


@dataclass
class PatchOperation:
    op: OperationType
    target: str
    code: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "op": self.op.value if isinstance(self.op, OperationType) else self.op,
            "target": self.target,
            "code": self.code,
            "description": self.description,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatchOperation":
        return cls(
            op=OperationType(data["op"]),
            target=data.get("target", ""),
            code=data.get("code", ""),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SemanticPatch:
    version: str = "0.1.0"
    target_file: str = ""
    operations: List[PatchOperation] = field(default_factory=list)
    description: str = ""
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "target_file": self.target_file,
            "description": self.description,
            "created_at": self.created_at,
            "operations": [op.to_dict() for op in self.operations],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SemanticPatch":
        ops = [PatchOperation.from_dict(item) for item in data.get("operations", [])]
        return cls(
            version=data.get("version", "0.1.0"),
            target_file=data.get("target_file", ""),
            operations=ops,
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "SemanticPatch":
        data = json.loads(json_str)
        return cls.from_dict(data)
