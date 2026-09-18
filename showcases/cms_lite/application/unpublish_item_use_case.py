from dataclasses import dataclass
import uuid
from showcases.cms_lite.services.cms_service import CmsLiteService
@dataclass
class UnpublishItemDTO: item_id: str
@dataclass
class ItemResponse: id: str; title: str; slug: str; status: str
class UnpublishItemUseCase:
    def __init__(self, service: CmsLiteService): self._service=service
    def execute(self, dto: UnpublishItemDTO):
        item=self._service.unpublish_item(uuid.UUID(dto.item_id))
        return ItemResponse(str(item.id), item.title, item.slug, item.status.value)
