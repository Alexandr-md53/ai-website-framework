import sqlite3
import pytest

from ai_framework.crud.engine import UniversalCRUDEngine
from ai_framework.crud.sqlite_persistence import SQLitePersistenceProvider
from ai_framework.validation.result import ValidationResult


class IntegrationValidationEngine:
    """Интеграционный ValidationEngine для проверки связи CRUD и SQLite."""

    async def validate_entity(
        self, entity_name: str, payload: dict
    ) -> ValidationResult:
        result = ValidationResult(valid=True, errors=[])

        name = payload.get("name")
        if not name:
            result.add_error(field="name", message_key="validation.required")
        elif isinstance(name, str) and len(name) < 3:
            result.add_error(
                field="name",
                message_key="validation.min_length",
                params={"min_length": 3},
            )

        return result


@pytest.fixture
def sqlite_integration_db(tmp_path):
    db_file = str(tmp_path / "integration.db")

    conn = sqlite3.connect(db_file)
    conn.execute(
        "CREATE TABLE plants (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT)"
    )
    conn.close()

    return db_file


@pytest.fixture
def integrated_crud_engine(sqlite_integration_db):
    validation_engine = IntegrationValidationEngine()
    persistence_provider = SQLitePersistenceProvider(db_path=sqlite_integration_db)

    return UniversalCRUDEngine(
        validation_engine=validation_engine,
        persistence_provider=persistence_provider,
    )


@pytest.mark.asyncio
async def test_integration_create_valid_record(integrated_crud_engine):
    payload = {"name": "Ficus", "type": "tree"}

    result = await integrated_crud_engine.create("plants", payload)

    assert result.success is True
    assert result.data["id"] == 1
    assert result.data["name"] == "Ficus"

    # Проверяем через list, что запись действительно попала в БД
    list_result = await integrated_crud_engine.list("plants")
    assert list_result.success is True
    assert len(list_result.data) == 1


@pytest.mark.asyncio
async def test_integration_create_invalid_record_blocks_db(integrated_crud_engine):
    # Ошибка: имя слишком короткое (< 3 символов)
    payload = {"name": "Al"}

    result = await integrated_crud_engine.create("plants", payload)

    assert result.success is False
    assert len(result.errors) > 0
    assert result.errors[0].code == "VALIDATION_ERROR"
    assert result.errors[0].field == "name"

    # Убеждаемся, что база данных осталась пустой (валидация заблокировала запись)
    list_result = await integrated_crud_engine.list("plants")
    assert list_result.success is True
    assert len(list_result.data) == 0
