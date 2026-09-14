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
    cat = Category(id=uuid.uuid4(), name="Test", slug="test")
    repo.add(cat)
    service = PlantNurseryCatalogService(category_repo=repo)
    plant = Plant(id=uuid.uuid4(), category_id=cat.id, name="Monstera")
    service._plants.append(plant)
    return service, plant, cat

@pytest.fixture
def setup():
    return _setup_service()

@pytest.fixture
def client(setup):
    service, _, _ = setup
    app = build_plant_nursery_app(service_override=service)
    return TestClient(app)

def test_c16_1_01_update_stock_success(setup, client):
    service, plant, _ = setup
    resp = client.patch(f"/plants/{plant.id}/stock", json={"stock_quantity": 15})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == str(plant.id)
    assert data["stock_quantity"] == 15
    assert data["is_available"] is True

def test_c16_1_02_update_stock_zero_not_available(setup, client):
    service, plant, _ = setup
    resp = client.patch(f"/plants/{plant.id}/stock", json={"stock_quantity": 0})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["stock_quantity"] == 0
    assert data["is_available"] is False

def test_c16_1_03_negative_stock_invalid(setup, client):
    service, plant, _ = setup
    resp = client.patch(f"/plants/{plant.id}/stock", json={"stock_quantity": -5})
    assert resp.status_code == 400, resp.text

def test_c16_1_04_not_found(setup, client):
    fake_id = uuid.uuid4()
    resp = client.patch(f"/plants/{fake_id}/stock", json={"stock_quantity": 10})
    assert resp.status_code in (400, 404), resp.text

def test_c16_1_05_update_stock_overwrites(setup, client):
    service, plant, _ = setup
    resp1 = client.patch(f"/plants/{plant.id}/stock", json={"stock_quantity": 5})
    assert resp1.status_code == 200
    resp2 = client.patch(f"/plants/{plant.id}/stock", json={"stock_quantity": 20})
    assert resp2.status_code == 200
    assert resp2.json()["stock_quantity"] == 20
