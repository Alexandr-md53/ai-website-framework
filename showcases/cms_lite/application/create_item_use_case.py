from dataclasses import dataclass
import uuid
from typing import List, Optional
from showcases.cms_lite.services.cms_service import CmsLiteService
from showcases.cms_lite.domain.user import UserContext, UserRole

@dataclass
class CreateItemDTO:
    title: str
    slug: str
    content: str
    category_id: str
    tag_ids: Optional[List[str]] = None
    user_id: str = "00000000-0000-0000-0000-000000000000"
    user_role: str = "EDITOR"

@dataclass
class ItemResponse:
    id: str
    title: str
    slug: str
    status: str

class CreateItemUseCase:
    def __init__(self, service: CmsLiteService):
        self._service = service
    def execute(self, dto: CreateItemDTO):
        try:
            user = UserContext(user_id=dto.user_id, role=UserRole(dto.user_role))
            cat_id = uuid.UUID(dto.category_id)
            tag_uuids = [uuid.UUID(t) for t in (dto.tag_ids or [])]
            item = self._service.create_item(user=user, title=dto.title, slug=dto.slug, content=dto.content, category_id=cat_id, tag_ids=tag_uuids)
            return ItemResponse(str(item.id), item.title, item.slug, item.status.value)
        except Exception as e:
            msg = str(e)
            status = 403 if "Forbidden" in msg or "Unauthorized" in msg else (404 if "not found" in msg.lower() else 400)
            code = "PERMISSION_DENIED" if status==403 else ("NOT_FOUND" if status==404 else "VALIDATION_ERROR")
            return {"status": status, "json": {"success": False, "error": msg, "code": code}, "success": False}
