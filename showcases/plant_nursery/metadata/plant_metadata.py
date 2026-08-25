from typing import Any, Dict
from ai_framework.metadata.models import FieldWidgetType
from showcases.plant_nursery.domain.plant import LightRequirement, WateringRequirement


def get_plant_ui_schema() -> Dict[str, Dict[str, Any]]:
    return {
        "id": {
            "widget": FieldWidgetType.HIDDEN,
        },
        "category_id": {
            "widget": FieldWidgetType.TEXT,
        },
        "name": {
            "widget": FieldWidgetType.TEXT,
        },
        "description": {
            "widget": FieldWidgetType.TEXTAREA,
        },
        "light_req": {
            "widget": FieldWidgetType.SELECT,
            "options": [e.value for e in LightRequirement],
        },
        "water_req": {
            "widget": FieldWidgetType.SELECT,
            "options": [e.value for e in WateringRequirement],
        },
        "frost_resistance": {
            "widget": FieldWidgetType.NUMBER,
            "min": -50,
            "max": 40,
        },
        "main_image_id": {
            "widget": FieldWidgetType.FILE,
        },
    }
