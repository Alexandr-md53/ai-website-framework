from decimal import Decimal
import uuid
import pytest

from showcases.plant_nursery.domain.plant import (
    Plant,
    LightRequirement,
    WateringRequirement,
)
from showcases.plant_nursery.domain.category import Category
from showcases.plant_nursery.domain.pricing import DiscountPolicy
from showcases.plant_nursery.services.catalog_service import PlantNurseryCatalogService


class TestPlantNurseryCatalogService:
    @pytest.mark.asyncio
    async def test_add_plant_to_valid_category_success(self, category_repo):
        # Создаем категорию
        category = Category(
            id=uuid.uuid4(),
            name="Indoor Ferns",
            slug="indoor-ferns",
            parent_id=None,
        )
        category_repo.add(category)

        service = PlantNurseryCatalogService(category_repo=category_repo)

        plant = Plant(
            id=uuid.uuid4(),
            category_id=category.id,
            name="Boston Fern",
            description="Classic indoor green plant",
            light_req=LightRequirement.MEDIUM,
            water_req=WateringRequirement.FREQUENT,
            frost_resistance=0,
        )

        created_plant = await service.add_plant(plant)
        assert created_plant.name == "Boston Fern"

    @pytest.mark.asyncio
    async def test_add_plant_to_nonexistent_category_fails(self, category_repo):
        service = PlantNurseryCatalogService(category_repo=category_repo)

        plant = Plant(
            id=uuid.uuid4(),
            category_id=uuid.uuid4(),  # Несуществующая категория
            name="Orphan Plant",
            light_req=LightRequirement.LOW,
            water_req=WateringRequirement.SPARSE,
        )

        with pytest.raises(ValueError, match="Category does not exist"):
            await service.add_plant(plant)

    def test_calculate_order_quote(self, category_repo):
        service = PlantNurseryCatalogService(category_repo=category_repo)

        # Вычисление котировки для 10 растений по 1200.00 со скидкой VOLUME
        quote = service.calculate_quote(
            unit_price=Decimal("1200.00"),
            quantity=10,
            discount_policy=DiscountPolicy.VOLUME,
        )

        # 10 * 1200 * 0.90 = 10800.00
        assert quote == Decimal("10800.00")

    @pytest.mark.asyncio
    async def test_filter_plants_by_frost_resistance(self, category_repo):
        service = PlantNurseryCatalogService(category_repo=category_repo)

        category = Category(
            id=uuid.uuid4(), name="Conifers", slug="conifers", parent_id=None
        )
        category_repo.add(category)

        plant_hardy = Plant(
            id=uuid.uuid4(),
            category_id=category.id,
            name="Siberian Pine",
            frost_resistance=-35,
        )
        plant_tender = Plant(
            id=uuid.uuid4(),
            category_id=category.id,
            name="Lemon Tree",
            frost_resistance=5,
        )

        await service.add_plant(plant_hardy)
        await service.add_plant(plant_tender)

        hardy_plants = service.find_frost_resistant_plants(min_temp=-20)
        assert len(hardy_plants) == 1
        assert hardy_plants[0].name == "Siberian Pine"
