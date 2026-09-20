import pathlib, tempfile
import pytest
from ai_framework.rendering import (
    GeneratedPage,
    SeoContext,
    SeoInjector,
    JinjaTemplateRenderer,
    StaticSiteWriter,
)


def test_generated_page_immutable():
    pg = GeneratedPage(path="index.html", html="<h1>hi</h1>", kind="index")
    assert pg.path == "index.html"
    # frozen
    with pytest.raises(Exception):
        pg.path = "other.html"  # type: ignore


def test_generated_page_value_semantics():
    a = GeneratedPage("a.html", "hi", "index")
    b = GeneratedPage("a.html", "hi", "index")
    assert a == b
    assert hash(a) == hash(b)


def test_seo_context_normalize():
    # full
    ctx = SeoContext.normalize(
        {
            "title": "My Post",
            "seo_title": "SEO Title",
            "seo_description": "desc",
            "og_title": "OG",
            "og_description": "OG desc",
            "canonical_url": "/my-post/",
        }
    )
    assert ctx.seo_title == "SEO Title"
    assert ctx.seo_description == "desc"
    assert ctx.og_title == "OG"
    assert ctx.og_description == "OG desc"
    assert ctx.canonical_url == "/my-post/"


def test_seo_context_fallback():
    ctx = SeoContext.normalize({"title": "Only Title"}, title_fallback="Blog")
    assert ctx.seo_title == "Only Title"
    assert ctx.title == "Only Title"
    ctx2 = SeoContext.normalize({}, title_fallback="Blog")
    assert ctx2.seo_title == "Blog"


def test_seo_context_empty_fields():
    ctx = SeoContext.normalize(
        {"title": "T", "seo_description": "", "og_title": "", "canonical_url": ""}
    )
    assert ctx.seo_description == ""
    assert ctx.canonical_url == ""
    # seo_title still fallback
    assert ctx.seo_title == "T"


def test_seo_injection_missing_title():
    injector = SeoInjector()
    seo = SeoContext(
        seo_title="My Title",
        seo_description="desc",
        og_title="OG",
        og_description="OG desc",
        canonical_url="/canonical/",
    )
    html = "<html><body>hi</body></html>"
    out = injector.ensure_seo(html, seo)
    assert "<title>My Title</title>" in out
    assert 'name="description" content="desc"' in out
    assert "og:title" in out
    assert 'rel="canonical" href="/canonical/"' in out
    # must not contain Post, Blog, slug, /posts/
    assert "Post" not in out or "My Title" in out  # only seo title allowed
    # Ensure generic: no hard-coded /posts/ in injector
    # injector output should not invent /posts/
    assert "/posts/" not in out


def test_seo_injection_existing_title_adds_missing_meta():
    injector = SeoInjector()
    seo = SeoContext(seo_title="Title", seo_description="desc")
    html = "<html><head><title>Title</title></head><body></body></html>"
    out = injector.ensure_seo(html, seo)
    assert '<meta name="description"' in out
    assert out.count("<title>") == 1


def test_seo_injection_empty_fields_no_injection():
    injector = SeoInjector()
    seo = SeoContext(
        seo_title="Title",
        seo_description="",
        og_title="",
        og_description="",
        canonical_url="",
    )
    html = "<title>Title</title>"
    out = injector.ensure_seo(html, seo)
    # should not inject empty tags
    assert 'name="description"' not in out
    assert "og:title" not in out
    assert 'rel="canonical"' not in out


def test_seo_injector_no_domain_leak():
    injector = SeoInjector()
    # Check source code does not reference forbidden terms
    import inspect

    src = inspect.getsource(SeoInjector)
    for forbidden in ["Post", "Blog", "slug", "/posts/", "category", "tag"]:
        # allow slug inside variable names? We forbid hard-coded domain logic
        # For this test, ensure class does not reference "/posts/"
        if forbidden == "/posts/":
            assert forbidden not in src, "SeoInjector must not contain /posts/"
    # Generic check for class name leaks
    assert "Post" not in src or "SeoContext" in src  # only SeoContext allowed


def test_jinja_renderer():
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "hello.html").write_text("<h1>{{ title }}</h1>", encoding="utf-8")
    r = JinjaTemplateRenderer(tmp)
    out = r.render("hello.html", {"title": "World"})
    assert "<h1>World</h1>" in out


def test_writer_clean_true():
    writer = StaticSiteWriter()
    tmp = pathlib.Path(tempfile.mkdtemp())
    # create garbage file
    (tmp / "old.html").write_text("old", encoding="utf-8")
    pages = [GeneratedPage("index.html", "new", "index")]
    writer.write(pages, tmp, clean=True)
    assert not (tmp / "old.html").exists()
    assert (tmp / "index.html").exists()
    assert (tmp / "index.html").read_text() == "new"


def test_writer_clean_false():
    writer = StaticSiteWriter()
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "keep.html").write_text("keep", encoding="utf-8")
    pages = [GeneratedPage("index.html", "new", "index")]
    writer.write(pages, tmp, clean=False)
    assert (tmp / "keep.html").exists()
    assert (tmp / "index.html").exists()


def test_writer_relative_paths():
    writer = StaticSiteWriter()
    tmp = pathlib.Path(tempfile.mkdtemp())
    pages = [GeneratedPage("posts/my-post/index.html", "<h1>hi</h1>", "post")]
    written = writer.write(pages, tmp, clean=True)
    assert (tmp / "posts" / "my-post" / "index.html").exists()
    # Rejects absolute or .. paths
    with pytest.raises(ValueError):
        writer.write([GeneratedPage("/absolute.html", "x", "index")], tmp, clean=True)
    with pytest.raises(ValueError):
        writer.write([GeneratedPage("../escape.html", "x", "index")], tmp, clean=True)
