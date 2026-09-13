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


def test_c14_2_01_empty_gallery(client, repo, service):
    """C14.2.01 empty gallery -> 200 images=[] main=null count=0"""
    cat = _add_category(repo)
    plant = _add_plant(service, cat)

    resp = client.get(f"/plants/{plant.id}/images")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("images") == [], f"expected empty images, got {data}"
    assert data.get("main_image_id") is None, f"expected main_image_id None, got {data}"
    assert data.get("count") == 0, f"expected count 0, got {data}"


def test_c14_2_02_full_gallery_after_posts(client, repo, service):
    """C14.2.02 after POSTs -> full gallery + main + count"""
    cat = _add_category(repo)
    plant = _add_plant(service, cat)
    img1 = str(uuid.uuid4())
    img2 = str(uuid.uuid4())

    r1 = client.post(f"/plants/{plant.id}/images", json={"image_id": img1})
    assert r1.status_code == 200, r1.text
    r2 = client.post(f"/plants/{plant.id}/images", json={"image_id": img2})
    assert r2.status_code == 200, r2.text

    resp = client.get(f"/plants/{plant.id}/images")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    images = data.get("images")
    assert isinstance(images, list), f"images not list: {data}"
    assert len(images) == 2, f"expected 2, got {images}"
    assert img1 in images and img2 in images, f"missing ids: {images}"
    # order should be insertion order
    assert images[0] == img1 and images[1] == img2, f"order mismatch: {images}"

    assert data.get("main_image_id") == img1, f"main should be first: {data}"
    assert data.get("count") == 2, f"count should be 2: {data}"


def test_c14_2_03_plant_not_found(client, repo, service):
    """C14.2.03 unknown plant -> 400 validation.not_found"""
    missing = uuid.uuid4()
    resp = client.get(f"/plants/{missing}/images")
    assert resp.status_code == 400, resp.text
    txt = str(resp.json()).lower()
    assert "not_found" in txt
