from unittest.mock import MagicMock

from ai_framework.asset_manager.contracts import Asset, FileUploadInput
from ai_framework.crud_ui.media_bridge import MediaUIBridge


def test_media_bridge_handles_upload_and_returns_asset_id():
    mock_asset_manager = MagicMock()
    mock_asset_manager.upload.return_value = Asset(
        id="asset-xyz-123",
        filename="avatar.png",
        mime_type="image/png",
        size=512,
        storage_key="uploads/avatar.png",
    )

    bridge = MediaUIBridge(asset_manager=mock_asset_manager)

    file_input = FileUploadInput(
        filename="avatar.png",
        content=b"fake-image-data",
        mime_type="image/png",
    )

    asset_id = bridge.handle_upload(file_input)

    assert asset_id == "asset-xyz-123"
    mock_asset_manager.upload.assert_called_once_with(file_input)


def test_media_bridge_resolves_asset_metadata():
    mock_asset_manager = MagicMock()
    expected_asset = Asset(
        id="asset-xyz-123",
        filename="avatar.png",
        mime_type="image/png",
        size=512,
        storage_key="uploads/avatar.png",
    )
    mock_asset_manager.get_metadata.return_value = expected_asset

    bridge = MediaUIBridge(asset_manager=mock_asset_manager)
    resolved = bridge.resolve_asset("asset-xyz-123")

    assert resolved == expected_asset
    mock_asset_manager.get_metadata.assert_called_once_with("asset-xyz-123")


def test_media_bridge_presents_asset_representation():
    mock_asset_manager = MagicMock()
    asset = Asset(
        id="asset-xyz-123",
        filename="avatar.png",
        mime_type="image/png",
        size=512,
        storage_key="uploads/avatar.png",
    )
    mock_asset_manager.get_metadata.return_value = asset

    bridge = MediaUIBridge(asset_manager=mock_asset_manager)
    presentation = bridge.present_asset("asset-xyz-123")

    assert presentation == {
        "asset_id": "asset-xyz-123",
        "filename": "avatar.png",
        "mime_type": "image/png",
        "size": 512,
        "storage_key": "uploads/avatar.png",
    }


def test_media_bridge_presents_none_for_missing_or_empty_asset():
    mock_asset_manager = MagicMock()
    mock_asset_manager.get_metadata.return_value = None

    bridge = MediaUIBridge(asset_manager=mock_asset_manager)

    assert bridge.present_asset(None) is None
    assert bridge.present_asset("missing-id") is None


def test_media_bridge_enriches_context_with_file_presentation():
    mock_asset_manager = MagicMock()
    mock_asset_manager.get_metadata.return_value = Asset(
        id="asset-xyz-123",
        filename="avatar.png",
        mime_type="image/png",
        size=512,
        storage_key="uploads/avatar.png",
    )

    bridge = MediaUIBridge(asset_manager=mock_asset_manager)
    context = {
        "title": "Profile",
        "avatar_id": "asset-xyz-123",
        "bio": "Developer",
    }

    enriched = bridge.enrich_context(context, file_fields=("avatar_id",))

    assert enriched["avatar_id"] == {
        "asset_id": "asset-xyz-123",
        "filename": "avatar.png",
        "mime_type": "image/png",
        "size": 512,
        "storage_key": "uploads/avatar.png",
    }
    assert enriched["bio"] == "Developer"
