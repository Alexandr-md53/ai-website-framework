from dataclasses import dataclass, field
import dataclasses
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class CRUDContext:
    """Операционный контекст CRUD-запроса."""

    tenant_id: Optional[str] = None
    locale: Optional[str] = "en"


@dataclass(frozen=True)
class CRUDError:
    """Унифицированная ошибка CRUD-операции."""

    code: str
    message_key: str
    field: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message_key": self.message_key,
            "field": self.field,
            "params": self.params,
        }


@dataclass(frozen=True)
class CRUDResult:
    """Унифицированный результат CRUD-операции."""

    success: bool
    errors: List[Any] = field(default_factory=list)
    data: Optional[Any] = None
    operation: str = "read"  # новое поле, по умолчанию "read"


@runtime_checkable
class PersistenceProviderProtocol(Protocol):
    """Контракт persistence layer для Universal CRUD Engine."""

    async def insert(
        self,
        entity_name: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]: ...

    async def fetch(
        self,
        entity_name: str,
        entity_id: Any,
    ) -> Optional[Dict[str, Any]]: ...

    async def fetch_all(
        self,
        entity_name: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]: ...

    async def update_record(
        self,
        entity_name: str,
        entity_id: Any,
        data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]: ...

    async def delete_record(
        self,
        entity_name: str,
        entity_id: Any,
    ) -> bool: ...

    async def is_unique(
        self,
        entity_name: str,
        field_name: str,
        value: Any,
        exclude_id: Optional[Any] = None,
    ) -> bool: ...


@runtime_checkable
class UniversalCRUDEngineProtocol(Protocol):
    """Публичный контракт Universal CRUD Engine."""

    async def create(
        self,
        entity_name: str,
        payload: Dict[str, Any],
        context: Optional[CRUDContext] = None,
    ) -> CRUDResult: ...

    async def get(
        self,
        entity_name: str,
        entity_id: Any,
        context: Optional[CRUDContext] = None,
    ) -> CRUDResult: ...

    async def list(
        self,
        entity_name: str,
        filters: Optional[Dict[str, Any]] = None,
        context: Optional[CRUDContext] = None,
    ) -> CRUDResult: ...

    async def update(
        self,
        entity_name: str,
        entity_id: Any,
        payload: Dict[str, Any],
        context: Optional[CRUDContext] = None,
    ) -> CRUDResult: ...

    async def delete(
        self,
        entity_name: str,
        entity_id: Any,
        context: Optional[CRUDContext] = None,
    ) -> CRUDResult: ...
