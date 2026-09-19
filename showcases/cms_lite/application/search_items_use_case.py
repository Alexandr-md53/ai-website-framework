from dataclasses import dataclass
from typing import List
from showcases.cms_lite.services.cms_service import CmsLiteService
from showcases.cms_lite.domain.user import UserContext, UserRole

@dataclass
class SearchItemsDTO:
    query: str
    only_published: bool = False
    user_id: str = "00000000-0000-0000-0000-000000000000"
    user_role: str = "EDITOR"

@dataclass
class ItemResponse:
    id: str
    title: str
    slug: str
    status: str

class SearchItemsUseCase:
    def __init__(self, service: CmsLiteService):
        self._service = service
    def execute(self, dto: SearchItemsDTO) -> List[ItemResponse]:
        try:
            if dto.only_published:
                items = self._service.search_published(dto.query)
            else:
                user = UserContext(user_id=dto.user_id, role=UserRole(dto.user_role))
                items = self._service.search_items(user=user, query=dto.query, only_published=dto.only_published)
            return [ItemResponse(str(i.id), i.title, i.slug, i.status.value) for i in items]
        except Exception as e:
            return {"status": 403 if "Forbidden" in str(e) else 400, "json": {"success": False, "error": str(e)}, "success": False}
