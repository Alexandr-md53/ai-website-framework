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


@dataclass
class MoveCategoryDTO:
    id: Optional[str] = None
    parent_id: Optional[str] = None


@dataclass
class ListPlantsByCategoryDTO:
    id: Optional[str] = None
    include_descendants: bool = False


@dataclass
class AddPlantImageDTO:
    id: Optional[str] = None
    image_id: Optional[str] = None


@dataclass
class GetPlantImagesDTO:
    id: Optional[str] = None


def _run_async(coro):
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
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_in_new_loop)
            return future.result()
    except RuntimeError:
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


class MoveCategoryUseCase:
    def __init__(self, category_repo):
        self._repo = category_repo

    def execute(self, dto: MoveCategoryDTO):
        try:
            if not dto.id:
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": "validation.not_found",
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "code": "VALIDATION_ERROR",
                                "field": "id",
                                "message": "validation.not_found",
                                "message_key": "validation.not_found",
                            }
                        ],
                    },
                    "success": False,
                }
            try:
                cat_id = uuid.UUID(dto.id) if isinstance(dto.id, str) else dto.id
            except Exception:
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": "validation.not_found",
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "code": "VALIDATION_ERROR",
                                "field": "id",
                                "message": "validation.not_found",
                                "message_key": "validation.not_found",
                            }
                        ],
                    },
                    "success": False,
                }

            existing = self._repo.get(cat_id)
            if not existing:
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": "validation.not_found",
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "code": "VALIDATION_ERROR",
                                "field": "id",
                                "message": "validation.not_found",
                                "message_key": "validation.not_found",
                            }
                        ],
                    },
                    "success": False,
                }

            parent_uuid = None
            if dto.parent_id is not None:
                try:
                    parent_uuid = (
                        uuid.UUID(dto.parent_id)
                        if isinstance(dto.parent_id, str)
                        else dto.parent_id
                    )
                except Exception:
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

            updated = Category(
                id=existing.id,
                name=existing.name,
                slug=existing.slug,
                parent_id=parent_uuid,
            )
            self._repo.add(updated)

            return {
                "id": str(updated.id),
                "name": updated.name,
                "slug": updated.slug,
                "parent_id": str(updated.parent_id) if updated.parent_id else None,
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


class ListPlantsByCategoryUseCase:
    def __init__(self, catalog_service):
        self._service = catalog_service

    def execute(self, dto: ListPlantsByCategoryDTO):
        try:
            if not dto.id:
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": "validation.not_found",
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "code": "VALIDATION_ERROR",
                                "field": "id",
                                "message": "validation.not_found",
                                "message_key": "validation.not_found",
                            }
                        ],
                    },
                    "success": False,
                }
            try:
                cat_id = uuid.UUID(dto.id) if isinstance(dto.id, str) else dto.id
            except Exception:
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": "validation.not_found",
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "code": "VALIDATION_ERROR",
                                "field": "id",
                                "message": "validation.not_found",
                                "message_key": "validation.not_found",
                            }
                        ],
                    },
                    "success": False,
                }

            try:
                plants = self._service.find_plants_by_category(
                    cat_id, include_descendants=dto.include_descendants
                )
            except ValueError as ve:
                msg = str(ve)
                if "not_found" in msg:
                    return {
                        "status": 400,
                        "json": {
                            "success": False,
                            "error": "validation.not_found",
                            "code": "VALIDATION_ERROR",
                            "errors": [
                                {
                                    "code": "VALIDATION_ERROR",
                                    "field": "id",
                                    "message": "validation.not_found",
                                    "message_key": "validation.not_found",
                                }
                            ],
                        },
                        "success": False,
                    }
                raise

            result = [
                {
                    "id": str(p.id),
                    "category_id": str(p.category_id),
                    "name": p.name,
                    "frost_resistance": p.frost_resistance,
                }
                for p in plants
            ]
            return result

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


class AddPlantImageUseCase:
    def __init__(self, catalog_service):
        self._service = catalog_service

    def execute(self, dto: AddPlantImageDTO):
        try:
            if not dto.id:
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": "validation.not_found",
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "code": "VALIDATION_ERROR",
                                "field": "id",
                                "message": "validation.not_found",
                                "message_key": "validation.not_found",
                            }
                        ],
                    },
                    "success": False,
                }
            try:
                plant_id = uuid.UUID(dto.id) if isinstance(dto.id, str) else dto.id
            except Exception:
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": "validation.not_found",
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "code": "VALIDATION_ERROR",
                                "field": "id",
                                "message": "validation.not_found",
                                "message_key": "validation.not_found",
                            }
                        ],
                    },
                    "success": False,
                }

            if not dto.image_id:
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": "validation.not_found",
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "code": "VALIDATION_ERROR",
                                "field": "image_id",
                                "message": "validation.not_found",
                                "message_key": "validation.not_found",
                            }
                        ],
                    },
                    "success": False,
                }

            try:
                uuid.UUID(str(dto.image_id))
            except Exception:
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": "validation.not_found",
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "code": "VALIDATION_ERROR",
                                "field": "image_id",
                                "message": "validation.not_found",
                                "message_key": "validation.not_found",
                            }
                        ],
                    },
                    "success": False,
                }

            try:
                result = self._service.add_image_to_plant(plant_id, str(dto.image_id))
                return result
            except ValueError as ve:
                msg = str(ve)
                field = "id"
                code = "validation.not_found"
                if "max_limit" in msg:
                    field = "image_id"
                    code = "validation.max_limit"
                    return {
                        "status": 400,
                        "json": {
                            "success": False,
                            "error": code,
                            "code": "VALIDATION_ERROR",
                            "errors": [
                                {
                                    "code": "VALIDATION_ERROR",
                                    "field": field,
                                    "message": code,
                                    "message_key": code,
                                }
                            ],
                        },
                        "success": False,
                    }
                if "image_id" in msg:
                    field = "image_id"
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": code,
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "code": "VALIDATION_ERROR",
                                "field": field,
                                "message": code,
                                "message_key": code,
                            }
                        ],
                    },
                    "success": False,
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


class GetPlantImagesUseCase:
    def __init__(self, catalog_service):
        self._service = catalog_service

    def execute(self, dto: GetPlantImagesDTO):
        try:
            if not dto.id:
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": "validation.not_found",
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "code": "VALIDATION_ERROR",
                                "field": "id",
                                "message": "validation.not_found",
                                "message_key": "validation.not_found",
                            }
                        ],
                    },
                    "success": False,
                }
            try:
                plant_id = uuid.UUID(dto.id) if isinstance(dto.id, str) else dto.id
            except Exception:
                return {
                    "status": 400,
                    "json": {
                        "success": False,
                        "error": "validation.not_found",
                        "code": "VALIDATION_ERROR",
                        "errors": [
                            {
                                "code": "VALIDATION_ERROR",
                                "field": "id",
                                "message": "validation.not_found",
                                "message_key": "validation.not_found",
                            }
                        ],
                    },
                    "success": False,
                }

            try:
                result = self._service.get_images(plant_id)
                return result
            except ValueError as ve:
                msg = str(ve)
                if "not_found" in msg:
                    return {
                        "status": 400,
                        "json": {
                            "success": False,
                            "error": "validation.not_found",
                            "code": "VALIDATION_ERROR",
                            "errors": [
                                {
                                    "code": "VALIDATION_ERROR",
                                    "field": "id",
                                    "message": "validation.not_found",
                                    "message_key": "validation.not_found",
                                }
                            ],
                        },
                        "success": False,
                    }
                raise

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
