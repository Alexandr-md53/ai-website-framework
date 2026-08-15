import pytest
import sqlite3

from ai_framework.crud.engine import UniversalCRUDEngine
from ai_framework.crud.sqlite_persistence import SQLitePersistenceProvider


@pytest.fixture
def sqlite_provider(tmp_path):
    db_file = str(tmp_path / "test.db")

    # Инициализируем схему таблицы plants
    conn = sqlite3.connect(db_file)
    conn.execute(
        "CREATE TABLE plants (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL)"
    )
    conn.close()

    return SQLitePersistenceProvider(db_path=db_file)


@pytest.fixture
def sqlite_crud_engine(sqlite_provider):
    return UniversalCRUDEngine(
        validation_engine=None, persistence_provider=sqlite_provider
    )


@pytest.mark.asyncio
async def test_sqlite_crud_lifecycle(sqlite_crud_engine):
    # 1. Create
    create_res = await sqlite_crud_engine.create(
        "plants", {"name": "Orchid", "price": 15.5}
    )
    assert create_res.success is True
    plant_id = create_res.data["id"]

    # 2. Get
    get_res = await sqlite_crud_engine.get("plants", plant_id)
    assert get_res.success is True
    assert get_res.data["name"] == "Orchid"

    # 3. Update
    update_res = await sqlite_crud_engine.update("plants", plant_id, {"price": 18.0})
    assert update_res.success is True
    assert update_res.data["price"] == 18.0

    # 4. List
    list_res = await sqlite_crud_engine.list("plants")
    assert list_res.success is True
    assert len(list_res.data) == 1

    # 5. Delete
    delete_res = await sqlite_crud_engine.delete("plants", plant_id)
    assert delete_res.success is True

    # 6. Verify Delete
    get_after_delete = await sqlite_crud_engine.get("plants", plant_id)
    assert get_after_delete.success is False
    assert get_after_delete.errors[0].code == "NOT_FOUND"
