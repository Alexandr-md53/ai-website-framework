from typing import Any
from ai_framework.settings.manager import SettingsManager


class SettingsUIBridge:
    """Адаптер для связывания SettingsManager с UI-формами."""

    def __init__(self, manager: SettingsManager) -> None:
        self.manager = manager

    def _infer_widget_type(self, value: Any) -> str:
        if isinstance(value, bool):
            return "checkbox"
        if isinstance(value, (int, float)):
            return "number"
        return "text"

    def get_form_model(self) -> dict[str, Any]:
        settings_map = self.manager.list()
        fields = []
        for key, val in settings_map.items():
            widget_type = self._infer_widget_type(val)
            fields.append(
                {
                    "name": key,
                    "widget_type": widget_type,
                    "value": val,
                }
            )
        return {"fields": fields}

    def _cast_value(self, key: str, raw_value: Any) -> Any:
        current_val = self.manager.get(key)
        target_val = (
            current_val if current_val is not None else self.manager.defaults.get(key)
        )

        if isinstance(target_val, bool):
            if isinstance(raw_value, str):
                return raw_value.lower() in ("true", "1", "yes", "on")
            return bool(raw_value)

        if isinstance(target_val, int) and not isinstance(target_val, bool):
            try:
                return int(raw_value)
            except (ValueError, TypeError):
                return raw_value

        if isinstance(target_val, float):
            try:
                return float(raw_value)
            except (ValueError, TypeError):
                return raw_value

        return raw_value

    def handle_submit(self, form_data: dict[str, Any]) -> dict[str, Any]:
        for key, raw_val in form_data.items():
            cast_val = self._cast_value(key, raw_val)
            self.manager.set(key, cast_val)
        return {"success": True}
