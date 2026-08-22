from typing import Callable, Generic, TypeVar

from ai_framework.application.pipeline.contracts import PipelineContext

TRequest = TypeVar("TRequest")
TResponse = TypeVar("TResponse")


class UseCaseHandlerAdapter(Generic[TRequest, TResponse]):
    """Адаптирует метод execute(request) существующего Use Case
    к контракту ApplicationHandlerProtocol.
    """

    def __init__(self, use_case_fn: Callable[[TRequest], TResponse]) -> None:
        self._use_case_fn = use_case_fn

    def handle(self, request: TRequest, context: PipelineContext) -> TResponse:
        return self._use_case_fn(request)
