from decimal import Decimal
import uuid
import pytest

from showcases.cafe.domain.menu_item import (
    MenuItem,
    MenuItemStatus,
    Modifier,
    InvalidStatusTransitionError,
)


class TestMenuItemStatusWorkflow:
    def test_create_menu_item_in_draft_status(self):
        """Создание позиции меню по умолчанию в статусе DRAFT."""
        item = MenuItem(
            id=uuid.uuid4(),
            name="Espresso",
            base_price=Decimal("2.50"),
        )
        assert item.status == MenuItemStatus.DRAFT
        assert item.total_price() == Decimal("2.50")

    def test_activate_menu_item_success(self):
        """Успешный перевод валидной позиции из DRAFT в ACTIVE."""
        item = MenuItem(
            id=uuid.uuid4(),
            name="Cappuccino",
            base_price=Decimal("3.80"),
        )
        item.activate()
        assert item.status == MenuItemStatus.ACTIVE

    def test_cannot_activate_item_with_zero_or_negative_price(self):
        """Запрет активации товара с невалидной ценой."""
        item = MenuItem(
            id=uuid.uuid4(),
            name="Free Coffee",
            base_price=Decimal("0.00"),
        )
        with pytest.raises(
            ValueError, match="Cannot activate item with zero or negative price"
        ):
            item.activate()

    def test_cannot_activate_without_name(self):
        """Запрет активации товара без наименования."""
        item = MenuItem(
            id=uuid.uuid4(),
            name="   ",
            base_price=Decimal("3.00"),
        )
        with pytest.raises(ValueError, match="Cannot activate item without valid name"):
            item.activate()

    def test_add_modifiers_and_calculate_total_price(self):
        """Подсчет итоговой стоимости товара с модификаторами (сироп, альтернативное молоко)."""
        syrup = Modifier(
            id=uuid.uuid4(), name="Vanilla Syrup", price_extra=Decimal("0.50")
        )
        oat_milk = Modifier(
            id=uuid.uuid4(), name="Oat Milk", price_extra=Decimal("0.80")
        )

        item = MenuItem(
            id=uuid.uuid4(),
            name="Latte",
            base_price=Decimal("4.00"),
            modifiers=[syrup, oat_milk],
        )

        assert len(item.modifiers) == 2
        # 4.00 + 0.50 + 0.80 = 5.30
        assert item.total_price() == Decimal("5.30")
