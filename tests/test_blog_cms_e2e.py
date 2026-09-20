import pytest
from fastapi.testclient import TestClient
from showcases.blog_cms.api.app_factory import create_test_app, FROZEN_ROUTES
from showcases.blog_cms.app_factory import FROZEN_ROUTES as MAIN_FROZEN


def test_frozen_route_map_smoke():
    app = create_test_app()
    # normalize: methods are set like {'GET'} — we check containment
    found = set()
    for r in app.routes:
        if not hasattr(r, "path"):
            continue
        methods = getattr(r, "methods", None)
        if not methods:
            continue
        for m in methods:
            # normalize {path:path} -> {path} for comparison, keep {post_id} as is
            path = r.path.replace("{path:path}", "{path}")
            found.add(f"{m} {path}")
    # also normalize frozen
    normalized_frozen = {rt.replace("{path:path}", "{path}") for rt in FROZEN_ROUTES}
    # frozen must be subset of found (allow extra docs/openapi)
    missing = [rt for rt in normalized_frozen if rt not in found]
    assert not missing, (
        f"Missing routes vs frozen map: {missing}\nFound: {found}\nFrozen: {normalized_frozen}"
    )
    assert FROZEN_ROUTES == MAIN_FROZEN


def test_auth_guard_viewer_forbidden_and_headers_normalization():
    app = create_test_app()
    client = TestClient(app)
    # VIEWER cannot create category
    r = client.post(
        "/categories",
        json={"name": "Hack", "slug": "hack"},
        headers={"X-User-Id": "u1", "X-User-Role": "VIEWER"},
    )
    assert r.status_code == 403
    # EDITOR can
    r2 = client.post(
        "/categories",
        json={"name": "Blog", "slug": "blog"},
        headers={"X-User-Id": "u2", "X-User-Role": "EDITOR"},
    )
    assert r2.status_code == 200


def test_static_generation_pipeline_G1_G2_G12():
    app = create_test_app()
    client = TestClient(app)
    # setup
    cat = client.post(
        "/categories",
        json={"name": "Tech", "slug": "tech"},
        headers={"X-User-Role": "EDITOR"},
    ).json()
    author = client.post(
        "/authors",
        json={"name": "Ada", "slug": "ada"},
        headers={"X-User-Role": "EDITOR"},
    ).json()
    post = client.post(
        "/posts",
        json={
            "title": "Hello World",
            "slug": "hello-world",
            "content": "This is long enough content for publish >=20 chars",
            "category_id": cat["id"],
            "author_id": author["id"],
        },
        headers={"X-User-Role": "EDITOR"},
    ).json()
    client.post(f"/posts/{post['id']}/publish", headers={"X-User-Role": "EDITOR"})
    # generate
    gen = client.post("/site/generate", headers={"X-User-Role": "GENERATOR"})
    assert gen.status_code == 200
    assert gen.json()["generated"] >= 4  # index + post + category + rss + sitemap
    pages = client.get("/site/pages").json()
    paths = [p["path"] for p in pages]
    assert "index.html" in paths
    assert "posts/hello-world/index.html" in paths
    assert "rss.xml" in paths
    assert "sitemap.xml" in paths
    # public read still works
    pub = client.get("/public/posts/hello-world")
    assert pub.status_code == 200
    assert pub.json()["slug"] == "hello-world"
    # SEO persists after publish (Type B keeps seo in generated html)
    seo_upd = client.patch(
        f"/posts/{post['id']}/seo",
        json={
            "seo_title": "SEO Title",
            "seo_description": "desc",
            "canonical_url": "/posts/hello-world/",
        },
        headers={"X-User-Role": "EDITOR"},
    )
    assert seo_upd.status_code == 200
    gen2 = client.post("/site/generate", headers={"X-User-Role": "EDITOR"}).json()
    page = client.get("/site/pages/posts/hello-world/index.html").json()
    assert "SEO Title" in page["html"]
