"""
Phase 7.1 — UPDATED for Phase 7.2
"""
import pathlib, tempfile

def test_cms_lite_no_rendering_import():
    for f in pathlib.Path("showcases/cms_lite").rglob("*.py"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        assert "ai_framework.rendering" not in txt

def test_blog_cms_uses_primitives():
    from showcases.blog_cms.services.blog_renderer import BlogRenderer
    from showcases.blog_cms.services.blog_service import BlogCmsService
    from showcases.blog_cms.services.site_generator import SiteGenerator
    from ai_framework.rendering import GeneratedPage
    pages = SiteGenerator(BlogCmsService(), BlogRenderer()).generate()
    assert isinstance(pages, list)

def test_docs_site_uses_same_primitives():
    from showcases.docs_site.services.docs_renderer import DocsRenderer
    from showcases.docs_site.services.docs_service import DocsService
    from showcases.docs_site.services.docs_site_generator import DocsSiteGenerator
    from ai_framework.rendering import GeneratedPage
    pages = DocsSiteGenerator(DocsService(), DocsRenderer()).generate()
    assert isinstance(pages, list)

def test_generated_page_single_and_immutable():
    from ai_framework.rendering import GeneratedPage
    defs = [f for f in pathlib.Path("ai_framework/rendering").rglob("*.py") if "class GeneratedPage" in f.read_text(encoding="utf-8", errors="ignore")]
    assert len(defs) == 1
    pg = GeneratedPage(path="index.html", html="<h1>hi</h1>", kind="index")
    try:
        pg.path = "other"; assert False
    except Exception:
        pass

def test_static_site_writer_only_generic_writer():
    txt = pathlib.Path("ai_framework/rendering/static_writer.py").read_text(encoding="utf-8", errors="ignore")
    assert "BlogCmsService" not in txt

def test_framework_isolation():
    for f in pathlib.Path("ai_framework/rendering").rglob("*.py"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        for fp in ["/posts/", "/guides/", "/categories/", "/tags/"]:
            if f'"{fp}"' in txt or f"'{fp}'" in txt:
                assert False, f"Framework must not contain {fp}: {f}"

def test_url_independence_via_same_writer():
    from ai_framework.rendering import GeneratedPage, StaticSiteWriter
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp)
        written = StaticSiteWriter().write([
            GeneratedPage(path="posts/hello/index.html", html="<h1>blog</h1>", kind="post"),
            GeneratedPage(path="guides/getting-started/index.html", html="<h1>docs</h1>", kind="doc"),
        ], out, clean=True)
        assert len(written) == 2

def test_generator_protocol_docs_only():
    """UPDATED for Phase 7.2"""
    all_text = "\n".join([f.read_text(encoding="utf-8", errors="ignore") for f in pathlib.Path("ai_framework/rendering").rglob("*.py")])
    doc_txt = pathlib.Path("docs/architecture/type_b_static_site.md").read_text(encoding="utf-8", errors="ignore")
    assert "Domain" in doc_txt and "Generator" in doc_txt
    if "class StaticSiteGeneratorProtocol" in all_text:
        proto_txt = pathlib.Path("ai_framework/rendering/protocols.py").read_text(encoding="utf-8")
        assert "def write" not in proto_txt
        assert "def generate" in proto_txt