from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict
import uuid

from showcases.cafe.domain.menu_item import MenuItem, MenuItemStatus


class UserRole(str, Enum):
    BARISTA = "BARISTA"
    MANAGER = "MANAGER"


@dataclass
class UserContext:
    user_id: str
    role: UserRole


class PermissionDeniedError(Exception):
    """Исключение при отсутствии прав доступа для выполнения операции."""

    pass


class CafeService:
    def __init__(self) -> None:
        self._items: Dict[uuid.UUID, MenuItem] = {}

    def create_menu_item(
        self,
        user: UserContext,
        name: str,
        base_price: Decimal,
    ) -> MenuItem:
        item_id = uuid.uuid4()
        item = MenuItem(
            id=item_id,
            name=name,
            base_price=base_price,
            status=MenuItemStatus.DRAFT,
        )
        self._items[item_id] = item
        return item

    def update_item_price(
        self,
        user: UserContext,
        item_id: uuid.UUID,
        new_price: Decimal,
    ) -> MenuItem:
        if user.role != UserRole.MANAGER:
            raise PermissionDeniedError("Only Manager can update price")

        item = self._get_item_or_raise(item_id)
        item.base_price = new_price
        return item

    def change_status(
        self,
        user: UserContext,
        item_id: uuid.UUID,
        new_status: MenuItemStatus,
    ) -> MenuItem:
        item = self._get_item_or_raise(item_id)

        if new_status == MenuItemStatus.ARCHIVED:
            if user.role != UserRole.MANAGER:
                raise PermissionDeniedError("Only Manager can archive items")
            item.status = MenuItemStatus.ARCHIVED
        elif new_status == MenuItemStatus.ACTIVE:
            item.activate()
        else:
            item.status = new_status

        return item

    def _get_item_or_raise(self, item_id: uuid.UUID) -> MenuItem:
        if item_id not in self._items:
            raise KeyError(f"Item with id {item_id} not found")
        return self._items[item_id]
