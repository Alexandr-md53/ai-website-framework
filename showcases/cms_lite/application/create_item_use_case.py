from dataclasses import dataclass
import uuid
from showcases.cms_lite.services.cms_service import CmsLiteService
@dataclass
class CreateItemDTO: title: str; slug: str; content: str; category_id: str
@dataclass
class ItemResponse: id: str; title: str; slug: str; status: str
class CreateItemUseCase:
    def __init__(self, service: CmsLiteService): self._service=service
    def execute(self, dto: CreateItemDTO):
        item=self._service.create_item(dto.title, dto.slug, dto.content, uuid.UUID(dto.category_id))
        return ItemResponse(str(item.id), item.title, item.slug, item.status.value)
