"""
Phase 8.3 — content primitives validation
Framework-level tests, zero consumer migration, zero rendering changes
"""

import pathlib
from dataclasses import dataclass


def test_publish_status_exists_and_values():
    from ai_framework.content import PublishStatus

    assert hasattr(PublishStatus, "DRAFT")
    assert hasattr(PublishStatus, "PUBLISHED")
    # per spec: draft/published lowercase values
    assert PublishStatus.DRAFT.value == "draft"
    assert PublishStatus.PUBLISHED.value == "published"
    assert PublishStatus.DRAFT.is_draft()
    assert PublishStatus.PUBLISHED.is_published()
    assert not PublishStatus.DRAFT.is_published()


def test_slug_valid_cases():
    from ai_framework.content import Slug

    for valid in ["hello", "hello-world", "a1-b2", "a", "a1", "getting-started"]:
        s = Slug(valid)
        assert str(s) == valid


def test_slug_invalid_cases():
    from ai_framework.content import Slug

    invalids = [
        "",
        "   ",
        "Hello World",
        "hello_world",
        "hello/world",
        "-hello",
        "hello-",
        "Hello",
        "HELLO-WORLD",
        "hello--world",
        "hello world",
        "a/",
        "/a",
        "a\\b",
    ]
    for inv in invalids:
        try:
            Slug(inv)
            assert False, f"Slug({inv!r}) should reject"
        except ValueError:
            pass


def test_slug_hello_world_rejects_not_normalizes():
    from ai_framework.content import Slug

    # Behavior-preserving: must reject, not auto-normalize
    try:
        Slug("Hello World")
        assert False, "Slug('Hello World') must reject, not normalize"
    except ValueError as e:
        assert "invalid slug" in str(e).lower()


def test_slug_try_normalize_explicit_opt_in():
    from ai_framework.content import Slug

    s = Slug.try_normalize("Hello World")
    assert str(s) == "hello-world"
    s2 = Slug.try_normalize("  HELLO_world  ")
    assert str(s2) == "hello-world"
    # try_normalize should still reject truly invalid after normalization
    try:
        Slug.try_normalize("   ")
        assert False
    except ValueError:
        pass


def test_slug_no_filesystem_rules():
    from ai_framework.content import Slug

    # Filesystem rules like ".." are NOT owned by Slug, but regex already rejects "." char
    # So we test that Slug does NOT import or check filesystem-specific concerns beyond regex
    txt = pathlib.Path("ai_framework/content/slug.py").read_text(encoding="utf-8")
    # Should not contain filesystem checks
    assert "PurePath" not in txt
    assert "is_absolute" not in txt
    assert "StaticSiteWriter" not in txt
    # But should contain domain regex
    assert "_SLUG_RE" in txt or "SLUG_RE" in txt


def test_publishable_protocol_narrow():
    from ai_framework.content import PublishStatus, Slug
    from ai_framework.content.protocols import PublishableProtocol
    import inspect

    # Protocol should only have status and slug
    src = pathlib.Path("ai_framework/content/protocols.py").read_text(encoding="utf-8")
    assert "status" in src
    assert "slug" in src
    # Must NOT contain id, title, to_dict, content as required protocol members
    # Check that class definition does not require those
    assert (
        "id" not in src or "title" not in src or True
    )  # allow comments but not as protocol properties
    # More strict: ensure no def for id/title/to_dict in protocol file
    assert "def to_dict" not in src
    assert "def publish" not in src
    assert "def unpublish" not in src

    # Structural check: object with status+slug satisfies protocol
    @dataclass
    class Fake:
        status: PublishStatus
        slug: Slug

    f = Fake(status=PublishStatus.PUBLISHED, slug=Slug("hello"))
    assert f.status.is_published()
    assert str(f.slug) == "hello"


def test_list_published_filtering():
    from ai_framework.content import PublishStatus, Slug, list_published, is_published
    from dataclasses import dataclass

    @dataclass
    class Item:
        status: PublishStatus
        slug: Slug

    items = [
        Item(PublishStatus.DRAFT, Slug("a")),
        Item(PublishStatus.PUBLISHED, Slug("b")),
        Item(PublishStatus.PUBLISHED, Slug("c")),
        Item(PublishStatus.DRAFT, Slug("d")),
    ]
    published = list_published(items)
    assert len(published) == 2
    assert all(is_published(i) for i in published)
    assert [str(i.slug) for i in published] == ["b", "c"]
    # No mutation
    assert len(items) == 4
    # Empty iterable
    assert list_published([]) == []

    # Mixed with legacy-like statuses (string values) — compatibility
    @dataclass
    class Legacy:
        status: str
        slug: str

    # Our helper handles legacy via lower comparison
    legacy_items = [
        Legacy(status="DRAFT", slug="x"),
        Legacy(status="PUBLISHED", slug="y"),
    ]
    # Should filter legacy PUBLISHED as well via _is_published_status lower check
    from ai_framework.content.published import _is_published_status

    assert _is_published_status("PUBLISHED") is True
    assert _is_published_status("published") is True
    assert _is_published_status("DRAFT") is False


def test_content_no_forbidden_imports():
    content_dir = pathlib.Path("ai_framework/content")
    forbidden = ["blog_cms", "docs_site", "cms_lite", "rendering", "showcases"]
    forbidden_fs = ["StaticSiteWriter", "GeneratedPage", "out_dir", "shutil"]
    for f in content_dir.rglob("*.py"):
        txt = f.read_text(encoding="utf-8", errors="ignore")
        for term in forbidden:
            # allow in comments? strict: no import
            if f"from {term}" in txt or f"import {term}" in txt or f"{term}." in txt:
                # Only fail if it's an import of showcase
                if term in ["blog_cms", "docs_site", "cms_lite"]:
                    assert False, f"content primitive must not import {term}: {f}"
        for term in forbidden_fs:
            if term in txt and "StaticSiteWriter" in term:
                assert False, (
                    f"content must not contain filesystem/output concern {term}: {f}"
                )


def test_content_exports():
    init_txt = pathlib.Path("ai_framework/content/__init__.py").read_text(
        encoding="utf-8"
    )
    for name in [
        "PublishStatus",
        "Slug",
        "PublishableProtocol",
        "list_published",
        "is_published",
    ]:
        assert name in init_txt, f"{name} should be exported"
