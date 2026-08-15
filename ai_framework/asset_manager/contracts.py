from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, BinaryIO, Optional, Protocol, runtime_checkable

from ai_framework.crud.contracts import CRUDResult


@dataclass(frozen=True)
class Asset:
    """Модель метаданных файла."""

    id: str
    filename: str
    storage_key: str
    mime_type: str
    size: int
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class FileUploadInput:
    """DTO загружаемого файла."""

    filename: str
    content: bytes | BinaryIO
    mime_type: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class AssetValidationConfig:
    """Конфигурация ограничений для файлов."""

    max_size_bytes: Optional[int] = None
    allowed_mime_types: Optional[set[str]] = None
    allowed_extensions: Optional[set[str]] = None


@runtime_checkable
class AssetStorageProtocol(Protocol):
    """Контракт физического хранилища бинарных данных."""

    def save(self, storage_key: str, data: bytes | BinaryIO) -> str: ...

    def read(self, storage_key: str) -> bytes: ...

    def delete(self, storage_key: str) -> bool: ...

    def exists(self, storage_key: str) -> bool: ...


@runtime_checkable
class AssetManagerProtocol(Protocol):
    """Контракт оркестратора ресурсов."""

    def upload(
        self,
        file_input: FileUploadInput,
        config: Optional[AssetValidationConfig] = None,
    ) -> CRUDResult: ...

    def get_metadata(self, asset_id: str) -> CRUDResult: ...

    def download(self, asset_id: str) -> CRUDResult: ...

    def delete(self, asset_id: str) -> CRUDResult: ...

    def list_assets(
        self, filters: Optional[dict[str, Any]] = None, limit: int = 50, offset: int = 0
    ) -> CRUDResult: ...
