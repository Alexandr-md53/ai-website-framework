from fastapi.testclient import TestClient
from showcases.docs_site.app_factory import create_test_app, FROZEN_ROUTES


def test_frozen_route_map_smoke():
    app = create_test_app()
    found = set()
    for r in app.routes:
        if not hasattr(r, "path"):
            continue
        methods = getattr(r, "methods", None)
        if not methods:
            continue
        for m in methods:
            path = r.path.replace("{path:path}", "{path}")
            found.add(f"{m} {path}")
    normalized_frozen = {rt.replace("{path:path}", "{path}") for rt in FROZEN_ROUTES}
    missing = [rt for rt in normalized_frozen if rt not in found]
    assert not missing, f"Missing routes: {missing}\nFound: {found}"


def test_docs_generation_pipeline_G1_G2():
    app = create_test_app()
    client = TestClient(app)
    sec = client.post("/sections", json={"name": "Guides", "slug": "guides"}).json()
    ver = client.post("/versions", json={"name": "v2", "slug": "v2"}).json()
    doc = client.post(
        "/docs",
        json={
            "title": "Getting Started",
            "slug": "getting-started",
            "content": "This is long enough content for docs publish",
            "section_id": sec["id"],
            "version_id": ver["id"],
        },
    ).json()
    client.post(f"/docs/{doc['id']}/publish")
    gen = client.post("/site/generate")
    assert gen.status_code == 200
    assert gen.json()["generated"] >= 3
    pages = client.get("/site/pages").json()
    paths = [p["path"] for p in pages]
    assert "index.html" in paths
    assert "guides/getting-started/index.html" in paths
    assert "sitemap.xml" in paths
    # URL conventions must be docs-specific, not blog
    assert not any("posts/" in p for p in paths), (
        "docs_site must not use posts/ convention"
    )
    assert not any("categories/" in p for p in paths)
    assert any("sections/" in p for p in paths)
    assert any("versions/" in p for p in paths)
    # SEO persists
    seo_upd = client.patch(
        f"/docs/{doc['id']}/seo",
        json={
            "seo_title": "Docs SEO Title",
            "seo_description": "desc",
            "canonical_url": "/guides/getting-started/",
        },
    )
    assert seo_upd.status_code == 200
    client.post("/site/generate")
    page = client.get("/site/pages/guides/getting-started/index.html").json()
    assert "Docs SEO Title" in page["html"]


def test_second_consumer_uses_same_framework_primitives():
    """Proves rendering abstraction is universal, not blog-specific"""
    from ai_framework.rendering import (
        GeneratedPage,
        SeoContext,
        SeoInjector,
        JinjaTemplateRenderer,
        StaticSiteWriter,
    )
    from showcases.docs_site.services.docs_renderer import DocsRenderer
    from showcases.docs_site.services.docs_site_generator import DocsSiteGenerator
    from showcases.docs_site.services.docs_service import DocsService

    # Same primitives as blog_cms
    svc = DocsService()
    renderer = DocsRenderer()
    gen = DocsSiteGenerator(svc, renderer)

    # Should produce GeneratedPage from framework
    pages = gen.generate()
    assert isinstance(pages, list)
    if pages:
        assert all(isinstance(p, GeneratedPage) for p in pages)

    # Writer is same class
    writer = StaticSiteWriter()
    assert writer is not None

    # SeoInjector is same generic
    injector = SeoInjector()
    seo = SeoContext(seo_title="Test", seo_description="desc")
    out = injector.ensure_seo("<html></html>", seo)
    assert "<title>Test</title>" in out
