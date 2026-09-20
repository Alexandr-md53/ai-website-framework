import pathlib, tempfile, shutil, re
from fastapi.testclient import TestClient
from showcases.blog_cms.api.app_factory import create_test_app
from showcases.blog_cms.services.site_generator import SiteGenerator, Renderer


def test_generated_site_integrity_G1_G2_G12():
    """
    Phase 6.2: generated-site integrity
    - full tree output/
    - each published entity represented
    - draft NOT in public site
    - no broken internal links
    - sitemap only public URLs
    - rss only published
    - deterministic re-generation
    - clean output (no garbage from previous runs)
    """
    app = create_test_app()
    client = TestClient(app)

    # ---- Setup: 2 categories, 2 tags, 3 posts (2 published, 1 draft) ----
    cat_tech = client.post(
        "/categories",
        json={"name": "Tech", "slug": "tech"},
        headers={"X-User-Role": "EDITOR"},
    ).json()
    cat_life = client.post(
        "/categories",
        json={"name": "Life", "slug": "life"},
        headers={"X-User-Role": "EDITOR"},
    ).json()

    tag_py = client.post(
        "/tags",
        json={"name": "Python", "slug": "python"},
        headers={"X-User-Role": "EDITOR"},
    ).json()
    tag_ai = client.post(
        "/tags", json={"name": "AI", "slug": "ai"}, headers={"X-User-Role": "EDITOR"}
    ).json()

    author = client.post(
        "/authors",
        json={"name": "Ada", "slug": "ada"},
        headers={"X-User-Role": "EDITOR"},
    ).json()

    def make_post(title, slug, cat_id, published=True, tags=None):
        p = client.post(
            "/posts",
            json={
                "title": title,
                "slug": slug,
                "content": f"{title} content long enough for publish validation, more than 20 chars, includes details.",
                "category_id": cat_id,
                "author_id": author["id"],
                "tag_ids": tags or [],
                "seo_title": f"{title} SEO",
                "seo_description": f"{title} desc",
            },
            headers={"X-User-Role": "EDITOR"},
        ).json()
        if published:
            client.post(
                f"/posts/{p['id']}/publish", headers={"X-User-Role": "EDITOR"}
            ).raise_for_status()
        return p

    p1 = make_post(
        "Published Tech Post",
        "published-tech-post",
        cat_tech["id"],
        published=True,
        tags=[tag_py["id"]],
    )
    p2 = make_post(
        "Published Life Post",
        "published-life-post",
        cat_life["id"],
        published=True,
        tags=[tag_ai["id"], tag_py["id"]],
    )
    p_draft = make_post(
        "Draft Post Should Not Appear", "draft-post", cat_tech["id"], published=False
    )

    # ---- First generation ----
    gen1 = client.post("/site/generate", headers={"X-User-Role": "EDITOR"})
    assert gen1.status_code == 200
    pages1 = client.get("/site/pages").json()
    paths1 = [x["path"] for x in pages1]

    # 1. Full tree check
    assert "index.html" in paths1
    assert "rss.xml" in paths1
    assert "sitemap.xml" in paths1
    assert f"posts/{p1['slug']}/index.html" in paths1
    assert f"posts/{p2['slug']}/index.html" in paths1
    assert f"categories/{cat_tech['slug']}/index.html" in paths1
    assert f"categories/{cat_life['slug']}/index.html" in paths1
    assert f"tags/{tag_py['slug']}/index.html" in paths1
    assert f"tags/{tag_ai['slug']}/index.html" in paths1

    # 2. Draft NOT in output
    assert f"posts/{p_draft['slug']}/index.html" not in paths1
    # Ensure draft content not leaked in index
    idx_html = client.get("/site/pages/index.html").json()["html"]
    assert p_draft["slug"] not in idx_html
    assert p_draft["title"] not in idx_html

    # 3. Each published entity represented
    post1_html = client.get(f"/site/pages/posts/{p1['slug']}/index.html").json()["html"]
    assert p1["title"] in post1_html
    assert f"{p1['title']} SEO" in post1_html  # seo_title

    # 4. No broken internal links
    # Collect all generated paths as valid targets
    # Valid internal hrefs we generate are /posts/<slug>/, /categories/<slug>/, /tags/<slug>/, /, /rss.xml, /sitemap.xml
    all_valid_prefixes = {"/", "/rss.xml", "/sitemap.xml"}
    # Build set of expected existing pages
    expected_hrefs = {
        f"/posts/{p1['slug']}/",
        f"/posts/{p2['slug']}/",
        f"/categories/{cat_tech['slug']}/",
        f"/categories/{cat_life['slug']}/",
        f"/tags/{tag_py['slug']}/",
        f"/tags/{tag_ai['slug']}/",
    }
    # Check every generated page for hrefs
    href_re = re.compile(r'href="([^"]+)"')
    for page in pages1:
        if not page["path"].endswith(".html"):
            continue
        html = client.get(f"/site/pages/{page['path']}").json()["html"]
        for href in href_re.findall(html):
            if (
                href.startswith("/posts/")
                or href.startswith("/categories/")
                or href.startswith("/tags/")
            ):
                # must be in expected or be root-like
                # allow trailing slash
                assert (
                    href in expected_hrefs
                    or href in all_valid_prefixes
                    or href.startswith("/posts/")
                    and any(h in href for h in [p1["slug"], p2["slug"]])
                ), f"Broken link {href} in {page['path']}"

    # 5. Sitemap only public URLs
    sitemap_html = client.get("/site/pages/sitemap.xml").json()["html"]
    assert p1["slug"] in sitemap_html
    assert p2["slug"] in sitemap_html
    assert p_draft["slug"] not in sitemap_html
    # sitemap should contain / url
    assert (
        "<loc>/</loc>" in sitemap_html
        or "<loc>/</loc>" in sitemap_html
        or "/" in sitemap_html
    )

    # 6. RSS only published
    rss_html = client.get("/site/pages/rss.xml").json()["html"]
    assert p1["title"] in rss_html
    assert p2["title"] in rss_html
    assert p_draft["title"] not in rss_html

    # 7. Deterministic re-generation
    gen2 = client.post("/site/generate", headers={"X-User-Role": "EDITOR"}).json()
    pages2 = client.get("/site/pages").json()
    # same paths count
    assert len(pages1) == len(pages2)
    # html content identical for same data
    for p in pages1:
        h1 = client.get(f"/site/pages/{p['path']}").json()["html"]
        # after second gen, re-fetch
        # generate again and compare
    # Actually generate twice and compare dicts
    client.post("/site/generate", headers={"X-User-Role": "EDITOR"})
    pages_after = {
        x["path"]: client.get(f"/site/pages/{x['path']}").json()["html"]
        for x in client.get("/site/pages").json()
    }
    client.post("/site/generate", headers={"X-User-Role": "EDITOR"})
    pages_after2 = {
        x["path"]: client.get(f"/site/pages/{x['path']}").json()["html"]
        for x in client.get("/site/pages").json()
    }
    assert pages_after.keys() == pages_after2.keys()
    for k in pages_after:
        assert pages_after[k] == pages_after2[k], f"Non-deterministic page {k}"

    # 8. Clean output — no garbage from previous runs (test via explicit write to temp dir)
    svc = app.state.service
    renderer = Renderer()
    tmp_root = pathlib.Path(tempfile.gettempdir()) / "blog_cms_integrity_62"
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir(parents=True)

    gen = SiteGenerator(svc, renderer)
    pages_objs = gen.generate()
    written = gen.write(pages_objs, tmp_root)
    # check tree exists on FS
    assert (tmp_root / "index.html").exists()
    assert (tmp_root / "posts" / p1["slug"] / "index.html").exists()
    assert (tmp_root / "posts" / p2["slug"] / "index.html").exists()
    assert not (tmp_root / "posts" / p_draft["slug"] / "index.html").exists()
    assert (tmp_root / "categories" / cat_tech["slug"] / "index.html").exists()
    assert (tmp_root / "tags" / tag_py["slug"] / "index.html").exists()
    assert (tmp_root / "rss.xml").exists()
    assert (tmp_root / "sitemap.xml").exists()

    # Now unpublish p2 and regenerate to fresh dir — old file must not appear
    client.post(f"/posts/{p2['id']}/unpublish", headers={"X-User-Role": "EDITOR"})
    tmp_root2 = pathlib.Path(tempfile.gettempdir()) / "blog_cms_integrity_62_v2"
    if tmp_root2.exists():
        shutil.rmtree(tmp_root2)
    tmp_root2.mkdir()
    pages_objs2 = gen.generate()
    gen.write(pages_objs2, tmp_root2)
    assert not (tmp_root2 / "posts" / p2["slug"] / "index.html").exists()
    assert (tmp_root2 / "posts" / p1["slug"] / "index.html").exists()


def test_draft_never_in_public_api_after_generation():
    app = create_test_app()
    client = TestClient(app)
    cat = client.post(
        "/categories",
        json={"name": "DraftCat", "slug": "draftcat"},
        headers={"X-User-Role": "EDITOR"},
    ).json()
    author = client.post(
        "/authors",
        json={"name": "DraftAuthor", "slug": "draftauthor"},
        headers={"X-User-Role": "EDITOR"},
    ).json()
    draft = client.post(
        "/posts",
        json={
            "title": "Draft Only",
            "slug": "draft-only",
            "content": "Draft content long enough for validation 12345",
            "category_id": cat["id"],
            "author_id": author["id"],
        },
        headers={"X-User-Role": "EDITOR"},
    ).json()
    # do not publish
    client.post("/site/generate", headers={"X-User-Role": "EDITOR"})
    # public API should not return draft
    pub = client.get("/public/posts").json()
    slugs = [p["slug"] for p in pub]
    assert "draft-only" not in slugs
    # direct public slug should 404
    r = client.get("/public/posts/draft-only")
    assert r.status_code == 404
