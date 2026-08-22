from typing import Any

from ai_framework.application.dto.article_dto import CreateArticleRequest
from ai_framework.application.pipeline import (
    ApplicationPipeline,
    MiddlewareProtocol,
    NextStep,
    PipelineContext,
    UseCaseHandlerAdapter,
)
from ai_framework.application.use_cases.create_article import CreateArticleUseCase
from ai_framework.crud.engine import UniversalCRUDEngine
from ai_framework.crud.persistence import InMemoryPersistenceProvider
from ai_framework.domain.entities.article import ArticleStatus
from ai_framework.infrastructure.repositories.article_repository import (
    CRUDArticleRepository,
)


class AuditTrackingMiddleware(MiddlewareProtocol[CreateArticleRequest, Any]):

    def __init__(self, audit_log: list[str]) -> None:
        self.audit_log = audit_log

    def process(
        self,
        request: CreateArticleRequest,
        context: PipelineContext,
        next_step: NextStep[CreateArticleRequest, Any],
    ) -> Any:
        self.audit_log.append(f"START:{context.request_id}:{request.title}")
        response = next_step(request, context)
        self.audit_log.append(f"END:{context.request_id}")
        return response


def test_end_to_end_pipeline_integration_with_use_case_and_crud() -> None:
    # 1. Infrastructure / CRUD Setup
    provider = InMemoryPersistenceProvider()
    engine = UniversalCRUDEngine(persistence_provider=provider)
    repository = CRUDArticleRepository(crud_engine=engine)

    # 2. Application Layer Setup (Frozen Use Case)
    use_case = CreateArticleUseCase(repository=repository)
    adapter = UseCaseHandlerAdapter(use_case.execute)

    # 3. Pipeline Setup
    audit_log: list[str] = []
    middleware = AuditTrackingMiddleware(audit_log)
    pipeline = ApplicationPipeline(
        middlewares=[middleware],
        handler=adapter,
    )

    # 4. Execution
    request = CreateArticleRequest(
        title="Integration Title",
        content="Integration Content Body",
    )
    context = PipelineContext(request_id="req-e2e-100")

    response = pipeline.execute(request, context)

    # 5. End-to-End Assertions
    # 5.1 Outcome contract assertion
    assert response.article_id is not None

    # 5.2 State assertion via Repository & Value Objects
    stored_article = repository.get_by_id(response.article_id)
    assert stored_article is not None
    assert stored_article.title.value == "Integration Title"
    assert stored_article.content.value == "Integration Content Body"
    assert stored_article.status == ArticleStatus.DRAFT

    # 5.3 Pipeline orchestration assertion
    assert audit_log == [
        "START:req-e2e-100:Integration Title",
        "END:req-e2e-100",
    ]