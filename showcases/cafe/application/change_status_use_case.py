# coding: utf-8, ASCII only
from dataclasses import dataclass
import uuid
from showcases.cafe.domain.menu_item import MenuItemStatus
from showcases.cafe.services.cafe_service import CafeService, UserContext, UserRole, PermissionDeniedError

@dataclass
class ChangeStatusDTO:
    item_id: str
    new_status: str
    user_id: str
    user_role: str

@dataclass
class MenuItemResponse:
    id: str
    name: str
    base_price: str
    status: str

class ChangeStatusUseCase:
    def __init__(self, service: CafeService):
        self._service = service

    def execute(self, dto: ChangeStatusDTO):
        try:
            user = UserContext(user_id=dto.user_id, role=UserRole(dto.user_role))
            new_status = MenuItemStatus(dto.new_status)
            item = self._service.change_status(user=user, item_id=uuid.UUID(dto.item_id), new_status=new_status)
            return MenuItemResponse(id=str(item.id), name=item.name, base_price=str(item.base_price), status=item.status.value)
        except PermissionDeniedError as e:
            return {"status": 403, "json": {"success": False, "error": str(e), "code": "PERMISSION_DENIED", "errors": [{"code": "PERMISSION_DENIED", "message": str(e)}]}, "success": False}
        except ValueError as e:
            # from MenuItem.activate() validation
            return {"status": 400, "json": {"success": False, "error": str(e), "code": "VALIDATION_ERROR", "errors": [{"code": "VALIDATION_ERROR", "message": str(e)}]}, "success": False}
        except KeyError as e:
            return {"status": 404, "json": {"success": False, "error": str(e), "code": "NOT_FOUND", "errors": [{"code": "NOT_FOUND", "message": str(e)}]}, "success": False}
