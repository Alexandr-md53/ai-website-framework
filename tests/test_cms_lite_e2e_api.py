# coding: utf-8, ASCII only
import uuid
import pytest
from fastapi.testclient import TestClient
from showcases.cms_lite.services.cms_service import CmsLiteService
from showcases.cms_lite.api.app_factory import build_cms_lite_app


def _make_client():
    svc = CmsLiteService()
    app = build_cms_lite_app(service_override=svc)
    return TestClient(app), svc


def test_cms_lite_crud_publish_public_flow():
    client, svc = _make_client()
    # 1. Create category as EDITOR
    r = client.post(
        "/categories",
        json={
            "name": "Blog",
            "slug": "blog",
            "user_role": "EDITOR",
            "user_id": str(uuid.uuid4()),
        },
    )
    assert r.status_code == 200, r.text
    cat_id = r.json()["id"] if isinstance(r.json(), dict) else r.json().get("id")
    # API returns ItemResponse style -> id in json
    # If response is wrapped, parse
    data = r.json()
    if isinstance(data, dict) and "id" in data:
        cat_id = data["id"]
    else:
        # fallback: get from service directly
        cats = svc.list_categories()
        cat_id = str(cats[0].id)

    # 2. Create item DRAFT
    editor_id = str(uuid.uuid4())
    r2 = client.post(
        "/items",
        json={
            "title": "Hello World",
            "slug": "hello-world",
            "content": "This is long enough content for publish >=20 chars",
            "category_id": cat_id,
            "user_role": "EDITOR",
            "user_id": editor_id,
        },
    )
    assert r2.status_code == 200, r2.text
    item_id = r2.json()["id"]

    # 3. Public cannot read DRAFT
    r_pub = client.get(f"/public/items/hello-world")
    assert r_pub.status_code == 404, r_pub.text

    # 4. Publish
    r_pub2 = client.post(
        f"/items/{item_id}/publish", json={"user_role": "EDITOR", "user_id": editor_id}
    )
    assert r_pub2.status_code == 200, r_pub2.text

    # 5. Public can read PUBLISHED
    r_pub3 = client.get(f"/public/items/hello-world")
    assert r_pub3.status_code == 200, r_pub3.text
    assert r_pub3.json()["slug"] == "hello-world"

    # 6. List published
    r_list = client.get("/public/items")
    assert r_list.status_code == 200
    assert len(r_list.json()) >= 1

    # 7. Duplicate
    r_dup = client.post(
        f"/items/{item_id}/duplicate",
        json={"user_role": "EDITOR", "user_id": editor_id},
    )
    assert r_dup.status_code == 200, r_dup.text
    assert r_dup.json()["status"] == "DRAFT"

    # 8. Unpublish
    r_unpub = client.post(
        f"/items/{item_id}/unpublish",
        json={"user_role": "EDITOR", "user_id": editor_id},
    )
    assert r_unpub.status_code == 200
    r_pub4 = client.get(f"/public/items/hello-world")
    assert r_pub4.status_code == 404


def test_cms_lite_auth_guard_viewer_forbidden():
    client, svc = _make_client()
    viewer_id = str(uuid.uuid4())
    r = client.post(
        "/categories",
        json={
            "name": "Hack",
            "slug": "hack",
            "user_role": "VIEWER",
            "user_id": viewer_id,
        },
    )
    # UseCase returns dict with status 403
    assert (
        r.status_code == 403
        or (r.status_code == 200 and r.json().get("status") == 403)
        or "Forbidden" in r.text
    )


def test_cms_lite_validation_slug_format():
    client, svc = _make_client()
    # Need category first
    ed_id = str(uuid.uuid4())
    r_cat = client.post(
        "/categories",
        json={"name": "Blog", "slug": "blog2", "user_role": "EDITOR", "user_id": ed_id},
    )
    assert r_cat.status_code == 200, r_cat.text
    # try invalid slug
    cat_id = svc.list_categories()[0].id
    r_bad = client.post(
        "/items",
        json={
            "title": "Bad",
            "slug": "Invalid Slug!",
            "content": "long enough content for publish test",
            "category_id": str(cat_id),
            "user_role": "EDITOR",
            "user_id": ed_id,
        },
    )
    assert r_bad.status_code in (400, 422), r_bad.text


def test_cms_lite_publish_requires_content_length():
    client, svc = _make_client()
    ed_id = str(uuid.uuid4())
    r_cat = client.post(
        "/categories",
        json={"name": "Blog", "slug": "blog3", "user_role": "EDITOR", "user_id": ed_id},
    )
    assert r_cat.status_code == 200
    cat_id = str(svc.list_categories()[0].id)
    # create with short content - draft allowed but publish should fail
    r_item = client.post(
        "/items",
        json={
            "title": "Short",
            "slug": "short",
            "content": "short",
            "category_id": cat_id,
            "user_role": "EDITOR",
            "user_id": ed_id,
        },
    )
    assert r_item.status_code == 200, r_item.text
    item_id = r_item.json()["id"]
    r_pub = client.post(
        f"/items/{item_id}/publish", json={"user_role": "EDITOR", "user_id": ed_id}
    )
    assert r_pub.status_code == 400, r_pub.text
