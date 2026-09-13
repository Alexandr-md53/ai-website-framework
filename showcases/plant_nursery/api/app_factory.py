# coding: utf-8, ASCII only
from typing import Dict, Tuple, Callable, Any, Optional
from ai_framework.product_registry import ProductInfo
from ai_framework.product.factory import build_app_from_product_info
from showcases.plant_nursery.services.catalog_service import PlantNurseryCatalogService
from showcases.plant_nursery.api.dto_factories import (
    add_plant_dto_factory,
    quote_dto_factory,
    frost_filter_dto_factory,
    create_category_dto_factory,
)
from showcases.plant_nursery.application.use_cases import (
    AddPlantUseCase,
    ListFrostResistantUseCase,
    QuoteUseCase,
    CreateCategoryUseCase,
)

_default_service: Optional[PlantNurseryCatalogService] = None


def _get_default_repo():
    from tests.showcases.plant_nursery.conftest import InMemoryCategoryRepository
    return InMemoryCategoryRepository()


def _get_default_service() -> PlantNurseryCatalogService:
    global _default_service
    if _default_service is None:
        _default_service = PlantNurseryCatalogService(category_repo=_get_default_repo())
    return _default_service


def _make_use_case_map(
    service: PlantNurseryCatalogService,
) -> Dict[Tuple[str, str], Tuple[Any, Callable[[Dict[str, Any]], Any]]]:
    return {
        ("POST", "/plants"): (
            AddPlantUseCase(catalog_service=service),
            add_plant_dto_factory,
        ),
        ("GET", "/plants"): (
            ListFrostResistantUseCase(catalog_service=service),
            frost_filter_dto_factory,
        ),
        ("POST", "/quotes"): (QuoteUseCase(catalog_service=service), quote_dto_factory),
        ("POST", "/categories"): (
            CreateCategoryUseCase(category_repo=service.category_repo),
            create_category_dto_factory,
        ),
    }


def build_plant_nursery_app(
    service_override: Optional[PlantNurseryCatalogService] = None,
):
    service = service_override or _get_default_service()
    info = ProductInfo(
        name="plant_nursery",
        path="showcases/plant_nursery",
        manifest={
            "name": "plant_nursery",
            "product": "crud",
            "version": "10.2.0-c1",
            "package": "showcases.plant_nursery",
        },
    )
    use_case_map = _make_use_case_map(service)
    app = build_app_from_product_info(info, use_case_map)
    app.state.service = service
    return app


def build_app(service_override=None):
    return build_plant_nursery_app(service_override=service_override)
