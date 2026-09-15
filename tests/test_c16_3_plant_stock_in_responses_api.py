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
    p1 = Plant(id=uuid.uuid4(), category_id=cat.id, name="Monstera", stock_quantity=10)
    p2 = Plant(id=uuid.uuid4(), category_id=cat.id, name="Cactus", stock_quantity=0)
    service._plants.extend([p1, p2])
    return service, [p1, p2], cat


@pytest.fixture
def setup():
    return _setup_service()


@pytest.fixture
def client(setup):
    service, _, _ = setup
    app = build_plant_nursery_app(service_override=service)
    return TestClient(app)


def test_c16_3_01_post_plants_contains_stock_fields(client, setup):
    _, _, cat = setup
    resp = client.post(
        "/plants",
        json={"category_id": str(cat.id), "name": "NewPlant", "frost_resistance": 0},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "stock_quantity" in data, f"missing stock_quantity in {data}"
    assert "is_available" in data, f"missing is_available in {data}"
    assert data["stock_quantity"] == 0
    assert data["is_available"] is False


def test_c16_3_02_get_category_plants_contains_stock_fields(client, setup):
    _, plants, cat = setup
    resp = client.get(f"/categories/{cat.id}/plants")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list) and len(data) >= 2
    for item in data:
        assert "stock_quantity" in item, f"missing stock_quantity in {item}"
        assert "is_available" in item, f"missing is_available in {item}"
    # check values match setup
    by_id = {d["id"]: d for d in data}
    assert by_id[str(plants[0].id)]["stock_quantity"] == 10
    assert by_id[str(plants[0].id)]["is_available"] is True
    assert by_id[str(plants[1].id)]["stock_quantity"] == 0
    assert by_id[str(plants[1].id)]["is_available"] is False


def test_c16_3_03_patch_reflected_in_category_plants(client, setup):
    _, plants, cat = setup
    pid = plants[0].id
    # patch to 0
    r1 = client.patch(f"/plants/{pid}/stock", json={"stock_quantity": 0})
    assert r1.status_code == 200, r1.text
    r2 = client.get(f"/categories/{cat.id}/plants")
    assert r2.status_code == 200
    by_id = {d["id"]: d for d in r2.json()}
    assert by_id[str(pid)]["stock_quantity"] == 0
    assert by_id[str(pid)]["is_available"] is False
    # patch back to 5
    r3 = client.patch(f"/plants/{pid}/stock", json={"stock_quantity": 5})
    assert r3.status_code == 200
    r4 = client.get(f"/categories/{cat.id}/plants")
    by_id2 = {d["id"]: d for d in r4.json()}
    assert by_id2[str(pid)]["stock_quantity"] == 5
    assert by_id2[str(pid)]["is_available"] is True
