import uuid
import pytest

from showcases.plant_nursery.domain.plant import (
    Plant,
    LightRequirement,
    WateringRequirement,
)
from showcases.plant_nursery.metadata.plant_metadata import get_plant_ui_schema
from ai_framework.metadata.models import FieldWidgetType


class TestPlantMetadataIntegration:
    def test_plant_domain_entity_instantiation(self):
        """Проверка корректной инициализации сущности Plant со всеми Value Objects и Enums."""
        plant = Plant(
            id=uuid.uuid4(),
            category_id=uuid.uuid4(),
            name="Monstera Deliciosa",
            description="Popular indoor plant",
            light_req=LightRequirement.MEDIUM,
            water_req=WateringRequirement.MODERATE,
            frost_resistance=-5,
            main_image_id="asset-uuid-1234",
        )

        assert plant.name == "Monstera Deliciosa"
        assert plant.light_req == LightRequirement.MEDIUM
        assert plant.water_req == WateringRequirement.MODERATE
        assert plant.frost_resistance == -5

    def test_plant_metadata_schema_widget_mapping(self):
        """Проверка маппинга доменных полей Plant на виджеты Admin UI Phase 7."""
        schema = get_plant_ui_schema()

        # Поля Enum должны мапиться на SELECT
        assert schema["light_req"]["widget"] == FieldWidgetType.SELECT
        assert schema["water_req"]["widget"] == FieldWidgetType.SELECT

        # Числовые границы frost_resistance
        assert schema["frost_resistance"]["widget"] == FieldWidgetType.NUMBER
        assert schema["frost_resistance"]["min"] == -50
        assert schema["frost_resistance"]["max"] == 40

        # Связь с медиа-ресурсами через AssetManager Phase 4 должна использовать FILE
        assert schema["main_image_id"]["widget"] == FieldWidgetType.FILE
