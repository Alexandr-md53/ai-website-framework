"""
Phase 9.3 regression — FS safety + rendering contract
Fixed version: BlogRenderer owns SeoContext/Jinja, SiteGenerator delegates to StaticSiteWriter
"""

import pathlib, tempfile
import pytest
from ai_framework.rendering import GeneratedPage, StaticSiteWriter


def test_static_writer_rejects_traversal():
    w = StaticSiteWriter()
    tmp = pathlib.Path(tempfile.gettempdir()) / "test_blog_fs_guard_traversal"
    with pytest.raises(ValueError):
        w.write([GeneratedPage("../../etc/passwd", "x", "hack")], tmp, clean=True)


def test_static_writer_rejects_absolute():
    w = StaticSiteWriter()
    tmp = pathlib.Path(tempfile.gettempdir()) / "test_blog_fs_guard_absolute"
    with pytest.raises(ValueError):
        w.write([GeneratedPage("/etc/passwd", "x", "hack")], tmp, clean=True)
    with pytest.raises(ValueError):
        w.write([GeneratedPage("\\windows\\system32", "x", "hack")], tmp, clean=True)


def test_static_writer_rejects_drive():
    w = StaticSiteWriter()
    tmp = pathlib.Path(tempfile.gettempdir()) / "test_blog_fs_guard_drive"
    with pytest.raises(ValueError):
        w.write(
            [GeneratedPage("C:\\windows\\system32\\evil.html", "x", "hack")],
            tmp,
            clean=True,
        )


def test_site_generator_write_delegates_to_framework_writer():
    # site_generator.py must delegate to StaticSiteWriter, not do raw out_dir / path
    src = pathlib.Path("showcases/blog_cms/services/site_generator.py").read_text(
        encoding="utf-8"
    )
    assert "from ai_framework.rendering import" in src
    assert "GeneratedPage" in src
    assert "StaticSiteWriter" in src
    assert "self._writer.write" in src
    # Must NOT contain legacy direct write without guard
    assert "from jinja2 import Environment" not in src
    # Must export Renderer alias for backward compat with app_factory
    assert "Renderer = " in src or "Renderer= " in src


def test_blog_renderer_uses_framework_primitives():
    # BlogRenderer is the showcase-local renderer that composes framework primitives
    # per Phase 9.2 contract: JinjaTemplateRenderer + SeoContext + SeoInjector
    renderer_path = pathlib.Path("showcases/blog_cms/services/blog_renderer.py")
    assert renderer_path.exists(), "blog_renderer.py must exist"
    txt = renderer_path.read_text(encoding="utf-8")
    assert "from ai_framework.rendering import" in txt
    assert "JinjaTemplateRenderer" in txt
    assert "SeoContext" in txt
    assert "SeoInjector" in txt
    assert "from jinja2 import Environment" not in txt
    assert "class BlogRenderer" in txt


def test_blog_and_docs_use_same_framework_contract():
    blog_renderer_src = pathlib.Path(
        "showcases/blog_cms/services/blog_renderer.py"
    ).read_text(encoding="utf-8")
    site_gen_src = pathlib.Path(
        "showcases/blog_cms/services/site_generator.py"
    ).read_text(encoding="utf-8")
    # Blog uses framework primitives via BlogRenderer
    assert "JinjaTemplateRenderer" in blog_renderer_src
    assert "SeoContext" in blog_renderer_src
    assert "SeoInjector" in blog_renderer_src
    # SiteGenerator uses StaticSiteWriter (one FS boundary)
    assert "StaticSiteWriter" in site_gen_src
    assert "GeneratedPage" in site_gen_src

    # docs_site reference implementation should also use same primitives — check if file exists
    docs_renderer_path = pathlib.Path("showcases/docs_site/services/docs_renderer.py")
    docs_gen_path = pathlib.Path("showcases/docs_site/services/docs_site_generator.py")
    if docs_renderer_path.exists():
        docs_r = docs_renderer_path.read_text(encoding="utf-8")
        assert "JinjaTemplateRenderer" in docs_r
        assert "SeoContext" in docs_r
        assert "SeoInjector" in docs_r
    if docs_gen_path.exists():
        docs_g = docs_gen_path.read_text(encoding="utf-8")
        assert "StaticSiteWriter" in docs_g
        assert "GeneratedPage" in docs_g
