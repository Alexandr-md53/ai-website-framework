# coding: utf-8, ASCII only
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import uuid
import asyncio
import concurrent.futures
from decimal import Decimal
from showcases.plant_nursery.domain.category import Category
from showcases.plant_nursery.domain.plant import (
    Plant,
    LightRequirement,
    WateringRequirement,
)
from showcases.plant_nursery.domain.pricing import DiscountPolicy
from showcases.plant_nursery.validation.category_rules import CategoryHierarchyValidator
from ai_framework.validation import ValidationEngine, ValidationContext


@dataclass
class AddPlantDTO:
    category_id: str
    name: str
    description: Optional[str] = None
    light_req: str = "MEDIUM"
    water_req: str = "MODERATE"
    frost_resistance: int = 0
    main_image_id: Optional[str] = None


@dataclass
class FrostFilterDTO:
    min_temp: int


@dataclass
class QuoteDTO:
    unit_price: str
    quantity: int
    discount_policy: str = "NONE"


@dataclass
class CreateCategoryDTO:
    name: str
    slug: str
    parent_id: Optional[str] = None
    id: Optional[str] = None


def _run_async(coro):
    """Sync wrapper robust for TestClient running loop - never uses asyncio.run() inside running loop"""

    def _run_in_new_loop():
        new_loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(coro)
        finally:
            try:
                new_loop.close()
            except Exception:
                pass
            asyncio.set_event_loop(None)

    try:
        # If we are inside a running loop (FastAPI TestClient), offload to thread
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_in_new_loop)
            return future.result()
    except RuntimeError:
        # No running loop in this thread - direct run
        return _run_in_new_loop()


class AddPlantUseCase:
    def __init__(self, catalog_service):
        self._service = catalog_service

    def execute(self, dto: AddPlantDTO):
        try:
            cat_id = (
                uuid.UUID(dto.category_id)
                if isinstance(dto.category_id, str)
                else dto.category_id
            )
            light = (
                LightRequirement(dto.light_req)
                if isinstance(dto.light_req, str)
                else dto.light_req
            )
            water = (
                WateringRequirement(dto.water_req)
                if isinstance(dto.water_req, str)
                else dto.water_req
            )
            category = self._service.category_repo.get(cat_id)
            if not category:
                raise ValueError("Category does not exist")
            plant = Plant(
                id=uuid.uuid4(),
                category_id=cat_id,
                name=dto.name,
                description=dto.description,
                light_req=light,
                water_req=water,
                frost_resistance=int(dto.frost_resistance),
                main_image_id=dto.main_image_id,
            )
            self._service._plants.append(plant)
            created = plant
            return {
                "id": str(created.id),
                "category_id": str(created.category_id),
                "name": created.name,
                "description": created.description,
                "light_req": created.light_req.value
                if hasattr(created.light_req, "value")
                else str(created.light_req),
                "water_req": created.water_req.value
                if hasattr(created.water_req, "value")
                else str(created.water_req),
                "frost_resistance": created.frost_resistance,
                "main_image_id": created.main_image_id,
            }
        except ValueError as e:
            return {
                "status": 400,
                "json": {
                    "success": False,
                    "error": str(e),
                    "code": "VALIDATION_ERROR",
                    "errors": [{"code": "VALIDATION_ERROR", "message": str(e)}],
                },
                "success": False,
            }


class ListFrostResistantUseCase:
    def __init__(self, catalog_service):
        self._service = catalog_service

    def execute(self, dto: FrostFilterDTO) -> List[Dict[str, Any]]:
        plants = self._service.find_frost_resistant_plants(min_temp=dto.min_temp)
        return [
            {
                "id": str(p.id),
                "category_id": str(p.category_id),
                "name": p.name,
                "frost_resistance": p.frost_resistance,
            }
            for p in plants
        ]


class QuoteUseCase:
    def __init__(self, catalog_service):
        self._service = catalog_service

    def execute(self, dto: QuoteDTO) -> Dict[str, Any]:
        try:
            unit_price = Decimal(str(dto.unit_price))
            policy = (
                DiscountPolicy(dto.discount_policy)
                if isinstance(dto.discount_policy, str)
                else dto.discount_policy
            )
            total = self._service.calculate_quote(
                unit_price=unit_price,
                quantity=int(dto.quantity),
                discount_policy=policy,
            )
            return {
                "unit_price": str(unit_price),
                "quantity": int(dto.quantity),
                "discount_policy": policy.value
                if hasattr(policy, "value")
                else str(policy),
                "total": str(total),
            }
        except ValueError as e:
            return {
                "status": 400,
                "json": {
                    "success": False,
                    "error": str(e),
                    "code": "VALIDATION_ERROR",
                    "errors": [{"code": "VALIDATION_ERROR", "message": str(e)}],
                },
                "success": False,
            }


class CreateCategoryUseCase:
    def __init__(self, category_repo):
        self._repo = category_repo

    def execute(self, dto: CreateCategoryDTO):
        try:
            cat_id = uuid.UUID(dto.id) if dto.id else uuid.uuid4()
            parent_uuid = None
            if dto.parent_id:
                try:
                    parent_uuid = (
                        uuid.UUID(dto.parent_id)
                        if isinstance(dto.parent_id, str)
                        else dto.parent_id
                    )
                except Exception:
                    # invalid format -> will be treated as not_found by repo.get returning None
                    # create a UUID that definitely does not exist to trigger not_found
                    parent_uuid = uuid.UUID(dto.parent_id) if False else None
                    # Instead return not_found directly via validation path
                    # Build payload with random UUID to force not_found
                    payload = {"id": cat_id, "parent_id": uuid.uuid4()}
                    context = ValidationContext(persistence_provider=self._repo)
                    engine = ValidationEngine(context=context)
                    rules = {"parent_id": [CategoryHierarchyValidator()]}

                    async def _validate_invalid():
                        return await engine.validate(payload=payload, rules=rules)

                    result = _run_async(_validate_invalid())
                    # force not_found error
                    return {
                        "status": 400,
                        "json": {
                            "success": False,
                            "error": "validation.not_found",
                            "code": "VALIDATION_ERROR",
                            "errors": [
                                {
                                    "code": "VALIDATION_ERROR",
                                    "field": "parent_id",
                                    "message": "validation.not_found",
                                    "message_key": "validation.not_found",
                                }
                            ],
                        },
                        "success": False,
                    }

            payload = {"id": cat_id, "parent_id": parent_uuid}
            context = ValidationContext(persistence_provider=self._repo)
            engine = ValidationEngine(context=context)
            rules = {"parent_id": [CategoryHierarchyValidator()]}

            async def _validate():
                return await engine.validate(payload=payload, rules=rules)

            result = _run_async(_validate())

            is_valid = getattr(result, "is_valid", None)
            if is_valid is None:
                is_valid = getattr(result, "valid", False)

            if not is_valid:
                first_error = result.errors[0] if result.errors else None
                msg_key = (
                    getattr(first_error, "message_key", "validation.error")
                    if first_error
                    else "validation.error"
                )
                field = (
                    getattr(first_error, "field", "parent_id")
                    if first_error
                    else "parent_id"
                )
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": msg_key,
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "code": "VALIDATION_ERROR",
                                "field": field,
                                "message": msg_key,
                                "message_key": msg_key,
                            }
                        ],
                    },
                    "success": False,
                }

            category = Category(
                id=cat_id, name=dto.name, slug=dto.slug, parent_id=parent_uuid
            )
            self._repo.add(category)

            return {
                "id": str(category.id),
                "name": category.name,
                "slug": category.slug,
                "parent_id": str(category.parent_id) if category.parent_id else None,
            }
        except ValueError as e:
            return {
                "status": 400,
                "json": {
                    "success": False,
                    "error": str(e),
                    "code": "VALIDATION_ERROR",
                    "errors": [{"code": "VALIDATION_ERROR", "message": str(e)}],
                },
                "success": False,
            }
