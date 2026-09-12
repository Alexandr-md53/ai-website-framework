# coding: utf-8, ASCII only
from decimal import Decimal
from dataclasses import dataclass
import uuid
from showcases.cafe.services.cafe_service import CafeService, UserContext, UserRole, PermissionDeniedError

@dataclass
class UpdatePriceDTO:
    item_id: str
    new_price: str
    user_id: str
    user_role: str

@dataclass
class MenuItemResponse:
    id: str
    name: str
    base_price: str
    status: str

class UpdatePriceUseCase:
    def __init__(self, service: CafeService):
        self._service = service
    def execute(self, dto: UpdatePriceDTO):
        try:
            user = UserContext(user_id=dto.user_id, role=UserRole(dto.user_role))
            item = self._service.update_item_price(user=user, item_id=uuid.UUID(dto.item_id), new_price=Decimal(dto.new_price))
            return MenuItemResponse(id=str(item.id), name=item.name, base_price=str(item.base_price), status=item.status.value)
        except PermissionDeniedError as e:
            # Return dict that ResponseAdapter maps to 403, not 500
            return {"status": 403, "json": {"success": False, "error": str(e), "code": "PERMISSION_DENIED", "errors": [{"code": "PERMISSION_DENIED", "message": str(e)}]}, "success": False}
