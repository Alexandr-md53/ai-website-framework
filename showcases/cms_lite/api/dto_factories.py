from typing import Dict, Any
from showcases.cms_lite.application.create_category_use_case import CreateCategoryDTO
from showcases.cms_lite.application.create_item_use_case import CreateItemDTO
from showcases.cms_lite.application.publish_item_use_case import PublishItemDTO
from showcases.cms_lite.application.unpublish_item_use_case import UnpublishItemDTO
from showcases.cms_lite.application.duplicate_item_use_case import DuplicateItemDTO
from showcases.cms_lite.application.search_items_use_case import SearchItemsDTO
from showcases.cms_lite.application.list_published_use_case import ListPublishedDTO
from showcases.cms_lite.application.get_published_item_use_case import GetPublishedItemDTO

def _body(d): return d.get("body", d) if isinstance(d, dict) and isinstance(d.get("body"), dict) else d
def _path(d): return d.get("path_params", {}) if isinstance(d, dict) else {}
def _query(d): return d.get("query_params", {}) if isinstance(d, dict) else {}
def _headers(d): return d.get("headers", {}) if isinstance(d, dict) else {}

def _extract_user(d: Dict[str, Any]):
    headers = _headers(d)
    # X-User-Role / X-User-Id or body
    body = _body(d)
    role = headers.get("X-User-Role") or headers.get("x-user-role") or body.get("user_role") or "EDITOR"
    uid = headers.get("X-User-Id") or headers.get("x-user-id") or body.get("user_id") or "00000000-0000-0000-0000-000000000000"
    return str(uid), str(role)

def create_category_dto_factory(data: Dict[str, Any]) -> CreateCategoryDTO:
    b = _body(data)
    uid, role = _extract_user(data)
    return CreateCategoryDTO(name=b.get("name",""), slug=b.get("slug",""), description=b.get("description",""), user_id=uid, user_role=role)

def create_item_dto_factory(data: Dict[str, Any]) -> CreateItemDTO:
    b = _body(data)
    uid, role = _extract_user(data)
    return CreateItemDTO(title=b.get("title",""), slug=b.get("slug",""), content=b.get("content",""), category_id=str(b.get("category_id","")), tag_ids=b.get("tag_ids"), user_id=uid, user_role=role)

def publish_item_dto_factory(data: Dict[str, Any]) -> PublishItemDTO:
    m = {**_body(data), **_path(data), **data}
    uid, role = _extract_user(data)
    return PublishItemDTO(item_id=str(m.get("item_id") or m.get("id") or ""), user_id=uid, user_role=role)

def unpublish_item_dto_factory(data: Dict[str, Any]) -> UnpublishItemDTO:
    m = {**_body(data), **_path(data), **data}
    uid, role = _extract_user(data)
    return UnpublishItemDTO(item_id=str(m.get("item_id") or m.get("id") or ""), user_id=uid, user_role=role)

def duplicate_item_dto_factory(data: Dict[str, Any]) -> DuplicateItemDTO:
    m = {**_body(data), **_path(data), **data}
    uid, role = _extract_user(data)
    return DuplicateItemDTO(item_id=str(m.get("item_id") or m.get("id") or ""), user_id=uid, user_role=role)

def search_items_dto_factory(data: Dict[str, Any]) -> SearchItemsDTO:
    qp = _query(data)
    b = _body(data)
    uid, role = _extract_user(data)
    q = qp.get("q") or b.get("q") or ""
    only_pub = qp.get("only_published", False)
    if isinstance(only_pub, str):
        only_pub = only_pub.lower() in ("true","1","yes")
    return SearchItemsDTO(query=str(q), only_published=bool(only_pub), user_id=uid, user_role=role)

def list_published_dto_factory(data: Dict[str, Any]) -> ListPublishedDTO:
    qp = _query(data)
    return ListPublishedDTO(category_id=qp.get("category_id"), tag_id=qp.get("tag_id"))

def get_published_item_dto_factory(data: Dict[str, Any]) -> GetPublishedItemDTO:
    m = {**_path(data), **_query(data), **_body(data), **data}
    return GetPublishedItemDTO(slug=str(m.get("slug") or m.get("item_slug") or ""))
