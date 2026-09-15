# coding: utf-8, ASCII only
import uuid
import pytest
from fastapi.testclient import TestClient
from showcases.plant_nursery.services.catalog_service import PlantNurseryCatalogService
from showcases.plant_nursery.domain.category import Category
from showcases.plant_nursery.domain.plant import Plant
from showcases.plant_nursery.api.app_factory import build_plant_nursery_app


class InMemoryCategoryRepository:
    def __init__(self):
        self._storage = {}

    def add(self, cat):
        self._storage[cat.id] = cat

    def get(self, cat_id):
        return self._storage.get(cat_id)

    def list_all(self):
        return list(self._storage.values())


def _setup():
    repo = InMemoryCategoryRepository()
    cat = Category(id=uuid.uuid4(), name="TestCat", slug="test-cat")
    repo.add(cat)
    service = PlantNurseryCatalogService(category_repo=repo)
    p = Plant(id=uuid.uuid4(), category_id=cat.id, name="Stock10", stock_quantity=10)
    service._plants.append(p)
    return service, cat, p


@pytest.fixture
def setup():
    return _setup()


@pytest.fixture
def client(setup):
    service, _, _ = setup
    app = build_plant_nursery_app(service_override=service)
    return TestClient(app)


def test_c16_5_01_decrement_success(client, setup):
    service, _, p = setup
    resp = client.post(
        "/quotes",
        json={
            "plant_id": str(p.id),
            "unit_price": "10.00",
            "quantity": 3,
            "discount_policy": "NONE",
        },
    )
    assert resp.status_code == 200, resp.text
    # stock should be 7 now
    assert p.stock_quantity == 7, f"expected 7 got {p.stock_quantity}"


def test_c16_5_02_exact_stock_to_zero(client, setup):
    service, _, p = setup
    resp = client.post(
        "/quotes",
        json={
            "plant_id": str(p.id),
            "unit_price": "5.00",
            "quantity": 10,
            "discount_policy": "NONE",
        },
    )
    assert resp.status_code == 200, resp.text
    assert p.stock_quantity == 0
    assert p.is_available is False


def test_c16_5_03_second_quote_after_zero_fails(client, setup):
    service, _, p = setup
    # first drain
    r1 = client.post(
        "/quotes",
        json={
            "plant_id": str(p.id),
            "unit_price": "1.00",
            "quantity": 10,
            "discount_policy": "NONE",
        },
    )
    assert r1.status_code == 200
    # second should fail OUT_OF_STOCK
    r2 = client.post(
        "/quotes",
        json={
            "plant_id": str(p.id),
            "unit_price": "1.00",
            "quantity": 1,
            "discount_policy": "NONE",
        },
    )
    assert r2.status_code == 400, r2.text
    assert "OUT_OF_STOCK" in r2.text.upper()
