from typing import Dict, Any, Optional
from ai_framework.validation.exceptions import EntitySchemaNotFoundError


class InMemoryMetadataProvider:
    """Простой провайдер метаданных для хранения схем в памяти."""

    def __init__(self, schemas: Optional[Dict[str, Dict[str, Any]]] = None):
        self._schemas = schemas or {}

    def register_schema(self, entity_name: str, schema: Dict[str, Any]) -> None:
        self._schemas[entity_name] = schema

    def get_schema(self, entity_name: str) -> Dict[str, Any]:
        if entity_name not in self._schemas:
            raise EntitySchemaNotFoundError(
                f"Schema for entity '{entity_name}' was not found in Metadata Engine."
            )
        return self._schemas[entity_name]
