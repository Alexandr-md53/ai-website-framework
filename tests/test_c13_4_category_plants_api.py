# coding: utf-8, ASCII only
import uuid
import pytest
from fastapi.testclient import TestClient
from showcases.plant_nursery.api.app_factory import build_plant_nursery_app
from tests.showcases.plant_nursery.conftest import InMemoryCategoryRepository
from showcases.plant_nursery.services.catalog_service import PlantNurseryCatalogService
from showcases.plant_nursery.domain.category import Category
from showcases.plant_nursery.domain.plant import (
    Plant,
    LightRequirement,
    WateringRequirement,
)


@pytest.fixture
def repo():
    return InMemoryCategoryRepository()


@pytest.fixture
def service(repo):
    return PlantNurseryCatalogService(category_repo=repo)


@pytest.fixture
def client(service):
    app = build_plant_nursery_app(service_override=service)
    return TestClient(app)


def _add_category(repo, name, slug, parent_id=None):
    cid = uuid.uuid4()
    repo.add(Category(id=cid, name=name, slug=slug, parent_id=parent_id))
    return cid


def _add_plant(service, category_id, name):
    plant = Plant(
        id=uuid.uuid4(),
        category_id=category_id,
        name=name,
        description="test",
        light_req=LightRequirement.MEDIUM,
        water_req=WateringRequirement.MODERATE,
        frost_resistance=0,
        main_image_id=None,
    )
    service._plants.append(plant)
    return plant


def test_c13_4_01_direct_only(client, repo, service):
    """C13.4.01 direct only include_descendants=false"""
    root = _add_category(repo, "Root", "root")
    child = _add_category(repo, "Child", "child", parent_id=root)

    p_root = _add_plant(service, root, "RootPlant")
    p_child = _add_plant(service, child, "ChildPlant")

    resp = client.get(f"/categories/{root}/plants?include_descendants=false")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    ids = [
        item["id"] if isinstance(item, dict) else item.get("id")
        for item in (data if isinstance(data, list) else data.get("items", []))
    ]
    # If wrapped in envelope
    if isinstance(data, dict) and "items" in data:
        ids = [p["id"] for p in data["items"]]
    else:
        ids = [p["id"] for p in data] if isinstance(data, list) else []
    assert str(p_root.id) in ids
    assert str(p_child.id) not in ids


def test_c13_4_02_descendants(client, repo, service):
    """C13.4.02 include_descendants=true includes child"""
    root = _add_category(repo, "Root", "root")
    child = _add_category(repo, "Child", "child", parent_id=root)

    p_root = _add_plant(service, root, "RootPlant")
    p_child = _add_plant(service, child, "ChildPlant")

    resp = client.get(f"/categories/{root}/plants?include_descendants=true")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    plants = (
        data if isinstance(data, list) else data.get("items", data.get("plants", []))
    )
    ids = [p["id"] for p in plants]
    assert str(p_root.id) in ids
    assert str(p_child.id) in ids


def test_c13_4_03_deep_descendants(client, repo, service):
    """C13.4.03 deep descendants true includes grandchild"""
    root = _add_category(repo, "Root", "root")
    child = _add_category(repo, "Child", "child", parent_id=root)
    grand = _add_category(repo, "Grand", "grand", parent_id=child)

    p_root = _add_plant(service, root, "RootPlant")
    p_child = _add_plant(service, child, "ChildPlant")
    p_grand = _add_plant(service, grand, "GrandPlant")

    resp = client.get(f"/categories/{root}/plants?include_descendants=true")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    plants = (
        data if isinstance(data, list) else data.get("items", data.get("plants", []))
    )
    ids = [p["id"] for p in plants]
    assert str(p_root.id) in ids
    assert str(p_child.id) in ids
    assert str(p_grand.id) in ids


def test_c13_4_04_not_found(client, repo, service):
    """C13.4.04 unknown category -> 400 validation.not_found"""
    missing = uuid.uuid4()
    resp = client.get(f"/categories/{missing}/plants?include_descendants=false")
    assert resp.status_code == 400, resp.text
    data = resp.json()
    assert data.get("success") is False or "error" in data or "errors" in data


def test_c13_4_05_empty_category(client, repo, service):
    """C13.4.05 empty category -> 200 []"""
    root = _add_category(repo, "Empty", "empty")
    resp = client.get(f"/categories/{root}/plants?include_descendants=false")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    plants = (
        data if isinstance(data, list) else data.get("items", data.get("plants", []))
    )
    assert isinstance(plants, list)
    assert len(plants) == 0
