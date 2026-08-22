import threading
from ai_framework.metadata.exceptions import (
    DuplicateMetadataError,
    MetadataNotFoundError,
)
from ai_framework.metadata.models import EntityMetadata, FormMetadata


class MetadataRegistry:
    """Thread-safe, append-only registry for immutable Entity and Form metadata."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entities: dict[str, EntityMetadata] = {}
        self._forms: dict[str, FormMetadata] = {}

    def register_entity(self, entity: EntityMetadata) -> None:
        with self._lock:
            if entity.entity_name in self._entities:
                raise DuplicateMetadataError(
                    f"Entity metadata for '{entity.entity_name}' is already registered."
                )
            self._entities[entity.entity_name] = entity

    def register_form(self, form: FormMetadata) -> None:
        with self._lock:
            if form.entity_name in self._forms:
                raise DuplicateMetadataError(
                    f"Form metadata for entity '{form.entity_name}' is already registered."
                )
            self._forms[form.entity_name] = form

    def get_entity(self, entity_name: str) -> EntityMetadata:
        with self._lock:
            if entity_name not in self._entities:
                raise MetadataNotFoundError(
                    f"Entity metadata for '{entity_name}' not found."
                )
            return self._entities[entity_name]

    def get_form(self, entity_name: str) -> FormMetadata:
        with self._lock:
            if entity_name not in self._forms:
                raise MetadataNotFoundError(
                    f"Form metadata for entity '{entity_name}' not found."
                )
            return self._forms[entity_name]

    def has_entity(self, entity_name: str) -> bool:
        with self._lock:
            return entity_name in self._entities

    def list_entity_names(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self._entities.keys())
