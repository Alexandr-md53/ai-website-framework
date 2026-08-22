import concurrent.futures
import pytest

from ai_framework.metadata.exceptions import (
    DuplicateMetadataError,
    MetadataNotFoundError,
)
from ai_framework.metadata.models import EntityMetadata, FormMetadata
from ai_framework.metadata.registry import MetadataRegistry


def test_registry_register_and_get():
    registry = MetadataRegistry()
    entity = EntityMetadata(
        entity_name="user", label="User", plural_label="Users", primary_key_field="id"
    )
    form = FormMetadata(entity_name="user", title="Edit User")

    registry.register_entity(entity)
    registry.register_form(form)

    assert registry.has_entity("user") is True
    assert registry.get_entity("user") == entity
    assert registry.get_form("user") == form


def test_registry_duplicate_registration_raises_error():
    registry = MetadataRegistry()
    entity = EntityMetadata(
        entity_name="user", label="User", plural_label="Users", primary_key_field="id"
    )

    registry.register_entity(entity)

    with pytest.raises(DuplicateMetadataError):
        registry.register_entity(entity)


def test_registry_get_missing_entity_raises_not_found():
    registry = MetadataRegistry()

    with pytest.raises(MetadataNotFoundError):
        registry.get_entity("non_existent")

    with pytest.raises(MetadataNotFoundError):
        registry.get_form("non_existent")


def test_registry_concurrent_registration():
    registry = MetadataRegistry()

    def register_worker(index: int):
        entity = EntityMetadata(
            entity_name=f"entity_{index}",
            label=f"Entity {index}",
            plural_label=f"Entities {index}",
            primary_key_field="id",
        )
        registry.register_entity(entity)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(register_worker, i) for i in range(50)]
        concurrent.futures.wait(futures)

    assert len(registry.list_entity_names()) == 50
