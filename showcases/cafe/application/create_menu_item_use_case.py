# coding: utf-8, ASCII only
from decimal import Decimal
from dataclasses import dataclass
from showcases.cafe.services.cafe_service import CafeService, UserContext, UserRole

@dataclass
class CreateMenuItemDTO:
    name: str
    base_price: str
    user_id: str
    user_role: str

@dataclass
class MenuItemResponse:
    id: str
    name: str
    base_price: str
    status: str

class CreateMenuItemUseCase:
    def __init__(self, service: CafeService):
        self._service = service
    def execute(self, dto: CreateMenuItemDTO):
        user = UserContext(user_id=dto.user_id, role=UserRole(dto.user_role))
        item = self._service.create_menu_item(user=user, name=dto.name, base_price=Decimal(dto.base_price))
        return MenuItemResponse(id=str(item.id), name=item.name, base_price=str(item.base_price), status=item.status.value)
