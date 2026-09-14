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


def _add_category(repo):
    cid = uuid.uuid4()
    repo.add(Category(id=cid, name="TestCat", slug="test-cat", parent_id=None))
    return cid


def _add_plant(service, category_id):
    plant = Plant(
        id=uuid.uuid4(),
        category_id=category_id,
        name="TestPlant",
        description="test",
        light_req=LightRequirement.MEDIUM,
        water_req=WateringRequirement.MODERATE,
        frost_resistance=0,
        main_image_id=None,
    )
    service._plants.append(plant)
    return plant


def _add_images(client, plant_id, n=2):
    ids = [str(uuid.uuid4()) for _ in range(n)]
    for iid in ids:
        r = client.post(f"/plants/{plant_id}/images", json={"image_id": iid})
        assert r.status_code == 200, r.text
    return ids


def test_c14_3_01_delete_non_main(client, repo, service):
    """C14.3.01 delete non-main -> main unchanged"""
    cat = _add_category(repo)
    plant = _add_plant(service, cat)
    img1, img2 = _add_images(client, plant.id, 2)

    # img1 is main, delete img2
    resp = client.delete(f"/plants/{plant.id}/images/{img2}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("deleted") == img2
    assert data.get("main_image_id") == img1
    assert data.get("count") == 1
    assert img1 in data.get("images", [])
    assert img2 not in data.get("images", [])


def test_c14_3_02_delete_main_promote_next(client, repo, service):
    """C14.3.02 delete main -> promote next"""
    cat = _add_category(repo)
    plant = _add_plant(service, cat)
    img1, img2, img3 = _add_images(client, plant.id, 3)

    resp = client.delete(f"/plants/{plant.id}/images/{img1}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("deleted") == img1
    assert data.get("main_image_id") == img2, (
        f"expected promotion to {img2}, got {data}"
    )
    assert data.get("count") == 2
    assert img1 not in data.get("images", [])
    assert data.get("images")[0] == img2


def test_c14_3_03_delete_last_main_null(client, repo, service):
    """C14.3.03 delete last -> main null"""
    cat = _add_category(repo)
    plant = _add_plant(service, cat)
    img1 = _add_images(client, plant.id, 1)[0]

    resp = client.delete(f"/plants/{plant.id}/images/{img1}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("deleted") == img1
    assert data.get("main_image_id") is None
    assert data.get("count") == 0
    assert data.get("images") == []


def test_c14_3_04_not_found(client, repo, service):
    """C14.3.04 plant/image not_found -> 400 validation.not_found"""
    cat = _add_category(repo)
    plant = _add_plant(service, cat)
    img1 = _add_images(client, plant.id, 1)[0]

    # unknown plant
    missing_plant = uuid.uuid4()
    resp = client.delete(f"/plants/{missing_plant}/images/{img1}")
    assert resp.status_code == 400, resp.text
    assert "not_found" in str(resp.json()).lower()

    # unknown image for existing plant
    fake_image = str(uuid.uuid4())
    resp2 = client.delete(f"/plants/{plant.id}/images/{fake_image}")
    assert resp2.status_code == 400, resp2.text
    txt = str(resp2.json()).lower()
    assert "not_found" in txt
    # should reference image_id field
    assert "image_id" in txt or "image" in txt
