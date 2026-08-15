from typing import Any, Optional, Set, Tuple


class InMemoryPersistenceProvider:
    """Простой провайдер в памяти для проверки уникальности полей (например, занятых email или sku)."""

    def __init__(self, existing_records: Optional[Set[Tuple[str, str, Any]]] = None):
        # Храним кортежи (entity_name, field_name, value)
        self._records = existing_records or set()

    def add_record(self, entity_name: str, field_name: str, value: Any) -> None:
        self._records.add((entity_name, field_name, value))

    async def is_unique(
        self,
        entity_name: str,
        field_name: str,
        value: Any,
        exclude_id: Optional[Any] = None,
    ) -> bool:
        """Возвращает True, если значение свободно (уникально)."""
        return (entity_name, field_name, value) not in self._records
