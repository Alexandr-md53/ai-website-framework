import pytest

from showcases.cafe.domain.menu_item import MenuItemStatus
from showcases.cafe.metadata.cafe_metadata import get_menu_item_ui_schema
from ai_framework.metadata.models import FieldWidgetType


class TestCafeMetadataIntegration:
    def test_menu_item_widget_mappings(self):
        """Проверка маппинга полей MenuItem на канонические виджеты Admin UI Phase 7."""
        schema = get_menu_item_ui_schema()

        assert schema["name"]["widget"] == FieldWidgetType.TEXT
        assert schema["base_price"]["widget"] == FieldWidgetType.NUMBER
        assert schema["status"]["widget"] == FieldWidgetType.SELECT

    def test_menu_item_price_constraints(self):
        """Проверка числового ограничения минимальной цены."""
        schema = get_menu_item_ui_schema()

        assert schema["base_price"]["min"] == 0.01

    def test_status_select_options(self):
        """Проверка передачи значений Enum статуса в опции выбора."""
        schema = get_menu_item_ui_schema()

        options = schema["status"]["options"]
        assert MenuItemStatus.DRAFT.value in options
        assert MenuItemStatus.ACTIVE.value in options
        assert MenuItemStatus.ARCHIVED.value in options
