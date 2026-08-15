"""
Persistence Layer Subsystem

Provides protocol definitions for Repositories and UnitOfWork,
along with pagination structures and an in-memory repository implementation.
"""

from dataclasses import dataclass, replace, is_dataclass
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
)

T = TypeVar("T")
ID = TypeVar("ID")


@dataclass
class Pagination:
    """Параметры пагинации."""

    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return max(0, (self.page - 1) * self.page_size)


@dataclass
class PageResult(Generic[T]):
    """Результат выборки с пагинацией."""

    items: Sequence[T]
    total_count: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return (self.total_count + self.page_size - 1) // self.page_size


class BaseRepository(Protocol[T, ID]):
    """Протокол для Generic Repository."""

    async def get_by_id(self, entity_id: ID) -> Optional[T]: ...
    async def list_all(
        self, pagination: Optional[Pagination] = None
    ) -> PageResult[T]: ...
    async def find(
        self, filters: Dict[str, Any], pagination: Optional[Pagination] = None
    ) -> PageResult[T]: ...
    async def add(self, entity: T) -> T: ...
    async def update(self, entity_id: ID, data: Dict[str, Any]) -> Optional[T]: ...
    async def delete(self, entity_id: ID) -> bool: ...


class UnitOfWork(Protocol):
    """Протокол для управления транзакциями."""

    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class InMemoryRepository(Generic[T, ID]):
    """In-memory реализация репозитория для тестирования и быстрой прототипной разработки."""

    def __init__(self, id_field: str = "id") -> None:
        self.items: Dict[ID, T] = {}
        self.id_field = id_field
        self._auto_id_counter = 1

    async def get_by_id(self, entity_id: ID) -> Optional[T]:
        return self.items.get(entity_id)

    async def list_all(self, pagination: Optional[Pagination] = None) -> PageResult[T]:
        all_items = list(self.items.values())
        return self._paginate(all_items, pagination)

    async def find(
        self, filters: Dict[str, Any], pagination: Optional[Pagination] = None
    ) -> PageResult[T]:
        filtered: List[T] = []
        for item in self.items.values():
            match = True
            for key, expected_val in filters.items():
                val = (
                    getattr(item, key, None)
                    if hasattr(item, key)
                    else (item.get(key) if isinstance(item, dict) else None)
                )
                if val != expected_val:
                    match = False
                    break
            if match:
                filtered.append(item)

        return self._paginate(filtered, pagination)

    async def add(self, entity: T) -> T:
        current_id = getattr(entity, self.id_field, None)
        if current_id is None:
            current_id = self._auto_id_counter
            self._auto_id_counter += 1
            if is_dataclass(entity):
                entity = replace(entity, **{self.id_field: current_id})
            elif isinstance(entity, dict):
                entity[self.id_field] = current_id
            else:
                setattr(entity, self.id_field, current_id)

        self.items[current_id] = entity
        return entity

    async def update(self, entity_id: ID, data: Dict[str, Any]) -> Optional[T]:
        entity = await self.get_by_id(entity_id)
        if entity is None:
            return None

        if is_dataclass(entity):
            updated_entity = replace(entity, **data)
        elif isinstance(entity, dict):
            entity.update(data)
            updated_entity = entity
        else:
            for key, val in data.items():
                setattr(entity, key, val)
            updated_entity = entity

        self.items[entity_id] = updated_entity
        return updated_entity

    async def delete(self, entity_id: ID) -> bool:
        if entity_id in self.items:
            del self.items[entity_id]
            return True
        return False

    def _paginate(
        self, items: List[T], pagination: Optional[Pagination]
    ) -> PageResult[T]:
        total_count = len(items)
        if pagination is None:
            return PageResult(
                items=items,
                total_count=total_count,
                page=1,
                page_size=total_count if total_count > 0 else 20,
            )

        start = pagination.offset
        end = start + pagination.page_size
        paged_items = items[start:end]

        return PageResult(
            items=paged_items,
            total_count=total_count,
            page=pagination.page,
            page_size=pagination.page_size,
        )
