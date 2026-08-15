from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional
import sqlite3


class SQLitePersistenceProvider:
    """Провайдер персистентности для работы с SQLite БД."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Создание базовых таблиц при необходимости."""
        pass

    async def insert(self, entity_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        record = dict(payload)
        fields = list(record.keys())
        placeholders = ", ".join(["?"] * len(fields))
        columns = ", ".join(fields)

        query = f"INSERT INTO {entity_name} ({columns}) VALUES ({placeholders})"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, list(record.values()))
            conn.commit()
            if "id" not in record or not record["id"]:
                record["id"] = cursor.lastrowid

        return record

    async def fetch(self, entity_name: str, entity_id: Any) -> Optional[Dict[str, Any]]:
        query = f"SELECT * FROM {entity_name} WHERE id = ?"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (entity_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    async def fetch_all(
        self, entity_name: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        query = f"SELECT * FROM {entity_name}"
        params: List[Any] = []

        if filters:
            conditions = [f"{k} = ?" for k in filters.keys()]
            query += " WHERE " + " AND ".join(conditions)
            params = list(filters.values())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_record(
        self, entity_name: str, entity_id: Any, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not payload:
            return await self.fetch(entity_name, entity_id)

        set_clause = ", ".join([f"{k} = ?" for k in payload.keys()])
        query = f"UPDATE {entity_name} SET {set_clause} WHERE id = ?"
        params = list(payload.values()) + [entity_id]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            if cursor.rowcount == 0:
                return None

        return await self.fetch(entity_name, entity_id)

    async def delete_record(self, entity_name: str, entity_id: Any) -> bool:
        query = f"DELETE FROM {entity_name} WHERE id = ?"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (entity_id,))
            conn.commit()
            return cursor.rowcount > 0

    async def is_unique(
        self, entity_name: str, field_name: str, value: Any, exclude_id: Any = None
    ) -> bool:
        query = f"SELECT COUNT(*) as count FROM {entity_name} WHERE {field_name} = ?"
        params = [value]

        if exclude_id is not None:
            query += " AND id != ?"
            params.append(exclude_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row["count"] == 0 if row else True
