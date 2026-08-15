from typing import Protocol, Any, Dict, List, Optional, Union
from .context import ValidationContext
from .result import ValidationResult
from .types import (
    ValidationSchema,
    RuleDefinition,
)


class ValidatorProtocol(Protocol):
    name: str
    is_async: bool = False

    async def validate(
        self,
        value: Any,
        payload: Dict[str, Any],
        context: Optional[ValidationContext] = None,
    ) -> Optional[Dict[str, Any]]: ...


class ValidationEngineProtocol(Protocol):
    async def validate(
        self,
        payload: Dict[str, Any],
        schema: ValidationSchema,
        context: Optional[ValidationContext] = None,
    ) -> ValidationResult: ...

    async def validate_field(
        self,
        value: Any,
        rules: List[Union[str, RuleDefinition]],
        context: Optional[ValidationContext] = None,
    ) -> ValidationResult: ...

    async def validate_entity(
        self,
        entity_name: str,
        payload: Dict[str, Any],
        context: Optional[ValidationContext] = None,
    ) -> ValidationResult: ...

    def register_validator(self, name: str, validator: ValidatorProtocol) -> None: ...
