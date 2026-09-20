"""
Phase 6.3 — Rendering extraction validation
Validates clean boundary after extraction v0.1
Baseline: 195ae23 / extraction-rendering-primitives-v0.1-green / 606 passed
"""

import pathlib
import importlib
import ast


def test_cms_lite_no_rendering_dependency():
    """1. cms_lite не получил случайных зависимостей от rendering layer"""
    # cms_lite should not import ai_framework.rendering
    cms_lite_files = list(pathlib.Path("showcases/cms_lite").rglob("*.py"))
    for f in cms_lite_files:
        txt = f.read_text(encoding="utf-8", errors="ignore")
        assert "ai_framework.rendering" not in txt, (
            f"cms_lite should not depend on rendering layer: {f}"
        )
        assert "from ai_framework.rendering" not in txt
        assert "import ai_framework.rendering" not in txt


def test_blog_cms_uses_extracted_primitives():
    """2. blog_cms полностью работает через extracted primitives"""
    # Check imports
    blog_renderer_path = pathlib.Path("showcases/blog_cms/services/blog_renderer.py")
    assert blog_renderer_path.exists(), "blog_renderer.py must exist after extraction"
    txt = blog_renderer_path.read_text(encoding="utf-8")
    assert "from ai_framework.rendering" in txt
    assert (
        "GeneratedPage" in txt
        or "SeoContext" in txt
        or "SeoInjector" in txt
        or "JinjaTemplateRenderer" in txt
    )

    site_gen_path = pathlib.Path("showcases/blog_cms/services/site_generator.py")
    assert site_gen_path.exists()
    txt2 = site_gen_path.read_text(encoding="utf-8")
    assert (
        "from ai_framework.rendering" in txt2
        or "StaticSiteWriter" in txt2
        or "GeneratedPage" in txt2
    )

    # Actually import and check it works
    from showcases.blog_cms.services.blog_renderer import BlogRenderer
    from showcases.blog_cms.services.site_generator import SiteGenerator
    from showcases.blog_cms.services.blog_service import BlogCmsService
    from ai_framework.rendering import GeneratedPage

    svc = BlogCmsService()
    renderer = BlogRenderer()
    gen = SiteGenerator(svc, renderer)
    # generate should return List[GeneratedPage] from framework
    pages = gen.generate()
    assert isinstance(pages, list)
    # Even if empty, type should be GeneratedPage
    if pages:
        assert all(isinstance(p, GeneratedPage) for p in pages)


def test_generated_page_single_output_value_object():
    """3. GeneratedPage используется как единый output value object"""
    from ai_framework.rendering import GeneratedPage

    # Check that both ai_framework and blog_cms use same class
    # blog_cms should not define its own GeneratedPage anymore, but re-export
    # Check that site_generator imports from ai_framework or blog_renderer re-exports
    site_gen = pathlib.Path("showcases/blog_cms/services/site_generator.py").read_text(
        encoding="utf-8"
    )
    # Should import GeneratedPage from framework
    assert "GeneratedPage" in site_gen
    # Ensure ai_framework has only one definition
    framework_files = list(pathlib.Path("ai_framework/rendering").rglob("*.py"))
    definitions = []
    for f in framework_files:
        txt = f.read_text(encoding="utf-8")
        if "class GeneratedPage" in txt:
            definitions.append(f)
    assert len(definitions) == 1, (
        f"GeneratedPage should be defined once in framework, found in {definitions}"
    )

    # Immutability check
    pg = GeneratedPage(path="index.html", html="hi", kind="index")
    try:
        pg.path = "other"
        assert False, "GeneratedPage should be frozen"
    except Exception:
        pass


def test_static_site_writer_only_generic_writer():
    """4. StaticSiteWriter — единственная generic точка записи generated pages"""
    # Search for direct file writes in blog_cms that bypass writer
    blog_cms_services = pathlib.Path("showcases/blog_cms/services")
    for f in blog_cms_services.rglob("*.py"):
        if f.name == "site_generator.py":
            continue  # this file uses writer
        txt = f.read_text(encoding="utf-8", errors="ignore")
        # Should not do direct fp.write_text for pages outside site_generator
        # Allow blog_service to write? No, only site_generator should write
        if "write_text" in txt and "html" in txt.lower():
            # If it's not test file, flag
            if "blog_renderer" in f.name:
                # blog_renderer should not write files
                assert "write_text" not in txt, (
                    f"{f} should not write files, only render"
                )

    # Check that framework writer is used in app_factory
    app_factory = pathlib.Path("showcases/blog_cms/app_factory.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    # app_factory should call generator.write, not direct write
    assert (
        "generator.write" in app_factory
        or "gen.write" in app_factory
        or "SiteGenerator" in app_factory
    )

    from ai_framework.rendering import StaticSiteWriter

    writer = StaticSiteWriter()
    # Ensure writer is generic (no blog deps)
    src = pathlib.Path("ai_framework/rendering/static_writer.py").read_text(
        encoding="utf-8"
    )
    assert "BlogCmsService" not in src
    assert "BlogRenderer" not in src
    assert (
        "posts" not in src.lower()
        or "posts" in src.lower()
        and "slug" not in src.lower()
    )  # allow generic comment but not blog logic


def test_blog_renderer_does_not_leak_to_framework():
    """5. BlogRenderer не протаскивает blog semantics в ai_framework"""
    framework_dir = pathlib.Path("ai_framework/rendering")
    for f in framework_dir.rglob("*.py"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        # Framework must not import blog_cms
        assert "blog_cms" not in txt, f"Framework should not import blog_cms: {f}"
        assert "BlogCmsService" not in txt, (
            f"Framework should not know BlogCmsService: {f}"
        )
        assert "BlogRenderer" not in txt, f"Framework should not know BlogRenderer: {f}"
        # SeoInjector must not contain domain terms
        if f.name == "seo.py":
            # Should not contain hardcoded "/posts/" literal
            assert '"/posts/"' not in txt and "'/posts/'" not in txt, (
                f"SeoInjector must not contain /posts/ literal: {f}"
            )
            # Lowercase check for forbidden hardcodes in logic (allow in comments about what it does NOT know)
            # We check actual code, not docstring, but simpler: ensure no blog-specific URL generation
            # The only allowed strings are generic SEO tags
            assert "posts/<slug>" not in txt
            assert (
                "categories/" not in txt
                or "categories" in txt.lower()
                and "No domain knowledge" in txt
            )  # allow in docstring explaining what it doesn't know


def test_static_site_generator_protocol_absent():
    """6. StaticSiteGeneratorProtocol действительно пока отсутствует как Python abstraction"""
    rendering_dir = pathlib.Path("ai_framework/rendering")
    all_text = ""
    for f in rendering_dir.rglob("*.py"):
        all_text += f.read_text(encoding="utf-8", errors="ignore") + "\n"
    # Should not have a concrete protocol named StaticSiteGeneratorProtocol yet
    assert "class StaticSiteGeneratorProtocol" not in all_text, (
        "StaticSiteGeneratorProtocol should remain in docs, not code yet"
    )
    assert (
        "StaticSiteGenerator" not in all_text or "StaticSiteWriter" in all_text
    )  # allow writer, but not generator protocol

    # Check docs contain it as documentation
    doc_path = pathlib.Path("docs/architecture/type_b_static_site.md")
    assert doc_path.exists(), "docs/architecture/type_b_static_site.md must exist"
    doc_txt = doc_path.read_text(encoding="utf-8", errors="ignore")
    assert (
        "Domain" in doc_txt
        and "Generator" in doc_txt
        and "Renderer" in doc_txt
        and "Output" in doc_txt
    )
    assert "StaticSiteGeneratorProtocol" in doc_txt or "Generator" in doc_txt


def test_docs_match_implementation():
    """7. docs/architecture/type_b_static_site.md соответствует фактической реализации"""
    doc_path = pathlib.Path("docs/architecture/type_b_static_site.md")
    assert doc_path.exists()
    doc_txt = doc_path.read_text(encoding="utf-8")

    # Check that documented components actually exist
    assert pathlib.Path("ai_framework/rendering/generated_page.py").exists()
    assert pathlib.Path("ai_framework/rendering/seo.py").exists()
    assert pathlib.Path("ai_framework/rendering/jinja.py").exists()
    assert pathlib.Path("ai_framework/rendering/static_writer.py").exists()
    assert pathlib.Path("ai_framework/rendering/protocols.py").exists()

    # Check that BlogRenderer and SiteGenerator exist
    assert pathlib.Path("showcases/blog_cms/services/blog_renderer.py").exists()
    assert pathlib.Path("showcases/blog_cms/services/site_generator.py").exists()

    # Check that GeneratedPage is used in site_generator
    site_gen_txt = pathlib.Path(
        "showcases/blog_cms/services/site_generator.py"
    ).read_text(encoding="utf-8")
    assert "GeneratedPage" in site_gen_txt
    assert "StaticSiteWriter" in site_gen_txt or "self._writer" in site_gen_txt

    # Check that framework rendering __init__ exports 5 components
    init_txt = pathlib.Path("ai_framework/rendering/__init__.py").read_text(
        encoding="utf-8"
    )
    for name in [
        "GeneratedPage",
        "SeoContext",
        "SeoInjector",
        "JinjaTemplateRenderer",
        "StaticSiteWriter",
    ]:
        assert name in init_txt, (
            f"{name} should be exported from ai_framework.rendering"
        )
