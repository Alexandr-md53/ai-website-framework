from typing import Callable, Generic, Sequence, TypeVar, Union

from ai_framework.application.pipeline.contracts import (
    ApplicationHandlerProtocol,
    MiddlewareProtocol,
    NextStep,
    PipelineContext,
)

TRequest = TypeVar("TRequest")
TResponse = TypeVar("TResponse")

HandlerType = Union[
    ApplicationHandlerProtocol[TRequest, TResponse],
    Callable[[TRequest, PipelineContext], TResponse],
]


class ApplicationPipeline(Generic[TRequest, TResponse]):
    """Исполнитель цепочки Middleware (Onion Architecture / Chain Pattern)."""

    def __init__(
        self,
        middlewares: Sequence[MiddlewareProtocol[TRequest, TResponse]],
        handler: HandlerType[TRequest, TResponse],
    ) -> None:
        self._middlewares = list(middlewares)
        if hasattr(handler, "handle"):
            self._handler: Callable[[TRequest, PipelineContext], TResponse] = (
                handler.handle  # type: ignore[union-attr]
            )
        else:
            self._handler = handler  # type: ignore[assignment]

    def execute(self, request: TRequest, context: PipelineContext) -> TResponse:
        def build_chain(index: int) -> NextStep[TRequest, TResponse]:
            if index >= len(self._middlewares):
                return self._handler

            middleware = self._middlewares[index]

            def next_step(req: TRequest, ctx: PipelineContext) -> TResponse:
                return middleware.process(req, ctx, build_chain(index + 1))

            return next_step

        chain = build_chain(0)
        return chain(request, context)
