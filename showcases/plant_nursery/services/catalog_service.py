# coding: utf-8, ASCII only
from decimal import Decimal
from typing import Any, List, Set
import uuid

from showcases.plant_nursery.domain.plant import Plant
from showcases.plant_nursery.domain.pricing import PriceCalculator, DiscountPolicy
from showcases.plant_nursery.domain.category import Category


class PlantNurseryCatalogService:
    def __init__(self, category_repo: Any):
        self.category_repo = category_repo
        self.price_calculator = PriceCalculator()
        self._plants: List[Plant] = []

    async def add_plant(self, plant: Plant) -> Plant:
        category = self.category_repo.get(plant.category_id)
        if not category:
            raise ValueError("Category does not exist")
        self._plants.append(plant)
        return plant

    def calculate_quote(
        self,
        unit_price: Decimal,
        quantity: int,
        discount_policy: DiscountPolicy = DiscountPolicy.NONE,
    ) -> Decimal:
        return self.price_calculator.calculate_total(
            unit_price=unit_price,
            quantity=quantity,
            discount_policy=discount_policy,
        )

    def find_frost_resistant_plants(self, min_temp: int) -> List[Plant]:
        return [plant for plant in self._plants if plant.frost_resistance <= min_temp]

    def _get_all_categories(self) -> List[Category]:
        if hasattr(self.category_repo, "_storage"):
            storage = getattr(self.category_repo, "_storage")
            if isinstance(storage, dict):
                return list(storage.values())
        if hasattr(self.category_repo, "list_all"):
            try:
                return self.category_repo.list_all()
            except Exception:
                pass
        return []

    def _collect_descendant_ids(self, root_id: uuid.UUID) -> Set[uuid.UUID]:
        collected: Set[uuid.UUID] = {root_id}
        all_cats = self._get_all_categories()
        changed = True
        while changed:
            changed = False
            for cat in all_cats:
                if cat.parent_id in collected and cat.id not in collected:
                    collected.add(cat.id)
                    changed = True
        return collected

    def find_plants_by_category(
        self, category_id: uuid.UUID, include_descendants: bool = False
    ) -> List[Plant]:
        cat = self.category_repo.get(category_id)
        if not cat:
            raise ValueError("validation.not_found")
        if not include_descendants:
            return [p for p in self._plants if p.category_id == category_id]
        allowed = self._collect_descendant_ids(category_id)
        return [p for p in self._plants if p.category_id in allowed]
