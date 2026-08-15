import pytest

from ai_framework.crud.engine import UniversalCRUDEngine
from ai_framework.crud.persistence import InMemoryPersistenceProvider


@pytest.fixture
def memory_crud_engine():
    provider = InMemoryPersistenceProvider()
    # Запускаем движок без валидатора для проверки персистентности
    return UniversalCRUDEngine(validation_engine=None, persistence_provider=provider)


@pytest.mark.asyncio
async def test_full_crud_lifecycle_in_memory(memory_crud_engine):
    # 1. Create
    create_res = await memory_crud_engine.create("plants", {"name": "Monstera"})
    assert create_res.success is True
    plant_id = create_res.data["id"]
    assert create_res.data["name"] == "Monstera"

    # 2. Get
    get_res = await memory_crud_engine.get("plants", plant_id)
    assert get_res.success is True
    assert get_res.data["name"] == "Monstera"

    # 3. Update
    update_res = await memory_crud_engine.update(
        "plants", plant_id, {"name": "Monstera Deliciosa"}
    )
    assert update_res.success is True
    assert update_res.data["name"] == "Monstera Deliciosa"

    # 4. List
    list_res = await memory_crud_engine.list("plants")
    assert list_res.success is True
    assert len(list_res.data) == 1

    # 5. Delete
    delete_res = await memory_crud_engine.delete("plants", plant_id)
    assert delete_res.success is True

    # 6. Verify Delete
    get_after_delete = await memory_crud_engine.get("plants", plant_id)
    assert get_after_delete.success is False
    assert get_after_delete.errors[0].code == "NOT_FOUND"
