# coding: utf-8, ASCII only
from typing import Dict, Tuple, Callable, Any
from fastapi import Request
from fastapi.responses import JSONResponse
from ai_framework.product_registry import ProductInfo
from ai_framework.product.factory import build_app_from_product_info
from showcases.cafe.services.cafe_service import CafeService, PermissionDeniedError
from showcases.cafe.application.create_menu_item_use_case import CreateMenuItemUseCase
from showcases.cafe.application.update_price_use_case import UpdatePriceUseCase
from showcases.cafe.application.change_status_use_case import ChangeStatusUseCase
from showcases.cafe.api.dto_factories import create_menu_item_dto_factory, update_price_dto_factory, change_status_dto_factory

_cafe_service = CafeService()

def _make_use_case_map() -> Dict[Tuple[str, str], Tuple[Any, Callable[[Dict[str, Any]], Any]]]:
    create_uc = CreateMenuItemUseCase(service=_cafe_service)
    update_uc = UpdatePriceUseCase(service=_cafe_service)
    change_uc = ChangeStatusUseCase(service=_cafe_service)
    return {
        ("POST", "/menu-items"): (create_uc, create_menu_item_dto_factory),
        ("PATCH", "/menu-items/{item_id}/price"): (update_uc, update_price_dto_factory),
        ("PATCH", "/menu-items/{item_id}/status"): (change_uc, change_status_dto_factory),
    }

def build_cafe_app():
    info = ProductInfo(name="cafe", path="showcases/cafe", manifest={"name": "cafe", "product": "crud", "version": "10.2.0-c1", "package": "showcases.cafe"})
    use_case_map = _make_use_case_map()
    app = build_app_from_product_info(info, use_case_map)

    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
        return JSONResponse(status_code=403, content={"success": False, "error": str(exc), "code": "PERMISSION_DENIED", "errors": [{"code": "PERMISSION_DENIED", "message": str(exc)}]})

    return app
