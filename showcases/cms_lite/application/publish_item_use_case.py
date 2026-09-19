from dataclasses import dataclass
import uuid
from showcases.cms_lite.services.cms_service import CmsLiteService
from showcases.cms_lite.domain.user import UserContext, UserRole

@dataclass
class PublishItemDTO:
    item_id: str
    user_id: str = "00000000-0000-0000-0000-000000000000"
    user_role: str = "EDITOR"

@dataclass
class ItemResponse:
    id: str
    title: str
    slug: str
    status: str

class PublishItemUseCase:
    def __init__(self, service: CmsLiteService):
        self._service = service
    def execute(self, dto: PublishItemDTO):
        try:
            user = UserContext(user_id=dto.user_id, role=UserRole(dto.user_role))
            item = self._service.publish_item(user=user, item_id=uuid.UUID(dto.item_id))
            return ItemResponse(str(item.id), item.title, item.slug, item.status.value)
        except Exception as e:
            msg = str(e)
            status = 403 if "Forbidden" in msg else 400
            return {"status": status, "json": {"success": False, "error": msg}, "success": False}
