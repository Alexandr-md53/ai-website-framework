"""
framework/validation/engine.py
-------------------------------
Главный движок валидации, отвечающий за компиляцию схем и исполнение правил.
"""

from typing import Any, Dict, List, Optional, Type, Union

from ai_framework.validation.context import ValidationContext
from ai_framework.validation.exceptions import (
    EntitySchemaNotFoundError,
    InvalidSchemaError,
    UnknownValidatorError,
)
from ai_framework.validation.result import ValidationResult
from ai_framework.validation.validators.base import Validator
from ai_framework.validation.validators.format import FormatValidator
from ai_framework.validation.validators.length import LengthValidator
from ai_framework.validation.validators.required import RequiredValidator
from ai_framework.validation.validators.slug import SlugValidator
from ai_framework.validation.validators.type import TypeValidator
from ai_framework.validation.validators.unique import UniquenessValidator


class ValidationEngine:
    """Движок валидации данных и сущностей фреймворка."""

    # Реестр доступных строковых правил
    BUILTIN_VALIDATORS: Dict[str, Type[Validator]] = {
        "required": RequiredValidator,
        "type": TypeValidator,
        "length": LengthValidator,
        "format": FormatValidator,
        "unique": UniquenessValidator,
        "slug": SlugValidator,
    }

    def __init__(self, context: Optional[ValidationContext] = None):
        self.context = context or ValidationContext()
        self._custom_validators: Dict[str, Type[Validator]] = {}

    def register_validator(self, name: str, validator_cls: Type[Validator]) -> None:
        """Регистрирует кастомный валидатор."""
        self._custom_validators[name] = validator_cls

    async def validate(
        self,
        payload: Dict[str, Any],
        rules: Dict[str, List[Union[Validator, Dict[str, Any], str]]],
    ) -> ValidationResult:
        """
        Валидирует payload по набору правил (объекты Validator, dict или str).
        """
        result = ValidationResult(valid=True)
        compiled_rules = self._compile_schema(rules)

        for field_path, validators in compiled_rules.items():
            value = payload.get(field_path)

            for validator in validators:
                error = await validator.validate(
                    field=field_path,
                    value=value,
                    payload=payload,
                    context=self.context,
                )

                if error:
                    result.add_error(
                        field=error["field"],
                        message_key=error["message_key"],
                        params=error.get("params"),
                    )

        return result

    async def validate_entity(
        self, entity_name: str, payload: Dict[str, Any]
    ) -> ValidationResult:
        """Валидирует payload сущности по имени схемы из MetadataProvider."""
        if not self.context.metadata_provider:
            raise EntitySchemaNotFoundError(
                "MetadataProvider is not configured in ValidationContext."
            )

        schema = self.context.metadata_provider.get_schema(entity_name)
        return await self.validate(payload, schema)

    def _compile_schema(self, schema: Dict[str, Any]) -> Dict[str, List[Validator]]:
        compiled_rules: Dict[str, List[Validator]] = {}

        if not isinstance(schema, dict):
            raise InvalidSchemaError("Schema must be a dictionary.")

        for field_name, rules_list in schema.items():
            compiled_rules[field_name] = []

            if not isinstance(rules_list, list):
                rules_list = [rules_list]

            for rule_def in rules_list:
                # ПРИОРИТЕТ: Проверяем, является ли объект валидатором или имеет ли он метод validate
                if isinstance(rule_def, Validator) or hasattr(rule_def, "validate"):
                    compiled_rules[field_name].append(rule_def)
                elif isinstance(rule_def, dict):
                    rule_name = rule_def.get("rule")
                    if not rule_name:
                        raise InvalidSchemaError(
                            f"Missing 'rule' key in rule definition: {rule_def}"
                        )
                    params = {k: v for k, v in rule_def.items() if k != "rule"}
                    validator_obj = self._create_validator_instance(rule_name, params)
                    compiled_rules[field_name].append(validator_obj)
                elif isinstance(rule_def, str):
                    validator_obj = self._create_validator_instance(rule_def, {})
                    compiled_rules[field_name].append(validator_obj)
                else:
                    raise InvalidSchemaError(f"Invalid rule definition: {rule_def}")

        return compiled_rules

    def _create_validator_instance(
        self, rule_name: str, params: Dict[str, Any]
    ) -> Validator:
        """Инстанцирует валидатор по имени из реестра с переданными параметрами."""
        validator_cls = self._custom_validators.get(
            rule_name
        ) or self.BUILTIN_VALIDATORS.get(rule_name)

        if not validator_cls:
            raise UnknownValidatorError(f"Validator '{rule_name}' is not registered.")

        try:
            return validator_cls(**params)
        except TypeError as e:
            raise InvalidSchemaError(
                f"Invalid parameters for validator '{rule_name}': {e}"
            )
