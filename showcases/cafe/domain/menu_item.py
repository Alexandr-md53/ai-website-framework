from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List
import uuid


class MenuItemStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class InvalidStatusTransitionError(Exception):
    """Исключение при некорректной смене статуса позиции меню."""

    pass


@dataclass
class Modifier:
    id: uuid.UUID
    name: str
    price_extra: Decimal = Decimal("0.00")
    is_available: bool = True


@dataclass
class MenuItem:
    id: uuid.UUID
    name: str
    base_price: Decimal
    status: MenuItemStatus = MenuItemStatus.DRAFT
    modifiers: List[Modifier] = field(default_factory=list)

    def activate(self) -> None:
        """Перевод позиции из DRAFT в ACTIVE с валидацией наименования и базовой цены."""
        if not self.name or not self.name.strip():
            raise ValueError("Cannot activate item without valid name")
        if self.base_price <= Decimal("0.00"):
            raise ValueError("Cannot activate item with zero or negative price")

        self.status = MenuItemStatus.ACTIVE

    def total_price(self) -> Decimal:
        """Подсчет итоговой стоимости с учетом стоимости активных модификаторов."""
        modifier_extra = sum((m.price_extra for m in self.modifiers), Decimal("0.00"))
        return self.base_price + modifier_extra
