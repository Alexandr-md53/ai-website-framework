from decimal import Decimal
import uuid
import pytest

from showcases.cafe.domain.menu_item import MenuItem, MenuItemStatus
from showcases.cafe.services.cafe_service import (
    CafeService,
    UserRole,
    UserContext,
    PermissionDeniedError,
)


class TestCafeSecurityPermissions:
    def test_manager_can_create_and_update_price(self):
        """Менеджер имеет право изменять базовую стоимость позиции."""
        manager = UserContext(user_id="user-1", role=UserRole.MANAGER)
        service = CafeService()

        item = service.create_menu_item(
            user=manager,
            name="Flat White",
            base_price=Decimal("4.50"),
        )
        assert item.base_price == Decimal("4.50")

        updated_item = service.update_item_price(
            user=manager,
            item_id=item.id,
            new_price=Decimal("4.80"),
        )
        assert updated_item.base_price == Decimal("4.80")

    def test_barista_cannot_update_price(self):
        """Бариста не имеет права менять стоимость товара."""
        manager = UserContext(user_id="user-1", role=UserRole.MANAGER)
        barista = UserContext(user_id="user-2", role=UserRole.BARISTA)
        service = CafeService()

        item = service.create_menu_item(
            user=manager,
            name="Americano",
            base_price=Decimal("3.00"),
        )

        with pytest.raises(
            PermissionDeniedError, match="Only Manager can update price"
        ):
            service.update_item_price(
                user=barista,
                item_id=item.id,
                new_price=Decimal("2.00"),
            )

    def test_barista_can_activate_item(self):
        """Бариста может активировать позицию меню."""
        manager = UserContext(user_id="user-1", role=UserRole.MANAGER)
        barista = UserContext(user_id="user-2", role=UserRole.BARISTA)
        service = CafeService()

        item = service.create_menu_item(
            user=manager,
            name="Cortado",
            base_price=Decimal("3.50"),
        )

        activated_item = service.change_status(
            user=barista,
            item_id=item.id,
            new_status=MenuItemStatus.ACTIVE,
        )
        assert activated_item.status == MenuItemStatus.ACTIVE

    def test_barista_cannot_archive_item(self):
        """Бариста не имеет права архивировать позицию меню."""
        manager = UserContext(user_id="user-1", role=UserRole.MANAGER)
        barista = UserContext(user_id="user-2", role=UserRole.BARISTA)
        service = CafeService()

        item = service.create_menu_item(
            user=manager,
            name="Mocha",
            base_price=Decimal("4.20"),
        )

        with pytest.raises(
            PermissionDeniedError, match="Only Manager can archive items"
        ):
            service.change_status(
                user=barista,
                item_id=item.id,
                new_status=MenuItemStatus.ARCHIVED,
            )
