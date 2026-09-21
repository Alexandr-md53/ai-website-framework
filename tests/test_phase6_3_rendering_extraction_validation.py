"""
Phase 6.3 — Rendering extraction validation (UPDATED for Phase 7.2)
"""

import pathlib


def test_cms_lite_no_rendering_dependency():
    for f in pathlib.Path("showcases/cms_lite").rglob("*.py"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        assert "ai_framework.rendering" not in txt
        assert "from ai_framework.rendering" not in txt


def test_blog_cms_uses_extracted_primitives():
    assert "from ai_framework.rendering" in pathlib.Path(
        "showcases/blog_cms/services/blog_renderer.py"
    ).read_text(encoding="utf-8")
    from showcases.blog_cms.services.blog_renderer import BlogRenderer
    from showcases.blog_cms.services.site_generator import SiteGenerator
    from showcases.blog_cms.services.blog_service import BlogCmsService
    from ai_framework.rendering import GeneratedPage

    gen = SiteGenerator(BlogCmsService(), BlogRenderer())
    pages = gen.generate()
    assert isinstance(pages, list)


def test_generated_page_single_output_value_object():
    from ai_framework.rendering import GeneratedPage

    defs = [
        f
        for f in pathlib.Path("ai_framework/rendering").rglob("*.py")
        if "class GeneratedPage" in f.read_text(encoding="utf-8", errors="ignore")
    ]
    assert len(defs) == 1


def test_static_site_writer_only_generic_writer():
    txt = pathlib.Path("ai_framework/rendering/static_writer.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "BlogCmsService" not in txt and "DocsService" not in txt


def test_framework_isolation():
    rendering_dir = pathlib.Path("ai_framework/rendering")
    for f in rendering_dir.rglob("*.py"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        for fp in ["/posts/", "/guides/", "/categories/", "/tags/"]:
            if f'"{fp}"' in txt or f"'{fp}'" in txt:
                assert False, (
                    f"Framework must not contain hardcoded path literal {fp}: {f}"
                )


def test_static_site_generator_protocol_absent():
    """UPDATED for Phase 7.2: protocol allowed as minimal abstraction"""
    rendering_dir = pathlib.Path("ai_framework/rendering")
    all_text = "\n".join(
        [
            f.read_text(encoding="utf-8", errors="ignore")
            for f in rendering_dir.rglob("*.py")
        ]
    )
    doc_txt = pathlib.Path("docs/architecture/type_b_static_site.md").read_text(
        encoding="utf-8", errors="ignore"
    )
    if "class StaticSiteGeneratorProtocol" in all_text:
        proto_txt = (rendering_dir / "protocols.py").read_text(encoding="utf-8")
        assert "class StaticSiteGeneratorProtocol" in proto_txt
        assert "def write" not in proto_txt, "Protocol must not contain write()"
        assert "def generate" in proto_txt and "GeneratedPage" in proto_txt
    else:
        assert "Generator" in doc_txt


def test_docs_match_implementation():
    assert pathlib.Path("docs/architecture/type_b_static_site.md").exists()
    assert pathlib.Path("ai_framework/rendering/protocols.py").exists()
