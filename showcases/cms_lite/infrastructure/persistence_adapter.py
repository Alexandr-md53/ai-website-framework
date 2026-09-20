from typing import Any, Dict, List, Optional
import uuid


class FrameworkInMemoryPersistenceProvider:
    def __init__(self):
        self._store: Dict[str, Dict[Any, Dict[str, Any]]] = {}

    def _ensure_entity(self, entity_name: str):
        if entity_name not in self._store:
            self._store[entity_name] = {}

    async def insert(self, entity_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_entity(entity_name)
        rec = dict(payload)
        if "id" not in rec or not rec["id"]:
            rec["id"] = str(uuid.uuid4())
        self._store[entity_name][rec["id"]] = rec
        return rec

    async def fetch(self, entity_name: str, entity_id: Any) -> Optional[Dict[str, Any]]:
        self._ensure_entity(entity_name)
        return self._store[entity_name].get(str(entity_id))

    async def fetch_all(
        self, entity_name: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        self._ensure_entity(entity_name)
        records = list(self._store[entity_name].values())
        if not filters:
            return records
        return [r for r in records if all(r.get(k) == v for k, v in filters.items())]

    async def update_record(
        self, entity_name: str, entity_id: Any, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        self._ensure_entity(entity_name)
        eid = str(entity_id)
        if eid not in self._store[entity_name]:
            return None
        self._store[entity_name][eid].update(payload)
        return self._store[entity_name][eid]

    async def delete_record(self, entity_name: str, entity_id: Any) -> bool:
        self._ensure_entity(entity_name)
        eid = str(entity_id)
        if eid in self._store[entity_name]:
            del self._store[entity_name][eid]
            return True
        return False

    async def is_unique(
        self,
        entity_name: str,
        field_name: str,
        value: Any,
        exclude_id: Optional[Any] = None,
    ) -> bool:
        self._ensure_entity(entity_name)
        for eid, rec in self._store[entity_name].items():
            if exclude_id and str(eid) == str(exclude_id):
                continue
            if rec.get(field_name) == value:
                return False
        return True

    async def check_unique(self, entity_name: str, field_name: str, value: Any) -> bool:
        return await self.is_unique(entity_name, field_name, value)

    async def exists(self, field: str, value: Any, exclude_id: Any = None) -> bool:
        for ent, records in self._store.items():
            for eid, rec in records.items():
                if exclude_id and str(eid) == str(exclude_id):
                    continue
                if rec.get(field) == value:
                    return True
        return False
