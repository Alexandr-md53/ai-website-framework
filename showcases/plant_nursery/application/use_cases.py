# coding: utf-8, ASCII only
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import uuid
from decimal import Decimal
from showcases.plant_nursery.domain.plant import (
    Plant,
    LightRequirement,
    WateringRequirement,
)
from showcases.plant_nursery.domain.pricing import DiscountPolicy


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

            # sync validation same as in PlantNurseryCatalogService.add_plant but without async
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

            # direct append to avoid async call issue under TestClient event loop
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
