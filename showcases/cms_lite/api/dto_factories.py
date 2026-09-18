from typing import Dict, Any
from showcases.cms_lite.application.create_item_use_case import CreateItemDTO
from showcases.cms_lite.application.publish_item_use_case import PublishItemDTO
from showcases.cms_lite.application.unpublish_item_use_case import UnpublishItemDTO
from showcases.cms_lite.application.duplicate_item_use_case import DuplicateItemDTO
from showcases.cms_lite.application.search_items_use_case import SearchItemsDTO
def _body(d): return d.get("body",d) if isinstance(d,dict) and isinstance(d.get("body"),dict) else d
def _path(d): return d.get("path_params",{}) if isinstance(d,dict) else {}
def create_item_dto_factory(data: Dict[str, Any]) -> CreateItemDTO:
    b=_body(data); return CreateItemDTO(b["title"], b["slug"], b["content"], b["category_id"])
def publish_item_dto_factory(data: Dict[str, Any]) -> PublishItemDTO:
    m={**_body(data),**_path(data),**data}; return PublishItemDTO(str(m.get("item_id") or m.get("id")))
def unpublish_item_dto_factory(data: Dict[str, Any]) -> UnpublishItemDTO:
    m={**_body(data),**_path(data),**data}; return UnpublishItemDTO(str(m.get("item_id") or m.get("id")))
def duplicate_item_dto_factory(data: Dict[str, Any]) -> DuplicateItemDTO:
    m={**_body(data),**_path(data),**data}; return DuplicateItemDTO(str(m.get("item_id") or m.get("id")))
def search_items_dto_factory(data: Dict[str, Any]) -> SearchItemsDTO:
    qp=data.get("query_params",{}) if isinstance(data,dict) else {}; b=_body(data); q=qp.get("q") or b.get("q") or ""; return SearchItemsDTO(str(q), bool(qp.get("only_published",False)))
