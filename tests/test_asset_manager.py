import io
import pytest
from datetime import datetime

from ai_framework.asset_manager.contracts import (
    Asset,
    FileUploadInput,
    AssetValidationConfig,
    AssetStorageProtocol,
    AssetManagerProtocol,
)
from ai_framework.crud.contracts import CRUDResult

# Импорт будущей реализации AssetManager
try:
    from ai_framework.asset_manager.manager import AssetManager
except ImportError:
    AssetManager = None


class MockAssetStorage(AssetStorageProtocol):
    """Синхронный мок-провайдер хранилища для unit-тестов."""

    def __init__(self):
        self.saved_files: dict[str, bytes] = {}

    def save(self, storage_key: str, data: bytes | io.BytesIO) -> str:
        if isinstance(data, (io.BufferedIOBase, io.BytesIO)):
            content = data.read()
        else:
            content = data
        self.saved_files[storage_key] = content
        return storage_key

    def read(self, storage_key: str) -> bytes:
        if storage_key not in self.saved_files:
            raise FileNotFoundError(f"Key not found: {storage_key}")
        return self.saved_files[storage_key]

    def delete(self, storage_key: str) -> bool:
        if storage_key in self.saved_files:
            del self.saved_files[storage_key]
            return True
        return False

    def exists(self, storage_key: str) -> bool:
        return storage_key in self.saved_files


# --- Fixtures ---


@pytest.fixture
def mock_storage():
    return MockAssetStorage()


@pytest.fixture
def asset_manager(mock_storage):
    if AssetManager is None:
        pytest.fail("AssetManager еще не реализован (TDD RED State)")
    return AssetManager(storage=mock_storage)


# --- Tests ---


def test_asset_dataclass_structure():
    asset = Asset(
        id="ast_123",
        filename="test.png",
        storage_key="2026/08/uuid.png",
        mime_type="image/png",
        size=1024,
        metadata={"width": 100},
    )
    assert asset.id == "ast_123"
    assert asset.filename == "test.png"
    assert isinstance(asset.created_at, datetime)


def test_file_upload_input_variants():
    file_bytes = FileUploadInput(filename="file.txt", content=b"hello")
    assert file_bytes.content == b"hello"

    stream = io.BytesIO(b"hello stream")
    file_stream = FileUploadInput(filename="file.txt", content=stream)
    assert file_stream.content == stream


def test_upload_success(asset_manager, mock_storage):
    file_input = FileUploadInput(
        filename="photo.jpg", content=b"fake_image_data", mime_type="image/jpeg"
    )
    result = asset_manager.upload(file_input)

    # Было: assert result.is_success
    assert result.success
    asset = result.data
    assert isinstance(asset, Asset)
    assert asset.filename == "photo.jpg"
    assert asset.size == len(b"fake_image_data")
    assert "2026/" in asset.storage_key
    assert len(mock_storage.saved_files) == 1


def test_upload_validation_max_size_exceeded(asset_manager):
    file_input = FileUploadInput(filename="large.bin", content=b"1234567890")
    config = AssetValidationConfig(max_size_bytes=5)

    result = asset_manager.upload(file_input, config=config)
    # Было: assert not result.is_success
    assert not result.success
    assert result.errors[0].code == "VALIDATION_ERROR"


def test_upload_validation_invalid_mime_type(asset_manager):
    file_input = FileUploadInput(
        filename="script.sh", content=b"echo hi", mime_type="text/x-shellscript"
    )
    config = AssetValidationConfig(allowed_mime_types={"image/png", "image/jpeg"})

    result = asset_manager.upload(file_input, config=config)
    # Было: assert not result.is_success
    assert not result.success
    # Было: assert result.error.code == "VALIDATION_ERROR"
    assert result.errors[0].code == "VALIDATION_ERROR"


def test_get_metadata_not_found(asset_manager):
    result = asset_manager.get_metadata("non_existent_id")
    # Было: assert not result.is_success
    assert not result.success
    # Было: assert result.error.code == "NOT_FOUND"
    assert result.errors[0].code == "NOT_FOUND"


def test_download_asset_success(asset_manager):
    file_input = FileUploadInput(filename="doc.txt", content=b"sample content")
    upload_res = asset_manager.upload(file_input)
    asset_id = upload_res.data.id

    download_res = asset_manager.download(asset_id)
    # Было: assert download_res.is_success
    assert download_res.success
    assert download_res.data == b"sample content"


def test_delete_asset_cascade(asset_manager, mock_storage):
    file_input = FileUploadInput(filename="temp.txt", content=b"data")
    upload_res = asset_manager.upload(file_input)
    asset_id = upload_res.data.id

    del_res = asset_manager.delete(asset_id)
    # Было: assert del_res.is_success
    assert del_res.success
    assert len(mock_storage.saved_files) == 0

    # Было: assert not asset_manager.get_metadata(asset_id).is_success
    assert not asset_manager.get_metadata(asset_id).success
    assert not asset_manager.download(asset_id).success
