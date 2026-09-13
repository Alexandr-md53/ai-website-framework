# coding: utf-8, ASCII only
import uuid
import asyncio
from fastapi.testclient import TestClient
import pytest
from decimal import Decimal

from showcases.plant_nursery.domain.category import Category
from showcases.plant_nursery.domain.plant import (
    Plant,
    LightRequirement,
    WateringRequirement,
)
from showcases.plant_nursery.services.catalog_service import PlantNurseryCatalogService
from tests.showcases.plant_nursery.conftest import InMemoryCategoryRepository


def _build_app_with_repo(repo):
    from showcases.plant_nursery.api.app_factory import build_plant_nursery_app

    service = PlantNurseryCatalogService(category_repo=repo)
    app = build_plant_nursery_app(service_override=service)
    return app, service


def test_c13_1_01_add_plant_valid_category():
    repo = InMemoryCategoryRepository()
    cat = Category(
        id=uuid.uuid4(), name="Indoor Ferns", slug="indoor-ferns", parent_id=None
    )
    repo.add(cat)

    app, _ = _build_app_with_repo(repo)
    client = TestClient(app)

    payload = {
        "category_id": str(cat.id),
        "name": "Boston Fern",
        "description": "Classic indoor green plant",
        "light_req": "MEDIUM",
        "water_req": "FREQUENT",
        "frost_resistance": 0,
    }

    resp = client.post("/plants", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # framework may wrap in {success, data} or return direct - handle both
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    assert data["name"] == "Boston Fern"
    assert data["category_id"] == str(cat.id)


def test_c13_1_02_frost_filter():
    repo = InMemoryCategoryRepository()
    cat = Category(id=uuid.uuid4(), name="Conifers", slug="conifers", parent_id=None)
    repo.add(cat)

    app, service = _build_app_with_repo(repo)

    async def _seed():
        for name, frost in [("Siberian Pine", -35), ("Lemon Tree", 5)]:
            plant = Plant(
                id=uuid.uuid4(),
                category_id=cat.id,
                name=name,
                light_req=LightRequirement.MEDIUM,
                water_req=WateringRequirement.MODERATE,
                frost_resistance=frost,
            )
            await service.add_plant(plant)

    asyncio.run(_seed())

    client = TestClient(app)
    resp = client.get("/plants", params={"min_temp": -20})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        data = data["data"]
    names = [p["name"] for p in data] if isinstance(data, list) else [data.get("name")]
    assert "Siberian Pine" in names
    assert "Lemon Tree" not in names


def test_c13_1_03_quote_calculation():
    repo = InMemoryCategoryRepository()
    app, _ = _build_app_with_repo(repo)
    client = TestClient(app)

    payload = {
        "unit_price": "1200.00",
        "quantity": 10,
        "discount_policy": "VOLUME",
    }

    resp = client.post("/quotes", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    total = data.get("total") if isinstance(data, dict) else None
    assert total is not None
    assert Decimal(str(total)) == Decimal("10800.00")
