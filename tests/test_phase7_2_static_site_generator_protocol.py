"""
Phase 7.2 — StaticSiteGeneratorProtocol + duplicate fail-fast
"""

import pathlib
import tempfile


def test_protocol_exists_minimal():
    proto_path = pathlib.Path("ai_framework/rendering/protocols.py")
    assert proto_path.exists()
    txt = proto_path.read_text(encoding="utf-8")
    assert "class StaticSiteGeneratorProtocol" in txt
    assert "def generate" in txt
    assert "GeneratedPage" in txt
    lines = [l for l in txt.splitlines() if "def write" in l]
    assert len(lines) == 0, f"Protocol must not contain write(): {lines}"


def test_generators_structural():
    from showcases.blog_cms.services.site_generator import SiteGenerator as BlogGen
    from showcases.docs_site.services.docs_site_generator import DocsSiteGenerator

    assert hasattr(BlogGen, "generate")
    assert hasattr(DocsSiteGenerator, "generate")
    from showcases.blog_cms.services.blog_renderer import BlogRenderer
    from showcases.blog_cms.services.blog_service import BlogCmsService
    from showcases.docs_site.services.docs_renderer import DocsRenderer
    from showcases.docs_site.services.docs_service import DocsService
    from ai_framework.rendering import GeneratedPage

    blog_pages = BlogGen(BlogCmsService(), BlogRenderer()).generate()
    docs_pages = DocsSiteGenerator(DocsService(), DocsRenderer()).generate()
    assert isinstance(blog_pages, list)
    assert isinstance(docs_pages, list)
    if blog_pages:
        assert all(isinstance(p, GeneratedPage) for p in blog_pages)
    if docs_pages:
        assert all(isinstance(p, GeneratedPage) for p in docs_pages)


def test_writer_duplicate_fail_fast():
    from ai_framework.rendering import GeneratedPage, StaticSiteWriter

    writer = StaticSiteWriter()
    dup = [
        GeneratedPage(path="posts/hello/index.html", html="<h1>a</h1>", kind="post"),
        GeneratedPage(path="posts/hello/index.html", html="<h1>b</h1>", kind="post"),
    ]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            writer.write(dup, pathlib.Path(tmp), clean=True)
        assert False, "must raise on duplicate"
    except ValueError as e:
        assert "Duplicate" in str(e) or "duplicate" in str(e).lower()


def test_writer_allows_two_different_paths():
    from ai_framework.rendering import GeneratedPage, StaticSiteWriter

    writer = StaticSiteWriter()
    pages = [
        GeneratedPage(path="posts/hello/index.html", html="<h1>blog</h1>", kind="post"),
        GeneratedPage(
            path="guides/getting-started/index.html", html="<h1>docs</h1>", kind="doc"
        ),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp)
        written = writer.write(pages, out, clean=True)
        assert len(written) == 2
        assert (out / "posts/hello/index.html").exists()
        assert (out / "guides/getting-started/index.html").exists()


def test_docs_updated():
    txt = pathlib.Path("docs/architecture/type_b_static_site.md").read_text(
        encoding="utf-8"
    )
    assert "Purity" in txt or "pure" in txt.lower()
    assert (
        "Determinism" in txt
        or "deterministic" in txt.lower()
        or "Same domain state" in txt
    )
    assert "Unique" in txt or "duplicate" in txt.lower()
    assert "Empty" in txt or "empty" in txt.lower()
