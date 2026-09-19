from dataclasses import dataclass
from typing import List, Optional
import uuid
from showcases.cms_lite.services.cms_service import CmsLiteService

@dataclass
class ListPublishedDTO:
    category_id: Optional[str] = None
    tag_id: Optional[str] = None

@dataclass
class ItemResponse:
    id: str
    title: str
    slug: str
    status: str

class ListPublishedUseCase:
    def __init__(self, service: CmsLiteService):
        self._service = service
    def execute(self, dto: ListPublishedDTO) -> List[ItemResponse]:
        cat_id = uuid.UUID(dto.category_id) if dto.category_id else None
        tag_id = uuid.UUID(dto.tag_id) if dto.tag_id else None
        items = self._service.list_published(category_id=cat_id, tag_id=tag_id)
        return [ItemResponse(str(i.id), i.title, i.slug, i.status.value) for i in items]
