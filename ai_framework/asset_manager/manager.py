import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from ai_framework.asset_manager.contracts import (
    Asset,
    AssetManagerProtocol,
    AssetStorageProtocol,
    AssetValidationConfig,
    FileUploadInput,
)
from ai_framework.crud.contracts import CRUDError, CRUDResult


class AssetManager(AssetManagerProtocol):
    """Оркестратор валидации, сохранения бинарных данных и управления метаданными."""

    def __init__(
        self,
        storage: AssetStorageProtocol,
        metadata_store: Optional[dict[str, Asset]] = None,
    ):
        self.storage = storage
        self._metadata_store: dict[str, Asset] = (
            metadata_store if metadata_store is not None else {}
        )

    def _generate_storage_key(self, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        now = datetime.now(timezone.utc)
        unique_id = uuid.uuid4().hex
        return f"{now.year}/{now.month:02d}/{unique_id}{ext}"

    def _validate(
        self, file_input: FileUploadInput, config: AssetValidationConfig, size: int
    ) -> Optional[CRUDError]:
        if config.max_size_bytes is not None and size > config.max_size_bytes:
            return CRUDError(
                code="VALIDATION_ERROR",
                message_key=f"File size {size} bytes exceeds limit of {config.max_size_bytes} bytes",
                field="size",
                params={"size": size, "max_size": config.max_size_bytes},
            )

        if (
            config.allowed_mime_types
            and file_input.mime_type not in config.allowed_mime_types
        ):
            return CRUDError(
                code="VALIDATION_ERROR",
                message_key=f"MIME type '{file_input.mime_type}' is not allowed",
                field="mime_type",
                params={"mime_type": file_input.mime_type},
            )

        if config.allowed_extensions:
            ext = os.path.splitext(file_input.filename)[1].lower()
            if ext not in config.allowed_extensions:
                return CRUDError(
                    code="VALIDATION_ERROR",
                    message_key=f"Extension '{ext}' is not allowed",
                    field="filename",
                    params={"extension": ext},
                )

        return None

    def upload(
        self,
        file_input: FileUploadInput,
        config: Optional[AssetValidationConfig] = None,
    ) -> CRUDResult:
        operation = "upload"

        # 1. Извлечение байтов и размера
        if isinstance(file_input.content, bytes):
            data_bytes = file_input.content
        else:
            data_bytes = file_input.content.read()

        size = len(data_bytes)

        # 2. Валидация
        if config:
            error = self._validate(file_input, config, size)
            if error:
                return CRUDResult(
                    success=False, errors=[error], data=None, operation=operation
                )

        # 3. Генерация ключа и сохранение файла
        asset_id = f"ast_{uuid.uuid4().hex[:12]}"
        storage_key = self._generate_storage_key(file_input.filename)

        try:
            self.storage.save(storage_key, data_bytes)
        except Exception as e:
            err = CRUDError(
                code="STORAGE_ERROR", message_key=str(e), field=None, params={}
            )
            return CRUDResult(
                success=False, errors=[err], data=None, operation=operation
            )

        # 4. Сохранение метаданных
        asset = Asset(
            id=asset_id,
            filename=file_input.filename,
            storage_key=storage_key,
            mime_type=file_input.mime_type or "application/octet-stream",
            size=size,
            metadata=file_input.metadata or {},
        )

        self._metadata_store[asset_id] = asset
        return CRUDResult(success=True, errors=[], data=asset, operation=operation)

    def get_metadata(self, asset_id: str) -> CRUDResult:
        operation = "get_metadata"
        if asset_id not in self._metadata_store:
            err = CRUDError(
                code="NOT_FOUND",
                message_key=f"Asset {asset_id} not found",
                field="asset_id",
                params={"asset_id": asset_id},
            )
            return CRUDResult(
                success=False, errors=[err], data=None, operation=operation
            )

        return CRUDResult(
            success=True,
            errors=[],
            data=self._metadata_store[asset_id],
            operation=operation,
        )

    def download(self, asset_id: str) -> CRUDResult:
        operation = "download"
        meta_res = self.get_metadata(asset_id)
        if not meta_res.success:
            return meta_res

        asset: Asset = meta_res.data
        try:
            data = self.storage.read(asset.storage_key)
            return CRUDResult(success=True, errors=[], data=data, operation=operation)
        except Exception as e:
            err = CRUDError(
                code="STORAGE_ERROR", message_key=str(e), field=None, params={}
            )
            return CRUDResult(
                success=False, errors=[err], data=None, operation=operation
            )

    def delete(self, asset_id: str) -> CRUDResult:
        operation = "delete"
        meta_res = self.get_metadata(asset_id)
        if not meta_res.success:
            return meta_res

        asset: Asset = meta_res.data
        try:
            self.storage.delete(asset.storage_key)
            del self._metadata_store[asset_id]
            return CRUDResult(success=True, errors=[], data=True, operation=operation)
        except Exception as e:
            err = CRUDError(
                code="STORAGE_ERROR", message_key=str(e), field=None, params={}
            )
            return CRUDResult(
                success=False, errors=[err], data=None, operation=operation
            )

    def list_assets(
        self, filters: Optional[dict[str, Any]] = None, limit: int = 50, offset: int = 0
    ) -> CRUDResult:
        operation = "list_assets"
        items = list(self._metadata_store.values())
        return CRUDResult(
            success=True,
            errors=[],
            data=items[offset : offset + limit],
            operation=operation,
        )
