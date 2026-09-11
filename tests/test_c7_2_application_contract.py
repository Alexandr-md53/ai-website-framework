# CODING: utf-8, ASCII only
"""
C7.2 Application Boundary Freeze — contract tests only

Verifies existing canonical contracts without modifying production code.
C5 frozen, C6 frozen, scaffold.py, fastapi.py, UniversalCRUDEngine untouched.
"""

from ai_framework.application.pipeline.contracts import (
    PipelineContext,
    ApplicationHandlerProtocol,
    MiddlewareProtocol,
    ApplicationPipelineProtocol,
)
from ai_framework.application.pipeline.executor import ApplicationPipeline
from ai_framework.application.pipeline.adapter import UseCaseHandlerAdapter
from ai_framework.domain.contracts.repositories import ArticleRepository
from ai_framework.infrastructure.repositories.article_repository import (
    CRUDArticleRepository,
)
from ai_framework.application.dto.article_dto import (
    CreateArticleRequest,
    CreateArticleResponse,
    PublishArticleRequest,
    PublishArticleResponse,
    ArchiveArticleRequest,
    ArchiveArticleResponse,
)
from ai_framework.domain.entities.article import Article, ArticleStatus
from ai_framework.domain.value_objects.article_id import ArticleId
from ai_framework.domain.value_objects.title import Title
from ai_framework.domain.value_objects.content import Content
from ai_framework.application.use_cases.create_article import CreateArticleUseCase
from ai_framework.application.use_cases.publish_article import PublishArticleUseCase
from ai_framework.application.use_cases.archive_article import ArchiveArticleUseCase


class FakeArticleRepository(ArticleRepository):
    def __init__(self):
        self._store = {}

    def add(self, article: Article) -> None:
        self._store[article.id.value] = article

    def get_by_id(self, article_id: ArticleId):
        return self._store.get(article_id.value)


def test_pipeline_context_metadata():
    ctx = PipelineContext(request_id="req-123", metadata={"user": "test"})
    assert ctx.request_id == "req-123"
    assert ctx.metadata["user"] == "test"
    assert ctx.metadata is not None


def test_application_pipeline_onion_execution():
    class AddFlagMiddleware:
        def process(self, request, context, next_step):
            request["flag"] = True
            context.metadata["mw"] = "hit"
            return next_step(request, context)

    class FinalHandler:
        def handle(self, request, context):
            assert request.get("flag") is True
            assert context.metadata.get("mw") == "hit"
            return {"ok": True, "request_id": context.request_id}

    pipeline = ApplicationPipeline(
        middlewares=[AddFlagMiddleware()], handler=FinalHandler()
    )
    ctx = PipelineContext(request_id="r1")
    result = pipeline.execute({"data": 1}, ctx)
    assert result["ok"] is True
    assert result["request_id"] == "r1"


def test_pipeline_with_callable_handler():
    def callable_handler(request, context):
        return f"handled:{request['x']}:{context.request_id}"

    pipeline = ApplicationPipeline(middlewares=[], handler=callable_handler)
    ctx = PipelineContext(request_id="c1")
    assert pipeline.execute({"x": 42}, ctx) == "handled:42:c1"


def test_use_case_handler_adapter_contract():
    class DummyUseCase:
        def execute(self, req):
            return f"uc:{req}"

    adapter = UseCaseHandlerAdapter(DummyUseCase().execute)
    ctx = PipelineContext(request_id="adapt-1")
    assert hasattr(adapter, "handle")
    result = adapter.handle("test-req", ctx)
    assert result == "uc:test-req"
    pipeline = ApplicationPipeline(middlewares=[], handler=adapter)
    assert pipeline.execute("test-req", ctx) == "uc:test-req"


def test_crud_article_repository_implements_abstract():
    assert issubclass(CRUDArticleRepository, ArticleRepository)
    repo = CRUDArticleRepository(crud_engine=None)
    assert isinstance(repo, ArticleRepository)
    article = Article(
        id=ArticleId("a1"),
        title=Title("t"),
        content=Content("c"),
        status=ArticleStatus.DRAFT,
    )
    repo.add(article)
    assert repo.get_by_id(ArticleId("a1")) is None


def test_create_article_use_case_to_repo_chain():
    repo = FakeArticleRepository()
    uc = CreateArticleUseCase(repository=repo)
    req = CreateArticleRequest(title="Hello", content="World")
    resp = uc.execute(req)
    assert isinstance(resp, CreateArticleResponse)
    assert isinstance(resp.article_id, ArticleId)
    stored = repo.get_by_id(resp.article_id)
    assert stored is not None
    assert stored.title.value == "Hello"
    assert stored.status == ArticleStatus.DRAFT


def test_publish_article_use_case_chain():
    repo = FakeArticleRepository()
    create_uc = CreateArticleUseCase(repository=repo)
    created = create_uc.execute(CreateArticleRequest(title="T", content="C"))
    publish_uc = PublishArticleUseCase(repository=repo)
    resp = publish_uc.execute(
        PublishArticleRequest(article_id=created.article_id.value)
    )
    assert isinstance(resp, PublishArticleResponse)
    assert resp.is_published is True
    stored = repo.get_by_id(created.article_id)
    assert stored.status == ArticleStatus.PUBLISHED


def test_archive_article_use_case_chain():
    repo = FakeArticleRepository()
    create_uc = CreateArticleUseCase(repository=repo)
    created = create_uc.execute(CreateArticleRequest(title="T", content="C"))
    publish_uc = PublishArticleUseCase(repository=repo)
    publish_uc.execute(PublishArticleRequest(article_id=created.article_id.value))
    archive_uc = ArchiveArticleUseCase(repository=repo)
    resp = archive_uc.execute(
        ArchiveArticleRequest(article_id=created.article_id.value)
    )
    assert isinstance(resp, ArchiveArticleResponse)
    assert resp.is_archived is True
    stored = repo.get_by_id(created.article_id)
    assert stored.status == ArticleStatus.ARCHIVED


def test_pipeline_end_to_end_use_case_via_adapter():
    repo = FakeArticleRepository()
    create_uc = CreateArticleUseCase(repository=repo)
    adapter = UseCaseHandlerAdapter(create_uc.execute)
    pipeline = ApplicationPipeline(middlewares=[], handler=adapter)
    ctx = PipelineContext(request_id="e2e-1")
    resp = pipeline.execute(CreateArticleRequest(title="E2E", content="Flow"), ctx)
    assert isinstance(resp, CreateArticleResponse)
    assert repo.get_by_id(resp.article_id) is not None


def test_delivery_to_application_boundary_schema():
    repo = FakeArticleRepository()
    uc = CreateArticleUseCase(repository=repo)
    adapter = UseCaseHandlerAdapter(uc.execute)
    pipeline = ApplicationPipeline(middlewares=[], handler=adapter)

    def endpoint_handler_simulation(http_request: dict):
        dto = CreateArticleRequest(
            title=http_request["body"]["title"],
            content=http_request["body"]["content"],
        )
        ctx = PipelineContext(request_id=http_request.get("request_id", "req"))
        return pipeline.execute(dto, ctx)

    result = endpoint_handler_simulation(
        {
            "body": {"title": "From API", "content": "Via pipeline"},
            "request_id": "api-1",
        }
    )
    assert isinstance(result, CreateArticleResponse)
    assert repo.get_by_id(result.article_id).title.value == "From API"
