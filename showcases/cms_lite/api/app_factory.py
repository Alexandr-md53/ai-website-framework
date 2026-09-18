from typing import Dict, Tuple, Callable, Any
from ai_framework.product_registry import ProductInfo
from ai_framework.product.factory import build_app_from_product_info
from showcases.cms_lite.services.cms_service import CmsLiteService
from showcases.cms_lite.application.create_item_use_case import CreateItemUseCase
from showcases.cms_lite.application.publish_item_use_case import PublishItemUseCase
from showcases.cms_lite.application.unpublish_item_use_case import UnpublishItemUseCase
from showcases.cms_lite.application.duplicate_item_use_case import DuplicateItemUseCase
from showcases.cms_lite.application.search_items_use_case import SearchItemsUseCase
from showcases.cms_lite.api.dto_factories import create_item_dto_factory, publish_item_dto_factory, unpublish_item_dto_factory, duplicate_item_dto_factory, search_items_dto_factory
_cms_service = CmsLiteService()
def _make_use_case_map():
    return {
        ("POST", "/items"): (CreateItemUseCase(_cms_service), create_item_dto_factory),
        ("POST", "/items/{item_id}/publish"): (PublishItemUseCase(_cms_service), publish_item_dto_factory),
        ("POST", "/items/{item_id}/unpublish"): (UnpublishItemUseCase(_cms_service), unpublish_item_dto_factory),
        ("POST", "/items/{item_id}/duplicate"): (DuplicateItemUseCase(_cms_service), duplicate_item_dto_factory),
        ("GET", "/items/search"): (SearchItemsUseCase(_cms_service), search_items_dto_factory),
    }
def build_cms_lite_app():
    info = ProductInfo(name="cms_lite", path="showcases/cms_lite", manifest={"name":"cms_lite","product":"crud","version":"16.5-first-site-decision-A-v0.1","package":"showcases.cms_lite"})
    app = build_app_from_product_info(info, _make_use_case_map())
    return app
