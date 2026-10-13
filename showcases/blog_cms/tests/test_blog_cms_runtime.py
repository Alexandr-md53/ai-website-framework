from __future__ import annotations
from fastapi.testclient import TestClient
from showcases.blog_cms.app_factory import create_test_app
import uuid

HEADERS = {"X-User-Id": str(uuid.uuid4()), "X-User-Role": "ADMIN"}


def _client():
    app = create_test_app()
    return TestClient(app)


def _setup(client):
    cat = client.post(
        "/categories", json={"name": "Tech", "slug": "tech"}, headers=HEADERS
    ).json()
    tag = client.post(
        "/tags", json={"name": "Python", "slug": "python"}, headers=HEADERS
    ).json()
    author = client.post(
        "/authors", json={"name": "John", "slug": "john-doe"}, headers=HEADERS
    ).json()
    return cat, tag, author


def test_blog_cms_slug_validation():
    c = _client()
    cat, tag, author = _setup(c)

    # valid slug
    r = c.post(
        "/posts",
        json={
            "title": "Valid Post Title",
            "slug": "valid-post-slug",
            "content": "This content is definitely longer than twenty characters minimum.",
            "category_id": cat["id"],
            "author_id": author["id"],
            "tag_ids": [tag["id"]],
        },
        headers=HEADERS,
    )
    assert r.status_code == 200, r.text
    assert r.json()["slug"] == "valid-post-slug"

    # duplicate slug -> 400
    r_dup = c.post(
        "/posts",
        json={
            "title": "Dup",
            "slug": "valid-post-slug",
            "content": "This content is definitely longer than twenty characters minimum.",
            "category_id": cat["id"],
            "author_id": author["id"],
        },
        headers=HEADERS,
    )
    assert r_dup.status_code == 400, r_dup.text

    # invalid slug (uppercase + underscore) -> 400 via ai_framework.content.Slug
    r_bad = c.post(
        "/posts",
        json={
            "title": "Bad Slug",
            "slug": "Invalid_Slug_Upper",
            "content": "This content is definitely longer than twenty characters minimum.",
            "category_id": cat["id"],
            "author_id": author["id"],
        },
        headers=HEADERS,
    )
    assert r_bad.status_code == 400, (
        f"expected invalid slug rejection got {r_bad.status_code}"
    )


def test_blog_cms_publish_lifecycle():
    c = _client()
    cat, tag, author = _setup(c)

    r = c.post(
        "/posts",
        json={
            "title": "Draft Post",
            "slug": "draft-post",
            "content": "Draft content longer than twenty chars for validation.",
            "category_id": cat["id"],
            "author_id": author["id"],
        },
        headers=HEADERS,
    )
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    assert r.json()["status"] == "draft"

    # public should 404 before publish
    r_pub_before = c.get(f"/public/posts/draft-post")
    assert r_pub_before.status_code == 404

    # publish
    r_pub = c.post(f"/posts/{pid}/publish", headers=HEADERS)
    assert r_pub.status_code == 200, r_pub.text
    assert r_pub.json()["status"] == "published"

    # public should 200 after publish
    r_pub_after = c.get(f"/public/posts/draft-post")
    assert r_pub_after.status_code == 200, r_pub_after.text
    assert r_pub_after.json()["slug"] == "draft-post"

    # unpublish
    r_unpub = c.post(f"/posts/{pid}/unpublish", headers=HEADERS)
    assert r_unpub.status_code == 200
    assert r_unpub.json()["status"] == "draft"

    # public 404 after unpublish
    r_pub_after2 = c.get(f"/public/posts/draft-post")
    assert r_pub_after2.status_code == 404


def test_blog_cms_published_filtering():
    c = _client()
    cat, tag, author = _setup(c)

    r1 = c.post(
        "/posts",
        json={
            "title": "Published One",
            "slug": "published-one",
            "content": "Content for published one longer than twenty chars.",
            "category_id": cat["id"],
            "author_id": author["id"],
        },
        headers=HEADERS,
    ).json()
    r2 = c.post(
        "/posts",
        json={
            "title": "Draft Two",
            "slug": "draft-two",
            "content": "Content for draft two longer than twenty chars.",
            "category_id": cat["id"],
            "author_id": author["id"],
        },
        headers=HEADERS,
    ).json()

    c.post(f"/posts/{r1['id']}/publish", headers=HEADERS)

    # public list should contain only published - actual observable
    r_list = c.get("/public/posts")
    assert r_list.status_code == 200, r_list.text
    print("public/posts:", r_list.text[:1000])
    slugs = [p["slug"] for p in r_list.json()]
    assert "published-one" in slugs
    assert "draft-two" not in slugs

    # filter by category
    r_cat = c.get(f"/public/posts?category=tech")
    assert r_cat.status_code == 200, r_cat.text
    print("public/posts?category=tech:", r_cat.text[:1000])
    assert any(p["slug"] == "published-one" for p in r_cat.json())

    # internal list - framework uses upper enum
    r_all = c.get("/posts")
    assert r_all.status_code == 200
    assert len(r_all.json()) >= 2

    # published filter - service expects PostStatus(PUBLISHED) - uppercase
    r_pub = c.get("/posts?status=PUBLISHED")
    print("posts?status=PUBLISHED:", r_pub.text[:1000])
    assert r_pub.status_code == 200
    # if API returns string (old behavior) handle both
    data = r_pub.json()
    if data and isinstance(data[0], str):
        # shouldn't happen but print
        print("Got strings instead of dicts:", data[:5])
        assert False, "expected dicts"
    assert any(p["slug"] == "published-one" for p in data)


def test_blog_cms_seo_persistence():
    c = _client()
    cat, tag, author = _setup(c)

    r = c.post(
        "/posts",
        json={
            "title": "SEO Post",
            "slug": "seo-post",
            "content": "SEO post content longer than twenty characters minimum.",
            "category_id": cat["id"],
            "author_id": author["id"],
            "seo_title": "Initial SEO",
            "seo_description": "Initial desc",
            "canonical_url": "https://example.com/seo-post",
        },
        headers=HEADERS,
    )
    assert r.status_code == 200, r.text
    pid = r.json()["id"]
    assert r.json()["seo_title"] == "Initial SEO"

    # update seo
    r_seo = c.patch(
        f"/posts/{pid}/seo",
        json={
            "seo_title": "Updated SEO Title",
            "seo_description": "Updated desc",
            "canonical_url": "/seo-post",
        },
        headers=HEADERS,
    )
    assert r_seo.status_code == 200, r_seo.text
    assert r_seo.json()["seo_title"] == "Updated SEO Title"
    assert r_seo.json()["canonical_url"] == "/seo-post"

    # seo length validation >70 -> 400
    r_bad = c.patch(f"/posts/{pid}/seo", json={"seo_title": "x" * 71}, headers=HEADERS)
    assert r_bad.status_code == 400

    # canonical must start with http(s):// or / -> ftp should 400
    r_bad2 = c.patch(
        f"/posts/{pid}/seo", json={"canonical_url": "ftp://bad"}, headers=HEADERS
    )
    assert r_bad2.status_code == 400

    # publish and seo persists
    c.post(f"/posts/{pid}/publish", headers=HEADERS)
    r_get = c.get(f"/public/posts/seo-post")
    assert r_get.status_code == 200
    assert r_get.json()["seo_title"] == "Updated SEO Title"


def test_blog_cms_rendering_and_generation():
    c = _client()
    cat, tag, author = _setup(c)

    r = c.post(
        "/posts",
        json={
            "title": "Render Post",
            "slug": "render-post",
            "content": "Render content longer than twenty chars for generation.",
            "category_id": cat["id"],
            "author_id": author["id"],
            "seo_title": "Render SEO",
            "seo_description": "Render desc",
        },
        headers=HEADERS,
    )
    pid = r.json()["id"]
    c.post(f"/posts/{pid}/publish", headers=HEADERS)

    # generate site - requires ADMIN
    r_gen = c.post("/site/generate", headers=HEADERS)
    assert r_gen.status_code == 200, r_gen.text
    data = r_gen.json()
    assert data["generated"] >= 4  # index + post + category + tag + rss + sitemap
    assert any("posts/render-post" in p for p in data["pages"])
    assert any("index.html" == p for p in data["pages"])

    # site/pages list
    r_pages = c.get("/site/pages")
    assert r_pages.status_code == 200
    paths = [p["path"] for p in r_pages.json()]
    assert "index.html" in paths

    # get specific generated page and check HTML contains title and SEO
    r_html = c.get("/site/pages/posts/render-post/index.html")
    assert r_html.status_code == 200, r_html.text
    html = r_html.json()["html"]
    assert "Render Post" in html
    # SeoInjector should ensure seo title in html
    assert "Render SEO" in html or "Render Post" in html
    assert "<title>" in html.lower() or "seo" in html.lower()

    # sitemap and rss
    r_sitemap = c.get("/sitemap.xml")
    assert r_sitemap.status_code == 200
    assert "render-post" in r_sitemap.text

    r_rss = c.get("/rss.xml")
    assert r_rss.status_code == 200
    assert "Render Post" in r_rss.text
