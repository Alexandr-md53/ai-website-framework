import pytest

from ai_framework.validation.context import ValidationContext
from ai_framework.validation.engine import ValidationEngine
from ai_framework.validation.exceptions import (
    EntitySchemaNotFoundError,
    InvalidSchemaError,
    UnknownValidatorError,
)
from ai_framework.validation.result import ValidationResult
from ai_framework.validation.validators.required import RequiredValidator
from ai_framework.validation.validators.type import TypeValidator
from ai_framework.validation.validators.unique import UniquenessValidator

from tests.fakes import FakeMetadataProvider, FakePersistenceProvider


@pytest.fixture
def engine():
    return ValidationEngine()


# --- Базовый счастливый путь и возвращаемые типы ---


@pytest.mark.asyncio
async def test_returns_validation_result_on_success(engine):
    payload = {"username": "john_doe"}
    rules = {"username": [RequiredValidator(), TypeValidator("string")]}

    result = await engine.validate(payload, rules)

    assert isinstance(result, ValidationResult)
    assert result.valid is True
    assert len(result.errors) == 0


@pytest.mark.asyncio
async def test_returns_validation_result_on_failure(engine):
    payload = {"username": 12345}
    rules = {"username": [TypeValidator("string")]}

    result = await engine.validate(payload, rules)

    assert isinstance(result, ValidationResult)
    assert result.valid is False
    assert len(result.errors) > 0


# --- Edge cases и сборы ошибок ---


@pytest.mark.asyncio
async def test_extra_fields_in_payload_are_ignored(engine):
    payload = {"username": "john_doe", "extra_field": "some_value"}
    rules = {"username": [RequiredValidator()]}

    result = await engine.validate(payload, rules)

    assert result.valid is True


@pytest.mark.asyncio
async def test_multiple_validators_on_single_field(engine):
    payload = {"age": "not_a_number"}
    rules = {
        "age": [
            TypeValidator("integer"),
            RequiredValidator(),
        ]
    }

    result = await engine.validate(payload, rules)

    assert result.valid is False
    assert len(result.errors) == 1
    assert result.errors[0].field == "age"


@pytest.mark.asyncio
async def test_first_error_does_not_stop_other_field_checks(engine):
    payload = {"username": None, "age": "invalid"}
    rules = {
        "username": [RequiredValidator()],
        "age": [TypeValidator("integer")],
    }

    result = await engine.validate(payload, rules)

    assert result.valid is False
    assert len(result.errors) == 2
    fields_with_errors = [e.field for e in result.errors]
    assert "username" in fields_with_errors
    assert "age" in fields_with_errors


@pytest.mark.asyncio
async def test_rule_without_params_as_string(engine):
    payload = {"email": None}
    rules = {"email": ["required"]}

    result = await engine.validate(payload, rules)

    assert result.valid is False
    assert result.errors[0].message_key == "validation.required"


@pytest.mark.asyncio
async def test_empty_list_rule_passes(engine):
    payload = {"field": "value"}
    rules = {"field": []}

    result = await engine.validate(payload, rules)

    assert result.valid is True


@pytest.mark.asyncio
async def test_none_rule_raises_invalid_schema(engine):
    payload = {"field": "value"}
    rules = {"field": None}

    with pytest.raises(InvalidSchemaError, match="Invalid rule definition: None"):
        await engine.validate(payload, rules)


@pytest.mark.asyncio
async def test_unknown_validator_string_raises_error(engine):
    payload = {"field": "value"}
    rules = {"field": ["non_existent_validator"]}

    with pytest.raises(UnknownValidatorError):
        await engine.validate(payload, rules)


# --- Тесты с Fake-провайдерами (без MagicMock) ---


@pytest.mark.asyncio
async def test_validate_entity_with_fake_metadata_provider():
    """Тест валидации сущности через FakeMetadataProvider."""
    fake_metadata = FakeMetadataProvider({"user": {"name": [RequiredValidator()]}})

    ctx = ValidationContext(metadata_provider=fake_metadata)
    custom_engine = ValidationEngine(context=ctx)

    result = await custom_engine.validate_entity("user", {"name": "Alice"})

    assert result.valid is True


@pytest.mark.asyncio
async def test_uniqueness_validator_with_fake_persistence():
    """Тест валидации уникальности через FakePersistenceProvider."""
    fake_db = FakePersistenceProvider()
    # Записываем сущность 'user', поле 'email' со значением 'exists@test.com'
    fake_db.add_record("user", "email", "exists@test.com")

    ctx = ValidationContext(persistence_provider=fake_db)
    custom_engine = ValidationEngine(context=ctx)

    rules = {"email": [UniquenessValidator("user")]}

    # Ошибка: email уже есть в фейковой БД
    res_fail = await custom_engine.validate({"email": "exists@test.com"}, rules)
    assert res_fail.valid is False
    assert res_fail.errors[0].field == "email"

    # Успех: email свободен
    res_pass = await custom_engine.validate({"email": "new@test.com"}, rules)
    assert res_pass.valid is True


@pytest.mark.asyncio
async def test_validate_entity_without_metadata_provider_raises_error(engine):
    with pytest.raises(EntitySchemaNotFoundError):
        await engine.validate_entity("user", {})
