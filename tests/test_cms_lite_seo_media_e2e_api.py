from __future__ import annotations
import pytest
from fastapi.testclient import TestClient

from showcases.cms_lite.app_factory import create_app
from showcases.cms_lite.services.cms_service_framework_wired import (
    CmsLiteFrameworkWiredService,
)


def _client():
    svc = CmsLiteFrameworkWiredService()
    app = create_app(service=svc)
    return TestClient(app), svc


def _h(role="EDITOR"):
    return {"X-Role": role, "X-User-Id": "test-user-1"}


def _create_category(client):
    r = client.post(
        "/categories",
        json={"name": "Default Cat", "slug": "default-cat"},
        headers=_h("EDITOR"),
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _create_item(client, cat_id):
    r = client.post(
        "/items",
        json={
            "title": "Test Item",
            "slug": "test-item",
            "content": "hello world content here",
            "category_id": cat_id,
        },
        headers=_h("EDITOR"),
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_seo_update_flow():
    client, _ = _client()
    cat_id = _create_category(client)
    item_id = _create_item(client, cat_id)

    payload = {
        "seo_title": "SEO Title 70 chars max",
        "seo_description": "SEO desc 160 chars max description",
        "og_title": "OG Title",
        "og_description": "OG Desc",
        "canonical_url": "https://example.com/test-item",
    }
    r = client.patch(f"/items/{item_id}/seo", json=payload, headers=_h("EDITOR"))
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["seo_title"] == payload["seo_title"]
    assert data["canonical_url"] == payload["canonical_url"]

    r2 = client.patch(
        f"/items/{item_id}/seo",
        json={"canonical_url": "ftp://bad.url"},
        headers=_h("EDITOR"),
    )
    assert r2.status_code in (400, 422), r2.text

    r3 = client.patch(
        f"/items/{item_id}/seo", json={"seo_title": "x"}, headers=_h("VIEWER")
    )
    assert r3.status_code == 403, r3.text


def test_media_attach_detach_flow():
    client, _ = _client()
    cat_id = _create_category(client)
    item_id = _create_item(client, cat_id)

    m_resp = client.post(
        "/media",
        json={
            "filename": "pic.jpg",
            "filepath": "/tmp/pic.jpg",
            "media_type": "image",
            "alt_text": "pic",
        },
        headers=_h("EDITOR"),
    )
    assert m_resp.status_code == 200, m_resp.text
    media_id = m_resp.json()["id"]

    a1 = client.post(f"/items/{item_id}/media/{media_id}/attach", headers=_h("EDITOR"))
    assert a1.status_code == 200, a1.text
    assert media_id in a1.json()["media_ids"]

    a2 = client.post(f"/items/{item_id}/media/{media_id}/attach", headers=_h("EDITOR"))
    assert a2.status_code == 200
    assert a2.json()["media_ids"].count(media_id) == 1

    lst = client.get(f"/items/{item_id}/media")
    assert lst.status_code == 200
    assert len(lst.json()["media"]) == 1

    d1 = client.post(f"/items/{item_id}/media/{media_id}/detach", headers=_h("EDITOR"))
    assert d1.status_code == 200
    assert media_id not in d1.json()["media_ids"]

    d2 = client.post(f"/items/{item_id}/media/{media_id}/detach", headers=_h("EDITOR"))
    assert d2.status_code == 200
    assert media_id not in d2.json()["media_ids"]

    m2 = client.post(
        "/media",
        json={"filename": "a.jpg", "filepath": "/tmp/a.jpg"},
        headers=_h("EDITOR"),
    ).json()["id"]
    v = client.post(f"/items/{item_id}/media/{m2}/attach", headers=_h("VIEWER"))
    assert v.status_code == 403


def test_seo_persists_after_publish():
    client, _ = _client()
    cat_id = _create_category(client)
    item_id = _create_item(client, cat_id)

    client.patch(
        f"/items/{item_id}/seo",
        json={"seo_title": "Persist Title", "canonical_url": "/test-item"},
        headers=_h("EDITOR"),
    )

    pub = client.post(f"/items/{item_id}/publish", headers=_h("EDITOR"))
    assert pub.status_code == 200, pub.text

    got = client.get(f"/items/{item_id}")
    assert got.status_code == 200
    assert got.json()["seo_title"] == "Persist Title"
    assert got.json()["canonical_url"] == "/test-item"


def test_seo_length_validation():
    client, _ = _client()
    cat_id = _create_category(client)
    item_id = _create_item(client, cat_id)

    long_title = "a" * 71
    r = client.patch(
        f"/items/{item_id}/seo", json={"seo_title": long_title}, headers=_h("EDITOR")
    )
    assert r.status_code in (400, 422)

    long_desc = "b" * 161
    r2 = client.patch(
        f"/items/{item_id}/seo",
        json={"seo_description": long_desc},
        headers=_h("EDITOR"),
    )
    assert r2.status_code in (400, 422)

    long_og_desc = "c" * 201
    r3 = client.patch(
        f"/items/{item_id}/seo",
        json={"og_description": long_og_desc},
        headers=_h("EDITOR"),
    )
    assert r3.status_code in (400, 422)
