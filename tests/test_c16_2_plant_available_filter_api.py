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
    p1 = Plant(id=uuid.uuid4(), category_id=cat.id, name="Monstera", stock_quantity=10)
    p2 = Plant(id=uuid.uuid4(), category_id=cat.id, name="Cactus", stock_quantity=0)
    p3 = Plant(id=uuid.uuid4(), category_id=cat.id, name="Fern", stock_quantity=5)
    service._plants.extend([p1, p2, p3])
    return service, [p1, p2, p3], cat


@pytest.fixture
def setup():
    return _setup_service()


@pytest.fixture
def client(setup):
    service, _, _ = setup
    app = build_plant_nursery_app(service_override=service)
    return TestClient(app)


def test_c16_2_01_available_true_only_available(setup, client):
    _, plants, _ = setup
    resp = client.get("/plants?available=true")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # data is list of dicts
    ids = {d["id"] for d in data}
    assert str(plants[0].id) in ids
    assert str(plants[2].id) in ids
    assert str(plants[1].id) not in ids


def test_c16_2_02_available_false_only_unavailable(setup, client):
    _, plants, _ = setup
    resp = client.get("/plants?available=false")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    ids = {d["id"] for d in data}
    assert str(plants[1].id) in ids
    assert str(plants[0].id) not in ids


def test_c16_2_03_no_param_returns_all(setup, client):
    _, plants, _ = setup
    resp = client.get("/plants")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 3


def test_c16_2_04_combined_with_frost_filter(setup, client):
    # frost filter should still work
    resp = client.get("/plants?available=true&min_temp=100")
    assert resp.status_code == 200
