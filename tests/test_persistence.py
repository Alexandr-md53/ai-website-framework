import pytest
from dataclasses import dataclass
from typing import Optional

from framework.core.persistence import (
    InMemoryRepository,
    Pagination,
    PageResult,
)


@dataclass
class DummyEntity:
    id: Optional[int]
    name: str
    status: str = "active"


@pytest.fixture
def repository():
    repo = InMemoryRepository[DummyEntity, int](id_field="id")
    # Заполняем тестовыми данными (25 записей)
    for i in range(1, 26):
        status = "active" if i % 2 != 0 else "inactive"
        repo.items[i] = DummyEntity(id=i, name=f"Item {i}", status=status)
    return repo


@pytest.mark.asyncio
async def test_get_by_id_success(repository):
    item = await repository.get_by_id(1)
    assert item is not None
    assert item.name == "Item 1"


@pytest.mark.asyncio
async def test_get_by_id_not_found(repository):
    item = await repository.get_by_id(999)
    assert item is None


@pytest.mark.asyncio
async def test_pagination_offset_and_total_pages():
    pag = Pagination(page=2, page_size=10)
    assert pag.offset == 10

    res = PageResult(items=[], total_count=25, page=2, page_size=10)
    assert res.total_pages == 3


@pytest.mark.asyncio
async def test_list_all_with_pagination(repository):
    pag = Pagination(page=2, page_size=10)
    result = await repository.list_all(pagination=pag)

    assert result.total_count == 25
    assert len(result.items) == 10
    assert result.items[0].id == 11
    assert result.total_pages == 3


@pytest.mark.asyncio
async def test_find_with_filters(repository):
    filters = {"status": "inactive"}
    result = await repository.find(filters=filters)

    # Чётные числа от 1 до 25 -> 12 записей
    assert result.total_count == 12
    assert all(item.status == "inactive" for item in result.items)


@pytest.mark.asyncio
async def test_add_entity():
    repo = InMemoryRepository[DummyEntity, int](id_field="id")
    new_item = DummyEntity(id=None, name="New Created Item")

    saved = await repo.add(new_item)
    assert saved.id == 1

    retrieved = await repo.get_by_id(1)
    assert retrieved is not None
    assert retrieved.name == "New Created Item"


@pytest.mark.asyncio
async def test_update_entity(repository):
    updated = await repository.update(1, {"name": "Updated Name", "status": "archived"})
    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.status == "archived"


@pytest.mark.asyncio
async def test_delete_entity(repository):
    deleted = await repository.delete(1)
    assert deleted is True

    item = await repository.get_by_id(1)
    assert item is None
