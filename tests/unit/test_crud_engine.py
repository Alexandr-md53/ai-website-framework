from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_framework.crud.contracts import CRUDContext, CRUDError, CRUDResult
from ai_framework.crud.engine import UniversalCRUDEngine


@pytest.fixture
def mock_validation_engine():
    engine = MagicMock()

    success_result = MagicMock()
    success_result.valid = True
    success_result.errors = []

    engine.validate_entity = AsyncMock(return_value=success_result)
    return engine


@pytest.fixture
def mock_persistence_provider():
    provider = MagicMock()
    provider.insert = AsyncMock(return_value={"id": 1, "name": "Rose"})
    provider.fetch = AsyncMock(return_value={"id": 1, "name": "Rose"})
    provider.fetch_all = AsyncMock(return_value=[{"id": 1, "name": "Rose"}])
    provider.update_record = AsyncMock(return_value={"id": 1, "name": "Updated Rose"})
    provider.delete_record = AsyncMock(return_value=True)
    provider.is_unique = AsyncMock(return_value=True)
    return provider


@pytest.fixture
def crud_engine(mock_validation_engine, mock_persistence_provider):
    return UniversalCRUDEngine(
        validation_engine=mock_validation_engine,
        persistence_provider=mock_persistence_provider,
    )


@pytest.mark.asyncio
async def test_create_success(crud_engine, mock_persistence_provider):
    payload = {"name": "Rose"}
    result = await crud_engine.create("plant", payload)

    assert result.success is True
    assert result.data == {"id": 1, "name": "Rose"}
    assert result.errors == []
    mock_persistence_provider.insert.assert_called_once_with("plant", payload)


@pytest.mark.asyncio
async def test_create_validation_failure(
    crud_engine, mock_validation_engine, mock_persistence_provider
):
    mock_error = MagicMock()
    mock_error.field = "name"
    mock_error.message_key = "validation.required"
    mock_error.params = {}

    fail_result = MagicMock()
    fail_result.valid = False
    fail_result.errors = [mock_error]

    mock_validation_engine.validate_entity = AsyncMock(return_value=fail_result)

    result = await crud_engine.create("plant", {})

    assert result.success is False
    assert result.data is None
    assert len(result.errors) == 1
    assert result.errors[0].code == "VALIDATION_ERROR"
    assert result.errors[0].field == "name"
    assert result.errors[0].message_key == "validation.required"
    mock_persistence_provider.insert.assert_not_called()


@pytest.mark.asyncio
async def test_create_persistence_error(crud_engine, mock_persistence_provider):
    mock_persistence_provider.insert = AsyncMock(
        side_effect=RuntimeError("Database connection lost")
    )

    result = await crud_engine.create("plant", {"name": "Rose"})

    assert result.success is False
    assert result.data is None
    assert len(result.errors) == 1
    assert result.errors[0].code == "PERSISTENCE_ERROR"
    assert "Database connection lost" in result.errors[0].params["details"]


@pytest.mark.asyncio
async def test_get_success(crud_engine, mock_persistence_provider):
    result = await crud_engine.get("plant", 1)

    assert result.success is True
    assert result.data == {"id": 1, "name": "Rose"}
    mock_persistence_provider.fetch.assert_called_once_with("plant", 1)


@pytest.mark.asyncio
async def test_get_not_found(crud_engine, mock_persistence_provider):
    mock_persistence_provider.fetch = AsyncMock(return_value=None)

    result = await crud_engine.get("plant", 999)

    assert result.success is False
    assert result.data is None
    assert len(result.errors) == 1
    assert result.errors[0].code == "NOT_FOUND"


# Файл: tests/unit/test_crud_engine.py


@pytest.mark.asyncio
async def test_list_success(crud_engine, mock_persistence_provider):
    expected_data = [{"id": 1, "name": "Rose"}]
    # Явно задаем, что возвращает мок
    mock_persistence_provider.fetch_all = AsyncMock(return_value=expected_data)

    result = await crud_engine.list("plant", filters={"type": "flower"})

    assert result.success is True
    assert result.data == expected_data


@pytest.mark.asyncio
async def test_update_success(crud_engine, mock_persistence_provider):
    payload = {"name": "Updated Rose"}
    result = await crud_engine.update("plant", 1, payload)

    assert result.success is True
    assert result.data == {"id": 1, "name": "Updated Rose"}
    mock_persistence_provider.update_record.assert_called_once_with("plant", 1, payload)


@pytest.mark.asyncio
async def test_delete_success(crud_engine, mock_persistence_provider):
    result = await crud_engine.delete("plant", 1)

    assert result.success is True
    assert result.data is True
    mock_persistence_provider.delete_record.assert_called_once_with("plant", 1)


@pytest.mark.asyncio
async def test_delete_not_found(crud_engine, mock_persistence_provider):
    mock_persistence_provider.delete_record = AsyncMock(return_value=False)

    result = await crud_engine.delete("plant", 999)

    assert result.success is False
    assert len(result.errors) == 1
    assert result.errors[0].code == "NOT_FOUND"
