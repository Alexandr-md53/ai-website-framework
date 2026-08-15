from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ValidationError:
    field: str
    message_key: str
    params: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "message_key": self.message_key,
            "params": self.params or {},
        }


@dataclass
class ValidationResult:
    valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)

    def add_error(
        self,
        field: str,
        message_key: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.valid = False
        self.errors.append(
            ValidationError(
                field=field,
                message_key=message_key,
                params=params or {},
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [error.to_dict() for error in self.errors],
        }
