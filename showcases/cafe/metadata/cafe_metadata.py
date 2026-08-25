from typing import Any, Dict
from ai_framework.metadata.models import FieldWidgetType
from showcases.cafe.domain.menu_item import MenuItemStatus


def get_menu_item_ui_schema() -> Dict[str, Dict[str, Any]]:
    return {
        "id": {
            "widget": FieldWidgetType.HIDDEN,
        },
        "name": {
            "widget": FieldWidgetType.TEXT,
        },
        "base_price": {
            "widget": FieldWidgetType.NUMBER,
            "min": 0.01,
        },
        "status": {
            "widget": FieldWidgetType.SELECT,
            "options": [e.value for e in MenuItemStatus],
        },
    }
