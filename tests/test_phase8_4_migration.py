import uuid


def test_post_uses_publish_status_and_slug():
    from showcases.blog_cms.domain.models import Post, PostStatus
    from ai_framework.content import PublishStatus, Slug

    assert PostStatus is PublishStatus
    post = Post(
        id=uuid.uuid4(),
        title="Hello World Post",
        slug=Slug("hello-world"),
        content="This is enough content for draft validation, more than 20 chars.",
        category_id=uuid.uuid4(),
        author_id=uuid.uuid4(),
    )
    assert isinstance(post.slug, Slug)
    assert post.status == PublishStatus.DRAFT


def test_post_slug_validation_rejects_hello_world():
    from showcases.blog_cms.domain.models import Post

    try:
        Post(
            id=uuid.uuid4(),
            title="Test",
            slug="Hello World",
            content="valid content with more than 20 chars here",
            category_id=uuid.uuid4(),
            author_id=uuid.uuid4(),
        )
        assert False
    except ValueError:
        pass


def test_post_draft_publish_unpublish():
    from showcases.blog_cms.domain.models import Post
    from ai_framework.content import PublishStatus, Slug

    post = Post(
        id=uuid.uuid4(),
        title="Valid Title",
        slug=Slug("valid-slug"),
        content="This content is long enough for publishing validation.",
        category_id=uuid.uuid4(),
        author_id=uuid.uuid4(),
    )
    assert not post.is_published()
    post.publish()
    assert post.is_published()
    post.unpublish()
    assert post.status == PublishStatus.DRAFT


def test_docpage_uses_publish_status_and_slug():
    from showcases.docs_site.domain.models import DocPage, DocStatus
    from ai_framework.content import PublishStatus, Slug

    assert DocStatus is PublishStatus
    page = DocPage(
        id=uuid.uuid4(),
        title="Getting Started",
        slug=Slug("getting-started"),
        content="This is a docs page content that is long enough.",
    )
    assert isinstance(page.slug, Slug)


def test_docpage_slug_validation_now_enforced():
    from showcases.docs_site.domain.models import DocPage

    try:
        DocPage(
            id=uuid.uuid4(),
            title="Bad",
            slug="Hello World",
            content="Some content here that is long enough.",
        )
        assert False
    except ValueError:
        pass


def test_docpage_publish_lifecycle():
    from showcases.docs_site.domain.models import DocPage
    from ai_framework.content import PublishStatus, Slug

    page = DocPage(
        id=uuid.uuid4(),
        title="Guide",
        slug=Slug("guide"),
        content="Content with enough length for docs publishing.",
    )
    page.publish()
    assert page.is_published()
    page.unpublish()
    assert page.status == PublishStatus.DRAFT


def test_blog_service_uses_framework_list_published():
    from showcases.blog_cms.services.blog_service import BlogCmsService
    from showcases.blog_cms.domain.user import UserContext, UserRole, PipelineContext
    import pathlib

    src = pathlib.Path("showcases/blog_cms/services/blog_service.py").read_text(
        encoding="utf-8"
    )
    assert "framework_list_published" in src
    assert "from ai_framework.content" in src


def test_docs_service_uses_framework_list_published():
    import pathlib

    src = pathlib.Path("showcases/docs_site/services/docs_service.py").read_text(
        encoding="utf-8"
    )
    assert "framework_list_published" in src


def test_cross_consumer_publishable_protocol():
    from ai_framework.content import PublishStatus, Slug, list_published
    from showcases.blog_cms.domain.models import Post
    from showcases.docs_site.domain.models import DocPage

    post = Post(
        id=uuid.uuid4(),
        title="Post",
        slug=Slug("post-slug"),
        content="Post content long enough for validation.",
        category_id=uuid.uuid4(),
        author_id=uuid.uuid4(),
        status=PublishStatus.PUBLISHED,
    )
    page = DocPage(
        id=uuid.uuid4(),
        title="Page",
        slug=Slug("page-slug"),
        content="Page content long enough for validation.",
        status=PublishStatus.DRAFT,
    )
    published = list_published([post, page])
    assert len(published) == 1
