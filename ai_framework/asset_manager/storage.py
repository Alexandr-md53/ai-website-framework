import os
from pathlib import Path
from typing import BinaryIO

from ai_framework.asset_manager.contracts import AssetStorageProtocol


class LocalFileStorage(AssetStorageProtocol):
    """Реализация локального дискового хранилища файлов."""

    def __init__(self, base_path: str | Path = "./uploads"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _full_path(self, storage_key: str) -> Path:
        return self.base_path / storage_key

    def save(self, storage_key: str, data: bytes | BinaryIO) -> str:
        target_path = self._full_path(storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(data, bytes):
            target_path.write_bytes(data)
        else:
            with open(target_path, "wb") as f:
                f.write(data.read())

        return storage_key

    def read(self, storage_key: str) -> bytes:
        target_path = self._full_path(storage_key)
        if not target_path.exists():
            raise FileNotFoundError(f"File not found in storage: {storage_key}")
        return target_path.read_bytes()

    def delete(self, storage_key: str) -> bool:
        target_path = self._full_path(storage_key)
        if target_path.exists():
            target_path.unlink()
            return True
        return False

    def exists(self, storage_key: str) -> bool:
        return self._full_path(storage_key).exists()
