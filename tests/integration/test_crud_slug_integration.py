"""
Integration tests: Universal CRUD Engine + SLG_01 (Slug Service).
Verifies orchestration, availability callbacks, and custom slug invariants.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import pytest

from ai_framework.crud.engine import CRUDEngine
from ai_framework.services.slug import (
    SlugCollisionError,
    SlugGenerator,
)


@dataclass(frozen=True)
class SlugConfig:
    """Integration metadata defining slug behavior for CRUD Engine."""

    target_field: str = "slug"
    source_field: str = "name"
    auto_generate: bool = True
    overwrite_on_update: bool = False


@dataclass
class DummyPlantSchema:
    """Reference Domain Model for Plant integration."""

    id: Optional[int] = None
    name: str = ""
    slug: Optional[str] = None

    __slug_config__ = SlugConfig(
        target_field="slug",
        source_field="name",
        auto_generate=True,
    )


class InMemoryPersistenceProvider:
    """Mock persistence layer for integration testing."""

    def __init__(self) -> None:
        self.storage: Dict[int, Dict[str, Any]] = {}
        self._next_id = 1

    def exists(
        self,
        field: str,
        value: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        for entity_id, record in self.storage.items():
            if exclude_id is not None and entity_id == exclude_id:
                continue
            if record.get(field) == value:
                return True
        return False

    def save(self, data: dict) -> dict:
        if "id" not in data or data["id"] is None:
            data["id"] = self._next_id
            self._next_id += 1
        self.storage[data["id"]] = data
        return data


@pytest.fixture
def persistence() -> InMemoryPersistenceProvider:
    return InMemoryPersistenceProvider()


@pytest.fixture
def slug_service() -> SlugGenerator:
    return SlugGenerator()


@pytest.mark.asyncio
async def test_crud_create_auto_generates_slug(
    persistence: InMemoryPersistenceProvider,
    slug_service: SlugGenerator,
) -> None:
    """1. Auto-generation: Create without slug triggers SLG_01."""
    crud = CRUDEngine(persistence=persistence, slug_service=slug_service)
    payload = {"name": "Дуб Крупномер"}

    result = await crud.create(schema=DummyPlantSchema, payload=payload)

    assert result["slug"] == "dub-krupnomer"
    assert persistence.exists("slug", "dub-krupnomer")


@pytest.mark.asyncio
async def test_crud_create_respects_custom_slug(
    persistence: InMemoryPersistenceProvider,
    slug_service: SlugGenerator,
) -> None:
    """2. Custom slug: User provided slug is saved as-is if free."""
    crud = CRUDEngine(persistence=persistence, slug_service=slug_service)
    payload = {"name": "Дуб", "slug": "my-custom-oak"}

    result = await crud.create(schema=DummyPlantSchema, payload=payload)

    assert result["slug"] == "my-custom-oak"


@pytest.mark.asyncio
async def test_crud_create_resolves_collision_via_persistence(
    persistence: InMemoryPersistenceProvider,
    slug_service: SlugGenerator,
) -> None:
    """3. Auto-collision: Existing slug triggers generate_unique iteration."""
    persistence.save({"id": 1, "name": "Старый Дуб", "slug": "dub-krupnomer"})

    crud = CRUDEngine(persistence=persistence, slug_service=slug_service)
    payload = {"name": "Дуб Крупномер"}

    result = await crud.create(schema=DummyPlantSchema, payload=payload)

    assert result["slug"] == "dub-krupnomer-2"


@pytest.mark.asyncio
async def test_crud_create_custom_slug_collision_raises_error(
    persistence: InMemoryPersistenceProvider,
    slug_service: SlugGenerator,
) -> None:
    """4. Custom slug collision: Occupied custom slug MUST fail, NOT auto-increment."""
    persistence.save({"id": 1, "name": "Старый Дуб", "slug": "my-custom-oak"})

    crud = CRUDEngine(persistence=persistence, slug_service=slug_service)
    payload = {"name": "Дуб", "slug": "my-custom-oak"}

    with pytest.raises((SlugCollisionError, ValueError)):
        await crud.create(schema=DummyPlantSchema, payload=payload)


@pytest.mark.asyncio
async def test_crud_update_preserves_existing_slug(
    persistence: InMemoryPersistenceProvider,
    slug_service: SlugGenerator,
) -> None:
    """5. Update without slug/overwrite: Preserves current slug even if name changes."""
    persistence.save({"id": 1, "name": "Дуб Крупномер", "slug": "dub-krupnomer"})

    crud = CRUDEngine(persistence=persistence, slug_service=slug_service)
    update_payload = {"name": "Дуб Столетний"}

    result = await crud.update(
        schema=DummyPlantSchema, entity_id=1, payload=update_payload
    )

    assert result["slug"] == "dub-krupnomer"


@pytest.mark.asyncio
async def test_crud_update_allows_same_slug_for_same_entity_id(
    persistence: InMemoryPersistenceProvider,
    slug_service: SlugGenerator,
) -> None:
    """6. Self-exclusion on update: Same entity updating with its own slug passes."""
    persistence.save({"id": 5, "name": "Дуб", "slug": "dub-krupnomer"})

    crud = CRUDEngine(persistence=persistence, slug_service=slug_service)
    update_payload = {"name": "Дуб", "slug": "dub-krupnomer"}

    result = await crud.update(
        schema=DummyPlantSchema, entity_id=5, payload=update_payload
    )

    assert result["slug"] == "dub-krupnomer"


@pytest.mark.asyncio
async def test_crud_raises_error_if_slug_service_missing_but_required(
    persistence: InMemoryPersistenceProvider,
) -> None:
    """7. Missing Service Guard: Schema requires slug, but CRUDEngine has no slug_service."""
    crud = CRUDEngine(persistence=persistence, slug_service=None)
    payload = {"name": "Дуб Крупномер"}

    with pytest.raises(RuntimeError):
        await crud.create(schema=DummyPlantSchema, payload=payload)
