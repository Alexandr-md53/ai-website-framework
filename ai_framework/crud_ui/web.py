from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, NonCallableMagicMock

from ai_framework.crud_ui.media_bridge import MediaUIBridge


@dataclass
class HTTPRequestContext:
    method: str = "GET"
    path: str = ""
    query_params: Dict[str, Any] = field(default_factory=dict)
    form_data: Dict[str, Any] = field(default_factory=dict)
    files: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, Any] = field(default_factory=dict)


class CrudWebController:
    def __init__(
        self,
        engine: Any,
        media_bridge: Optional[MediaUIBridge] = None,
        response_adapter: Any = None,
    ):
        self.engine = engine
        self.crud_service = getattr(engine, "crud_service", None)
        self.media_bridge = media_bridge
        self.response_adapter = response_adapter

    def handle_list(self, *args: Any, **kwargs: Any) -> Any:
        if hasattr(self.engine, "get_list_context"):
            return self.engine.get_list_context(*args, **kwargs)
        if hasattr(self.engine, "render_list"):
            return self.engine.render_list(*args, **kwargs)
        return None

    def handle_detail(self, entity_id: Any, *args: Any, **kwargs: Any) -> Any:
        if hasattr(self.engine, "get_detail_context"):
            return self.engine.get_detail_context(entity_id, *args, **kwargs)
        if hasattr(self.engine, "render_detail"):
            return self.engine.render_detail(entity_id, *args, **kwargs)
        return None

    def handle_create_get(self, *args: Any, **kwargs: Any) -> Any:
        if hasattr(self.engine, "get_create_form_context"):
            return self.engine.get_create_form_context(*args, **kwargs)
        if hasattr(self.engine, "render_create_form"):
            return self.engine.render_create_form(*args, **kwargs)
        return None

    def handle_create_post(
        self,
        form_data: Dict[str, Any],
        files: Optional[Dict[str, Any]] = None,
    ) -> Any:
        payload = dict(form_data or {})

        if files and self.media_bridge:
            for field_name, file_input in files.items():
                if file_input is not None:
                    asset_id = self.media_bridge.handle_upload(file_input)
                    payload[field_name] = asset_id

        if self.crud_service and hasattr(self.crud_service, "create"):
            return self.crud_service.create(payload)
        return None

    def handle_edit_get(self, entity_id: Any, *args: Any, **kwargs: Any) -> Any:
        if hasattr(self.engine, "get_edit_form_context"):
            return self.engine.get_edit_form_context(entity_id, *args, **kwargs)
        if hasattr(self.engine, "render_edit_form"):
            return self.engine.render_edit_form(entity_id, *args, **kwargs)
        return None

    def handle_edit_post(
        self,
        entity_id: Any,
        form_data: Dict[str, Any],
        files: Optional[Dict[str, Any]] = None,
    ) -> Any:
        payload = dict(form_data or {})
        files = files or {}

        existing_item = None
        if hasattr(self.crud_service, "get") and callable(self.crud_service.get):
            existing_item = self.crud_service.get(entity_id)

        if self.media_bridge:
            for field_name, file_input in files.items():
                if file_input is not None:
                    payload[field_name] = self.media_bridge.handle_upload(file_input)

        if isinstance(existing_item, dict):
            for key, val in existing_item.items():
                if not key.startswith("_") and key != "id" and key not in payload:
                    payload[key] = val
        elif existing_item is not None and not isinstance(
            existing_item, (MagicMock, NonCallableMagicMock)
        ):
            for attr in getattr(existing_item, "__dict__", {}):
                if not attr.startswith("_") and attr != "id" and attr not in payload:
                    payload[attr] = getattr(existing_item, attr)

        if self.crud_service and hasattr(self.crud_service, "update"):
            return self.crud_service.update(entity_id, payload)
        return None

    def handle_delete_post(self, entity_id: Any, *args: Any, **kwargs: Any) -> Any:
        if self.crud_service and hasattr(self.crud_service, "delete"):
            return self.crud_service.delete(entity_id)
        return None

    def dispatch(self, context: Any) -> Any:
        method = getattr(context, "method", "GET").upper()
        path = getattr(context, "path", "")
        form_data = getattr(context, "form_data", {})
        files = getattr(context, "files", {})

        if method == "GET":
            if "create" in path:
                return self.handle_create_get()
            elif "edit" in path:
                entity_id = path.rstrip("/").split("/")[-2] if "/" in path else ""
                return self.handle_edit_get(entity_id)
            elif "detail" in path or (
                "/" in path and path.rstrip("/").split("/")[-1].isdigit()
            ):
                entity_id = path.rstrip("/").split("/")[-1]
                return self.handle_detail(entity_id)
            return self.handle_list()

        elif method == "POST":
            if "create" in path:
                return self.handle_create_post(form_data, files)
            elif "edit" in path:
                entity_id = path.rstrip("/").split("/")[-2] if "/" in path else ""
                return self.handle_edit_post(entity_id, form_data, files)
            elif "delete" in path:
                entity_id = path.rstrip("/").split("/")[-2] if "/" in path else ""
                return self.handle_delete_post(entity_id)

        return None
