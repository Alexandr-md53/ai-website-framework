"""
AssetManager

Core Service responsible for handling media uploads, file validation,
filename sanitization, and delegating storage operations.
"""

import os
import uuid
import mimetypes
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

from framework.services.slug import SlugService


@dataclass
class AssetInfo:
    """Информация о сохранённом ассете."""

    filename: str
    path: str
    url: str
    mime_type: str
    size_bytes: int


class StorageProvider(Protocol):
    """Интерфейс для работы с абстрактным хранилищем файлов."""

    async def save(self, file_data: bytes, target_path: str) -> str: ...
    async def delete(self, target_path: str) -> bool: ...
    async def exists(self, target_path: str) -> bool: ...
    def get_url(self, target_path: str) -> str: ...


class AssetManager:
    """Core Service для обработки и загрузки файлов."""

    def __init__(
        self,
        storage: StorageProvider,
        allowed_extensions: Optional[Sequence[str]] = None,
        max_file_size_mb: float = 10.0,
        slug_service: Optional[SlugService] = None,
    ) -> None:
        self.storage = storage
        self.allowed_extensions = set(
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in (
                allowed_extensions or [".jpg", ".jpeg", ".png", ".webp", ".pdf"]
            )
        )
        self.max_file_size_bytes = int(max_file_size_mb * 1024 * 1024)
        self.slug_service = slug_service or SlugService()

    def validate_file(self, filename: str, file_size_bytes: int) -> bool:
        """Проверяет расширение файла и размер."""
        if file_size_bytes > self.max_file_size_bytes:
            return False

        _, ext = os.path.splitext(filename.lower())
        return ext in self.allowed_extensions

    def generate_unique_filename(self, original_filename: str) -> str:
        """Очищает имя файла через SlugService и делает его уникальным через UUID."""
        name, ext = os.path.splitext(original_filename)
        ext = ext.lower()

        # Используем SlugService для честной транслитерации кириллицы
        clean_name = self.slug_service.slugify(name)
        if not clean_name or clean_name == self.slug_service.default_fallback:
            clean_name = "file"

        unique_suffix = uuid.uuid4().hex[:8]
        return f"{clean_name}-{unique_suffix}{ext}"

    async def upload(
        self,
        file_data: bytes,
        original_filename: str,
        folder: str = "general",
    ) -> AssetInfo:
        """Валидирует, генерирует уникальный путь и сохраняет файл в storage."""
        size_bytes = len(file_data)
        if not self.validate_file(original_filename, size_bytes):
            raise ValueError(
                f"File '{original_filename}' failed validation constraints."
            )

        clean_filename = self.generate_unique_filename(original_filename)
        target_path = f"{folder.strip('/')}/{clean_filename}"

        url = await self.storage.save(file_data, target_path)

        mime_type, _ = mimetypes.guess_type(original_filename)
        mime_type = mime_type or "application/octet-stream"

        return AssetInfo(
            filename=clean_filename,
            path=target_path,
            url=url,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )

    async def delete(self, asset_path: str) -> bool:
        """Удаляет файл из хранилища."""
        return await self.storage.delete(asset_path)
