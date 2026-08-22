from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, TypeVar

TRequest = TypeVar("TRequest", contravariant=True)
TResponse = TypeVar("TResponse", covariant=True)


@dataclass(frozen=True)
class PipelineContext:
    """Контейнер метаданных выполнения запроса (Execution Context)."""

    request_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


NextStep = Callable[[TRequest, PipelineContext], TResponse]


class ApplicationHandlerProtocol(Protocol[TRequest, TResponse]):
    """Единый контракт для конечных обработчиков (Handlers)."""

    def handle(self, request: TRequest, context: PipelineContext) -> TResponse:
        ...


class MiddlewareProtocol(Protocol[TRequest, TResponse]):
    """Контракт сквозного компонента (Middleware)."""

    def process(
        self,
        request: TRequest,
        context: PipelineContext,
        next_step: NextStep[TRequest, TResponse],
    ) -> TResponse:
        ...


class ApplicationPipelineProtocol(Protocol[TRequest, TResponse]):
    """Контракт исполнителя цепочки Middleware."""

    def execute(self, request: TRequest, context: PipelineContext) -> TResponse:
        ...