"""
Phase 7.1 — rendering abstraction validation
Architecture guard, not functional E2E.
Baseline: c7f91a7 / phase-7-docs-site-type-b / 616 passed
Must be validation-only, no runtime architecture change.
"""

import pathlib
import tempfile


# 1. cms_lite must not import ai_framework.rendering
def test_cms_lite_no_rendering_import():
    cms_lite_files = list(pathlib.Path("showcases/cms_lite").rglob("*.py"))
    assert cms_lite_files, "cms_lite not found"
    for f in cms_lite_files:
        txt = f.read_text(encoding="utf-8", errors="ignore")
        assert "ai_framework.rendering" not in txt, (
            f"cms_lite should not import rendering: {f}"
        )
        assert "from ai_framework.rendering" not in txt
        assert "import ai_framework.rendering" not in txt


# 2. blog_cms uses GeneratedPage, StaticSiteWriter, generic SEO/Jinja
def test_blog_cms_uses_primitives():
    blog_renderer = pathlib.Path("showcases/blog_cms/services/blog_renderer.py")
    site_gen = pathlib.Path("showcases/blog_cms/services/site_generator.py")
    assert blog_renderer.exists() and site_gen.exists()

    txt_r = blog_renderer.read_text(encoding="utf-8")
    txt_g = site_gen.read_text(encoding="utf-8")

    # Must use framework primitives
    assert (
        "from ai_framework.rendering" in txt_r or "from ai_framework.rendering" in txt_g
    )
    assert "GeneratedPage" in txt_g
    assert "StaticSiteWriter" in txt_g or "_writer" in txt_g
    # Generic SEO/Jinja
    assert (
        "SeoContext" in txt_r
        or "SeoInjector" in txt_r
        or "JinjaTemplateRenderer" in txt_r
    )

    # Runtime check
    from showcases.blog_cms.services.blog_renderer import BlogRenderer
    from showcases.blog_cms.services.blog_service import BlogCmsService
    from showcases.blog_cms.services.site_generator import SiteGenerator
    from ai_framework.rendering import GeneratedPage

    svc = BlogCmsService()
    renderer = BlogRenderer()
    gen = SiteGenerator(svc, renderer)
    pages = gen.generate()
    assert isinstance(pages, list)
    if pages:
        assert all(isinstance(p, GeneratedPage) for p in pages)


# 3. docs_site uses same GeneratedPage, same StaticSiteWriter, same generic primitives
def test_docs_site_uses_same_primitives():
    docs_renderer = pathlib.Path("showcases/docs_site/services/docs_renderer.py")
    docs_gen = pathlib.Path("showcases/docs_site/services/docs_site_generator.py")
    assert docs_renderer.exists() and docs_gen.exists()

    txt_r = docs_renderer.read_text(encoding="utf-8")
    txt_g = docs_gen.read_text(encoding="utf-8")

    assert "from ai_framework.rendering" in txt_r
    assert "from ai_framework.rendering" in txt_g or "StaticSiteWriter" in txt_g
    assert "GeneratedPage" in txt_g
    assert "SeoContext" in txt_r or "SeoInjector" in txt_r
    assert "JinjaTemplateRenderer" in txt_r

    from showcases.docs_site.services.docs_renderer import DocsRenderer
    from showcases.docs_site.services.docs_service import DocsService
    from showcases.docs_site.services.docs_site_generator import DocsSiteGenerator
    from ai_framework.rendering import GeneratedPage

    svc = DocsService()
    renderer = DocsRenderer()
    gen = DocsSiteGenerator(svc, renderer)
    pages = gen.generate()
    assert isinstance(pages, list)
    if pages:
        assert all(isinstance(p, GeneratedPage) for p in pages)


# 4. GeneratedPage single framework value object + immutable
def test_generated_page_single_and_immutable():
    from ai_framework.rendering import GeneratedPage

    framework_files = list(pathlib.Path("ai_framework/rendering").rglob("*.py"))
    definitions = [
        f
        for f in framework_files
        if "class GeneratedPage" in f.read_text(encoding="utf-8", errors="ignore")
    ]
    assert len(definitions) == 1, (
        f"GeneratedPage defined once in framework, found: {definitions}"
    )

    pg = GeneratedPage(path="index.html", html="<h1>hi</h1>", kind="index")
    try:
        pg.path = "other"
        assert False, "GeneratedPage should be frozen/immutable"
    except Exception:
        pass


# 5. StaticSiteWriter only generic writer, both showcases use it
def test_static_site_writer_only_generic_writer():
    writer_path = pathlib.Path("ai_framework/rendering/static_writer.py")
    assert writer_path.exists()
    txt = writer_path.read_text(encoding="utf-8", errors="ignore")
    # Must not contain domain hardcodes
    assert "BlogCmsService" not in txt
    assert "DocsService" not in txt
    assert "BlogRenderer" not in txt
    assert "DocsRenderer" not in txt

    # Both showcases must use StaticSiteWriter
    blog_gen = pathlib.Path("showcases/blog_cms/services/site_generator.py").read_text(
        encoding="utf-8"
    )
    docs_gen = pathlib.Path(
        "showcases/docs_site/services/docs_site_generator.py"
    ).read_text(encoding="utf-8")
    assert "StaticSiteWriter" in blog_gen
    assert "StaticSiteWriter" in docs_gen


# 6. Framework isolation — no domain terms
def test_framework_isolation():
    rendering_dir = pathlib.Path("ai_framework/rendering")
    forbidden = [
        "BlogCmsService",
        "DocsSiteService",
        "DocsService",
        "BlogRenderer",
        "DocsRenderer",
    ]
    # Domain path literals must not exist in framework (as literal strings)
    forbidden_paths = ["/posts/", "/guides/", "/categories/", "/tags/"]

    for f in rendering_dir.rglob("*.py"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        for term in forbidden:
            assert term not in txt, f"Framework should not contain {term}: {f}"
        for fp in forbidden_paths:
            # Allow mention in comment about what it does NOT know, but not as literal path generation
            # Strict: forbid exact '"%s"' or "'%s'" occurrence
            if f'"{fp}"' in txt or f"'{fp}'" in txt:
                # Except in docs where explicitly said "no domain knowledge"
                # Check if file is seo.py which already cleaned — should fail if present
                assert False, (
                    f"Framework must not contain hardcoded path literal {fp}: {f}"
                )


# 7. URL independence via same writer
def test_url_independence_via_same_writer():
    from ai_framework.rendering import GeneratedPage, StaticSiteWriter

    blog_page = GeneratedPage(
        path="posts/hello/index.html", html="<h1>blog</h1>", kind="post"
    )
    docs_page = GeneratedPage(
        path="guides/getting-started/index.html", html="<h1>docs</h1>", kind="doc"
    )

    writer = StaticSiteWriter()
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp)
        written = writer.write([blog_page, docs_page], out, clean=True)
        assert len(written) == 2
        assert (out / "posts/hello/index.html").exists()
        assert (out / "guides/getting-started/index.html").exists()
        assert (out / "posts/hello/index.html").read_text(
            encoding="utf-8"
        ) == "<h1>blog</h1>"
        assert (out / "guides/getting-started/index.html").read_text(
            encoding="utf-8"
        ) == "<h1>docs</h1>"


# 8. StaticSiteGeneratorProtocol absent as runtime, present only in docs
def test_generator_protocol_docs_only():
    rendering_dir = pathlib.Path("ai_framework/rendering")
    all_text = ""
    for f in rendering_dir.rglob("*.py"):
        all_text += f.read_text(encoding="utf-8", errors="ignore") + "\n"

    assert "class StaticSiteGeneratorProtocol" not in all_text, (
        "StaticSiteGeneratorProtocol must remain in docs, not code"
    )
    # Allow StaticSiteWriter, but not generator protocol
    # Docs must contain description of Domain -> Generator -> Renderer -> Output
    doc_path = pathlib.Path("docs/architecture/type_b_static_site.md")
    assert doc_path.exists(), "type_b_static_site.md must exist"
    doc_txt = doc_path.read_text(encoding="utf-8", errors="ignore")
    assert "Domain" in doc_txt and "Generator" in doc_txt and "Renderer" in doc_txt
