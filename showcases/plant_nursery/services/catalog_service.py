from decimal import Decimal
from typing import Any, List, Optional

from showcases.plant_nursery.domain.plant import Plant
from showcases.plant_nursery.domain.pricing import PriceCalculator, DiscountPolicy


class PlantNurseryCatalogService:
    def __init__(self, category_repo: Any):
        self.category_repo = category_repo
        self.price_calculator = PriceCalculator()
        self._plants: List[Plant] = []

    async def add_plant(self, plant: Plant) -> Plant:
        """Добавление растения с проверкой существования привязанной категории."""
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
        """Расчет стоимости партии с учетом выбранной политики скидок."""
        return self.price_calculator.calculate_total(
            unit_price=unit_price,
            quantity=quantity,
            discount_policy=discount_policy,
        )

    def find_frost_resistant_plants(self, min_temp: int) -> List[Plant]:
        """Фильтрация растений, способных выдерживать температуру min_temp и ниже."""
        return [plant for plant in self._plants if plant.frost_resistance <= min_temp]
