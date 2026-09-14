# coding: utf-8, ASCII only
from decimal import Decimal
from typing import Any, List, Set, Dict
import uuid

from showcases.plant_nursery.domain.plant import Plant
from showcases.plant_nursery.domain.pricing import PriceCalculator, DiscountPolicy
from showcases.plant_nursery.domain.category import Category


class PlantNurseryCatalogService:
    def __init__(self, category_repo: Any):
        self.category_repo = category_repo
        self.price_calculator = PriceCalculator()
        self._plants: List[Plant] = []
        self._gallery: Dict[uuid.UUID, List[str]] = {}

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

    def _find_plant(self, plant_id: uuid.UUID) -> Plant:
        for p in self._plants:
            if p.id == plant_id:
                return p
        return None

    
    def update_stock(self, plant_id: uuid.UUID, stock_quantity: int) -> dict:
        if stock_quantity is None:
            raise ValueError("validation.invalid")
        try:
            qty = int(stock_quantity)
        except Exception:
            raise ValueError("validation.invalid")
        if qty < 0:
            raise ValueError("validation.invalid")
        plant = self._find_plant(plant_id)
        if not plant:
            raise ValueError("validation.not_found:id")
        plant.stock_quantity = qty
        return {
            "id": str(plant.id),
            "stock_quantity": plant.stock_quantity,
            "is_available": plant.stock_quantity > 0,
        }

    def add_image_to_plant(self, plant_id: uuid.UUID, image_id: str) -> Dict[str, Any]:
        try:
            uuid.UUID(str(image_id))
        except Exception:
            raise ValueError("validation.not_found:image_id")

        plant = self._find_plant(plant_id)
        if not plant:
            raise ValueError("validation.not_found:id")

        gallery = self._gallery.get(plant_id, [])
        if len(gallery) >= 5:
            raise ValueError("validation.max_limit")

        if image_id not in gallery:
            gallery.append(str(image_id))
            self._gallery[plant_id] = gallery

        if not plant.main_image_id:
            plant.main_image_id = str(image_id)

        return {
            "id": str(plant.id),
            "main_image_id": plant.main_image_id,
            "images": list(gallery),
            "gallery": list(gallery),
        }

    def get_images(self, plant_id: uuid.UUID) -> Dict[str, Any]:
        plant = self._find_plant(plant_id)
        if not plant:
            raise ValueError("validation.not_found:id")
        gallery = self._gallery.get(plant_id, [])
        return {
            "id": str(plant.id),
            "images": list(gallery),
            "main_image_id": plant.main_image_id,
            "count": len(gallery),
        }

    def remove_image_from_plant(
        self, plant_id: uuid.UUID, image_id: str
    ) -> Dict[str, Any]:
        try:
            uuid.UUID(str(image_id))
        except Exception:
            raise ValueError("validation.not_found:image_id")

        plant = self._find_plant(plant_id)
        if not plant:
            raise ValueError("validation.not_found:id")

        gallery = self._gallery.get(plant_id, [])
        if str(image_id) not in gallery:
            raise ValueError("validation.not_found:image_id")

        # remove
        new_gallery = [i for i in gallery if i != str(image_id)]
        self._gallery[plant_id] = new_gallery

        # main promotion
        if plant.main_image_id == str(image_id):
            if new_gallery:
                plant.main_image_id = new_gallery[0]
            else:
                plant.main_image_id = None

        return {
            "id": str(plant.id),
            "images": list(new_gallery),
            "main_image_id": plant.main_image_id,
            "count": len(new_gallery),
            "deleted": str(image_id),
        }
