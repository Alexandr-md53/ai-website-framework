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


def _setup_service():
    repo = InMemoryCategoryRepository()
    cat = Category(id=uuid.uuid4(), name="TestCat", slug="test-cat")
    repo.add(cat)
    service = PlantNurseryCatalogService(category_repo=repo)
    p_out = Plant(
        id=uuid.uuid4(), category_id=cat.id, name="OutOfStock", stock_quantity=0
    )
    p_low = Plant(
        id=uuid.uuid4(), category_id=cat.id, name="LowStock", stock_quantity=2
    )
    p_ok = Plant(id=uuid.uuid4(), category_id=cat.id, name="Enough", stock_quantity=10)
    service._plants.extend([p_out, p_low, p_ok])
    return service, p_out, p_low, p_ok


@pytest.fixture
def setup():
    return _setup_service()


@pytest.fixture
def client(setup):
    service, _, _, _ = setup
    app = build_plant_nursery_app(service_override=service)
    return TestClient(app)


def test_c16_4_01_out_of_stock(client, setup):
    _, p_out, _, _ = setup
    resp = client.post(
        "/quotes",
        json={
            "plant_id": str(p_out.id),
            "unit_price": "10.00",
            "quantity": 1,
            "discount_policy": "NONE",
        },
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    # error code should be OUT_OF_STOCK somewhere
    txt = str(body).upper()
    assert "OUT_OF_STOCK" in txt, f"expected OUT_OF_STOCK in {body}"


def test_c16_4_02_insufficient_stock(client, setup):
    _, _, p_low, _ = setup
    resp = client.post(
        "/quotes",
        json={
            "plant_id": str(p_low.id),
            "unit_price": "10.00",
            "quantity": 5,
            "discount_policy": "NONE",
        },
    )
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert "INSUFFICIENT_STOCK" in str(body).upper(), (
        f"expected INSUFFICIENT_STOCK in {body}"
    )


def test_c16_4_03_sufficient_stock_ok(client, setup):
    _, _, _, p_ok = setup
    resp = client.post(
        "/quotes",
        json={
            "plant_id": str(p_ok.id),
            "unit_price": "10.00",
            "quantity": 3,
            "discount_policy": "NONE",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "total" in data


def test_c16_4_04_no_plant_id_backward_compat(client, setup):
    resp = client.post(
        "/quotes",
        json={"unit_price": "10.00", "quantity": 9999, "discount_policy": "NONE"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "total" in data
