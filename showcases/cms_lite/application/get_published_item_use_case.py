from dataclasses import dataclass
from showcases.cms_lite.services.cms_service import CmsLiteService

@dataclass
class GetPublishedItemDTO:
    slug: str

@dataclass
class ItemDetailResponse:
    id: str
    title: str
    slug: str
    content: str
    status: str

class GetPublishedItemUseCase:
    def __init__(self, service: CmsLiteService):
        self._service = service
    def execute(self, dto: GetPublishedItemDTO):
        try:
            item = self._service.get_published_by_slug(dto.slug)
            return ItemDetailResponse(str(item.id), item.title, item.slug, item.content, item.status.value)
        except Exception as e:
            status = 404 if "not found" in str(e).lower() or "not published" in str(e).lower() else 400
            return {"status": status, "json": {"success": False, "error": str(e)}, "success": False}
