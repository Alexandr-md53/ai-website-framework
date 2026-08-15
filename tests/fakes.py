"""
In-Memory Fakes для изоляции Validation Engine в интеграционных тестах.
"""


class FakeMetadataProvider:
    """Фейковый провайдер метаданных, возвращающий заранее определенные схемы."""

    def __init__(self, schemas: dict | None = None):
        self._schemas = schemas or {}

    def register_schema(self, entity_name: str, schema: dict) -> None:
        self._schemas[entity_name] = schema

    def get_schema(self, entity_name: str) -> dict | None:
        return self._schemas.get(entity_name)


class FakePersistenceProvider:
    """Фейковый провайдер персистентности без обращения к реальной БД."""

    def __init__(self, existing_records: set | None = None):
        # Храним кортежи вида (entity_name, field_name, value)
        self._existing_records = existing_records or set()

    def add_record(self, entity_name: str, field_name: str, value: str) -> None:
        self._existing_records.add((entity_name, field_name, value))

    async def is_unique(
        self,
        entity_name: str,
        field_name: str,
        value: str,
        exclude_id: str | int | None = None,
    ) -> bool:
        """Возвращает True, если значение уникально (его НЕТ в базе)."""
        return (entity_name, field_name, value) not in self._existing_records
