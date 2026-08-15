from typing import Any, Dict, List, Optional

from ai_framework.crud.contracts import PersistenceProviderProtocol


class InMemoryPersistenceProvider(PersistenceProviderProtocol):
    """Асинхронный провайдер персистентности в памяти (In-Memory).

    Используется для быстрого прототипирования, тестирования и работы без внешних БД.
    """

    def __init__(self) -> None:
        # Хранилище вида: {"entity_name": {id: record_dict}}
        self._storage: Dict[str, Dict[Any, Dict[str, Any]]] = {}
        self._counters: Dict[str, int] = {}

    def _get_table(self, entity_name: str) -> Dict[Any, Dict[str, Any]]:
        if entity_name not in self._storage:
            self._storage[entity_name] = {}
        return self._storage[entity_name]

    def _generate_id(self, entity_name: str) -> int:
        current_id = self._counters.get(entity_name, 0) + 1
        self._counters[entity_name] = current_id
        return current_id

    async def insert(self, entity_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        table = self._get_table(entity_name)
        record = dict(payload)

        if "id" not in record or record["id"] is None:
            record["id"] = self._generate_id(entity_name)

        table[record["id"]] = record
        return record

    async def fetch(self, entity_name: str, entity_id: Any) -> Optional[Dict[str, Any]]:
        table = self._get_table(entity_name)
        return table.get(entity_id)

    async def fetch_all(
        self, entity_name: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        table = self._get_table(entity_name)
        records = list(table.values())

        if not filters:
            return records

        filtered_records = []
        for record in records:
            match = True
            for key, val in filters.items():
                if record.get(key) != val:
                    match = False
                    break
            if match:
                filtered_records.append(record)

        return filtered_records

    async def update_record(
        self, entity_name: str, entity_id: Any, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        table = self._get_table(entity_name)
        if entity_id not in table:
            return None

        record = table[entity_id]
        record.update(payload)
        return record

    async def delete_record(self, entity_name: str, entity_id: Any) -> bool:
        table = self._get_table(entity_name)
        if entity_id in table:
            del table[entity_id]
            return True
        return False

    async def is_unique(
        self, entity_name: str, field_name: str, value: Any, exclude_id: Any = None
    ) -> bool:
        table = self._get_table(entity_name)
        for rec_id, record in table.items():
            if exclude_id is not None and rec_id == exclude_id:
                continue
            if record.get(field_name) == value:
                return False
        return True
