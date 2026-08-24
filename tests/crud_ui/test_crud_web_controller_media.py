from unittest.mock import MagicMock

from ai_framework.asset_manager.contracts import FileUploadInput
from ai_framework.crud_ui.web import CrudWebController


def test_create_post_uploads_file_field_through_media_bridge():
    mock_crud_service = MagicMock()
    mock_crud_engine = MagicMock()
    mock_crud_engine.get_file_fields.return_value = ("image",)
    mock_crud_engine.crud_service = mock_crud_service

    mock_media_bridge = MagicMock()
    mock_media_bridge.handle_upload.return_value = "asset-xyz-777"

    controller = CrudWebController(
        engine=mock_crud_engine,
        media_bridge=mock_media_bridge,
    )

    file_input = FileUploadInput(
        filename="photo.jpg",
        content=b"jpeg_bytes",
        mime_type="image/jpeg",
    )

    form_data = {"title": "Test Title"}
    files = {"image": file_input}

    controller.handle_create_post(form_data=form_data, files=files)

    mock_media_bridge.handle_upload.assert_called_once_with(file_input)
    mock_crud_service.create.assert_called_once()

    created_payload = mock_crud_service.create.call_args[0][0]
    assert created_payload["image"] == "asset-xyz-777"
    assert created_payload["title"] == "Test Title"


def test_edit_post_uploads_new_file_and_updates_payload():
    mock_crud_service = MagicMock()
    mock_crud_engine = MagicMock()
    mock_crud_engine.crud_service = mock_crud_service

    mock_media_bridge = MagicMock()
    mock_media_bridge.handle_upload.return_value = "asset-new-999"

    controller = CrudWebController(
        engine=mock_crud_engine,
        media_bridge=mock_media_bridge,
    )

    file_input = FileUploadInput(
        filename="new_avatar.png",
        content=b"new_bytes",
        mime_type="image/png",
    )

    form_data = {"title": "Updated Title"}
    files = {"image": file_input}

    controller.handle_edit_post(entity_id="123", form_data=form_data, files=files)

    mock_media_bridge.handle_upload.assert_called_once_with(file_input)
    mock_crud_service.update.assert_called_once_with(
        "123", {"title": "Updated Title", "image": "asset-new-999"}
    )


def test_edit_post_preserves_existing_file_when_no_file_uploaded():
    mock_crud_service = MagicMock()
    mock_crud_service.get.return_value = {
        "id": "123",
        "title": "Old",
        "image": "asset-old-111",
    }

    mock_crud_engine = MagicMock()
    mock_crud_engine.crud_service = mock_crud_service

    mock_media_bridge = MagicMock()

    controller = CrudWebController(
        engine=mock_crud_engine,
        media_bridge=mock_media_bridge,
    )

    form_data = {"title": "Updated Title"}

    controller.handle_edit_post(entity_id="123", form_data=form_data, files=None)

    mock_media_bridge.handle_upload.assert_not_called()
    mock_crud_service.update.assert_called_once_with(
        "123", {"title": "Updated Title", "image": "asset-old-111"}
    )


def test_edit_post_with_new_file_upload():
    """RED #6a: При передаче файла в handle_edit_post медиа сохраняется через Media Bridge."""
    engine = MagicMock()
    media_bridge = MagicMock()

    # Существующие данные объекта
    engine.crud_service.get.return_value = {
        "id": "42",
        "title": "Old Title",
        "image": "old_asset_000",
    }
    media_bridge.handle_upload.return_value = "new_asset_999"
    engine.crud_service.update.return_value = {
        "id": "42",
        "title": "Updated Title",
        "image": "new_asset_999",
    }

    controller = CrudWebController(engine=engine, media_bridge=media_bridge)

    result = controller.handle_edit_post(
        "42",
        form_data={"title": "Updated Title"},
        files={"image": "fake_new_file_stream"},
    )

    # 1. Загрузка файла в медиа-хранилище
    media_bridge.handle_upload.assert_called_once_with("fake_new_file_stream")

    # 2. Обновление записи в CRUD-сервисе с новым asset_id
    engine.crud_service.update.assert_called_once_with(
        "42",
        {
            "title": "Updated Title",
            "image": "new_asset_999",
        },
    )

    assert result["image"] == "new_asset_999"


def test_edit_post_without_file_preserves_existing_asset():
    """RED #6b: Если файл не передавался, старый asset_id сохраняется, handle_upload не вызывается."""
    engine = MagicMock()
    media_bridge = MagicMock()

    engine.crud_service.get.return_value = {
        "id": "42",
        "title": "Old Title",
        "image": "existing_asset_123",
    }
    engine.crud_service.update.return_value = {
        "id": "42",
        "title": "New Title Only",
        "image": "existing_asset_123",
    }

    controller = CrudWebController(engine=engine, media_bridge=media_bridge)

    result = controller.handle_edit_post(
        "42",
        form_data={"title": "New Title Only"},
        files=None,
    )

    # handle_upload не должен вызываться
    media_bridge.handle_upload.assert_not_called()

    # В update уходит старый image
    engine.crud_service.update.assert_called_once_with(
        "42",
        {
            "title": "New Title Only",
            "image": "existing_asset_123",
        },
    )

    assert result["image"] == "existing_asset_123"
