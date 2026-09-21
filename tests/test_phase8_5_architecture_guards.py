"""
Phase 8.5 — architecture guards + regression
Baseline: e960a48 / 648 passed
"""

import pathlib


def test_guard_1_framework_isolation_no_showcase_or_rendering_imports():
    content_dir = pathlib.Path("ai_framework/content")
    assert content_dir.exists()
    forbidden = [
        "from showcases",
        "import showcases",
        "from blog_cms",
        "import blog_cms",
        "from docs_site",
        "import docs_site",
        "from cms_lite",
        "import cms_lite",
    ]
    for py_file in content_dir.rglob("*.py"):
        txt = py_file.read_text(encoding="utf-8", errors="ignore")
        for marker in forbidden:
            assert marker not in txt, (
                f"framework isolation violation: {py_file} contains '{marker}'"
            )


def test_guard_2_slug_boundary_no_filesystem_or_writer_concepts():
    txt = pathlib.Path("ai_framework/content/slug.py").read_text(encoding="utf-8")
    # Check for actual filesystem/path/writer CODE, not the word "filesystem" in docstring
    # "No filesystem rules — owned by writer" is allowed as documentation of boundary
    forbidden_code_terms = [
        "PurePath",
        "PurePosixPath",
        "PureWindowsPath",
        "is_absolute",
        "shutil",
        "StaticSiteWriter",
        "GeneratedPage",
        "out_dir",
        "resolve()",
    ]
    for term in forbidden_code_terms:
        assert term not in txt, (
            f"Slug boundary violation: ai_framework/content/slug.py must not contain code term '{term}' — filesystem safety owned by writer layer"
        )
    assert "_SLUG_RE" in txt


def test_guard_3_narrow_protocol_declared_contract_is_only_status_and_slug():
    from ai_framework.content.protocols import PublishableProtocol
    import inspect

    # Protocol is implemented via @property def status / def slug, so __annotations__ may be empty
    # Check via members and source structure
    src = pathlib.Path("ai_framework/content/protocols.py").read_text(encoding="utf-8")

    # Must declare status and slug as property/method
    assert "status" in src, (
        f"PublishableProtocol must declare 'status' — source missing: {src[:500]}"
    )
    assert "slug" in src, (
        f"PublishableProtocol must declare 'slug' — source missing: {src[:500]}"
    )

    # Forbidden members must NOT be in protocol
    forbidden = [
        "def id",
        "def title",
        "def content",
        "def to_dict",
        "def seo",
        "def publish",
        "def unpublish",
        "def html_content",
        "def category_id",
        "def author_id",
        "def section_id",
        "def version_id",
    ]
    for bad in forbidden:
        assert bad not in src, (
            f"PublishableProtocol must be narrow — must NOT contain '{bad}'"
        )

    # Also check that only status and slug are public properties (via inspection)
    # Get all property/method names that are not private/dunder
    public_names = []
    for name, obj in inspect.getmembers(PublishableProtocol):
        if name.startswith("_"):
            continue
        if (
            isinstance(obj, property)
            or inspect.isfunction(obj)
            or inspect.ismethod(obj)
        ):
            public_names.append(name)

    # Filter to expected: status, slug are required; allow nothing else from forbidden list
    # We expect exactly status and slug as public contract
    # Some Protocol implementations also expose __protocol_attrs__ etc — ignore
    relevant = [
        n
        for n in public_names
        if n
        in {
            "status",
            "slug",
            "id",
            "title",
            "content",
            "to_dict",
            "seo",
            "publish",
            "unpublish",
        }
    ]
    assert set(relevant) == {"status", "slug"}, (
        f"PublishableProtocol must declare exactly status+slug, got public relevant {relevant}, all public {public_names}"
    )

    # Check annotations if present — if empty, it's okay for property-based protocol, but if present, must be narrow
    ann = getattr(PublishableProtocol, "__annotations__", {})
    if ann:
        public_declared = {k for k in ann.keys() if not k.startswith("_")}
        # If annotations exist, they must be subset of {status, slug}
        assert public_declared.issubset({"status", "slug"}), (
            f"annotations must be subset of status,slug, got {public_declared}"
        )


def test_guard_4_post_uses_publish_status_and_slug():
    from showcases.blog_cms.domain.models import Post
    from ai_framework.content import Slug
    import uuid

    src = pathlib.Path("showcases/blog_cms/domain/models.py").read_text(
        encoding="utf-8"
    )
    assert "from ai_framework.content" in src
    assert "PublishStatus" in src
    post = Post(
        id=uuid.uuid4(),
        title="Guard Test",
        slug=Slug("guard-test"),
        content="Content long enough for draft validation, at least 20 chars.",
        category_id=uuid.uuid4(),
        author_id=uuid.uuid4(),
    )
    assert isinstance(post.slug, Slug)
    assert isinstance(post.to_dict()["slug"], str)


def test_guard_5_docpage_uses_publish_status_and_slug():
    from showcases.docs_site.domain.models import DocPage
    from ai_framework.content import PublishStatus, Slug
    import uuid

    page = DocPage(
        id=uuid.uuid4(),
        title="Guard Doc",
        slug=Slug("guard-doc"),
        content="Content long enough for docs, more than 10 chars.",
    )
    assert isinstance(page.slug, Slug)
    assert isinstance(page.status, PublishStatus)


def test_guard_6_blog_service_uses_framework_list_published():
    src = pathlib.Path("showcases/blog_cms/services/blog_service.py").read_text(
        encoding="utf-8"
    )
    assert "from ai_framework.content" in src
    assert "framework_list_published" in src
    published_src = pathlib.Path("ai_framework/content/published.py").read_text(
        encoding="utf-8"
    )
    assert "category_slug" not in published_src
    assert "tag_slug" not in published_src
    assert "section_slug" not in published_src
    assert "version_slug" not in published_src


def test_guard_6_docs_service_uses_framework_list_published():
    src = pathlib.Path("showcases/docs_site/services/docs_service.py").read_text(
        encoding="utf-8"
    )
    assert "from ai_framework.content" in src
    assert "framework_list_published" in src
    published_src = pathlib.Path("ai_framework/content/published.py").read_text(
        encoding="utf-8"
    )
    assert "def list_published" in published_src
    assert "Iterable" in published_src


def test_guard_7_docpage_invalid_slug_rejects():
    from showcases.docs_site.domain.models import DocPage
    import uuid

    try:
        DocPage(
            id=uuid.uuid4(),
            title="Bad",
            slug="Hello World",
            content="Content long enough for docs validation.",
        )
        assert False
    except ValueError:
        pass


def test_guard_8_rendering_pipeline_untouched():
    rendering_dir = pathlib.Path("ai_framework/rendering")
    if rendering_dir.exists():
        for f in rendering_dir.rglob("*.py"):
            txt = f.read_text(encoding="utf-8", errors="ignore")
            assert "SLUG_RE" not in txt or "content" not in txt.lower()
