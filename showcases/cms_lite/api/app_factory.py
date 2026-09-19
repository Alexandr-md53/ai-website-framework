from typing import Dict, Tuple, Callable, Any
from ai_framework.product_registry import ProductInfo
from ai_framework.product.factory import build_app_from_product_info
from showcases.cms_lite.services.cms_service import CmsLiteService
from showcases.cms_lite.application.create_category_use_case import CreateCategoryUseCase
from showcases.cms_lite.application.create_item_use_case import CreateItemUseCase
from showcases.cms_lite.application.publish_item_use_case import PublishItemUseCase
from showcases.cms_lite.application.unpublish_item_use_case import UnpublishItemUseCase
from showcases.cms_lite.application.duplicate_item_use_case import DuplicateItemUseCase
from showcases.cms_lite.application.search_items_use_case import SearchItemsUseCase
from showcases.cms_lite.application.list_published_use_case import ListPublishedUseCase
from showcases.cms_lite.application.get_published_item_use_case import GetPublishedItemUseCase
from showcases.cms_lite.api.dto_factories import (
    create_category_dto_factory,
    create_item_dto_factory,
    publish_item_dto_factory,
    unpublish_item_dto_factory,
    duplicate_item_dto_factory,
    search_items_dto_factory,
    list_published_dto_factory,
    get_published_item_dto_factory,
)

_cms_service = CmsLiteService()

def _make_use_case_map():
    return {
        ("POST", "/categories"): (CreateCategoryUseCase(_cms_service), create_category_dto_factory),
        ("POST", "/items"): (CreateItemUseCase(_cms_service), create_item_dto_factory),
        ("POST", "/items/{item_id}/publish"): (PublishItemUseCase(_cms_service), publish_item_dto_factory),
        ("POST", "/items/{item_id}/unpublish"): (UnpublishItemUseCase(_cms_service), unpublish_item_dto_factory),
        ("POST", "/items/{item_id}/duplicate"): (DuplicateItemUseCase(_cms_service), duplicate_item_dto_factory),
        ("GET", "/items/search"): (SearchItemsUseCase(_cms_service), search_items_dto_factory),
        ("GET", "/public/items"): (ListPublishedUseCase(_cms_service), list_published_dto_factory),
        ("GET", "/public/items/{slug}"): (GetPublishedItemUseCase(_cms_service), get_published_item_dto_factory),
    }

def build_cms_lite_app(service_override=None):
    svc = service_override or _cms_service
    # rebuild map with override if needed
    if service_override:
        use_case_map = {
            ("POST", "/categories"): (CreateCategoryUseCase(svc), create_category_dto_factory),
            ("POST", "/items"): (CreateItemUseCase(svc), create_item_dto_factory),
            ("POST", "/items/{item_id}/publish"): (PublishItemUseCase(svc), publish_item_dto_factory),
            ("POST", "/items/{item_id}/unpublish"): (UnpublishItemUseCase(svc), unpublish_item_dto_factory),
            ("POST", "/items/{item_id}/duplicate"): (DuplicateItemUseCase(svc), duplicate_item_dto_factory),
            ("GET", "/items/search"): (SearchItemsUseCase(svc), search_items_dto_factory),
            ("GET", "/public/items"): (ListPublishedUseCase(svc), list_published_dto_factory),
            ("GET", "/public/items/{slug}"): (GetPublishedItemUseCase(svc), get_published_item_dto_factory),
        }
    else:
        use_case_map = _make_use_case_map()
    info = ProductInfo(name="cms_lite", path="showcases/cms_lite", manifest={"name":"cms_lite","product":"crud","version":"16.5-cms-lite-phase2-e2e-v0.1","package":"showcases.cms_lite"})
    app = build_app_from_product_info(info, use_case_map)
    return app
