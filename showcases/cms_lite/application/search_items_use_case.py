from dataclasses import dataclass
from typing import List
from showcases.cms_lite.services.cms_service import CmsLiteService
@dataclass
class SearchItemsDTO: query: str; only_published: bool=False
@dataclass
class ItemResponse: id: str; title: str; slug: str; status: str
class SearchItemsUseCase:
    def __init__(self, service: CmsLiteService): self._service=service
    def execute(self, dto: SearchItemsDTO) -> List[ItemResponse]:
        items=self._service.search_items(dto.query, dto.only_published)
        return [ItemResponse(str(i.id), i.title, i.slug, i.status.value) for i in items]
