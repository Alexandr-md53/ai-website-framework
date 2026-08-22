from dataclasses import dataclass
from typing import Any
import pytest

from ai_framework.application.pipeline.contracts import (
    MiddlewareProtocol,
    NextStep,
    PipelineContext,
)
from ai_framework.application.pipeline.executor import ApplicationPipeline


@dataclass(frozen=True)
class PipelineTestRequest:
    data: str


@dataclass(frozen=True)
class PipelineTestResponse:
    data: str


class OrderTrackingMiddleware(
    MiddlewareProtocol[PipelineTestRequest, PipelineTestResponse]
):
    def __init__(self, name: str, execution_order: list[str]) -> None:
        self.name = name
        self.order = execution_order

    def process(
        self,
        request: PipelineTestRequest,
        context: PipelineContext,
        next_step: NextStep[PipelineTestRequest, PipelineTestResponse],
    ) -> PipelineTestResponse:
        self.order.append(f"IN_{self.name}")
        res = next_step(request, context)
        self.order.append(f"OUT_{self.name}")
        return res


class ExceptionCatchingMiddleware(
    MiddlewareProtocol[PipelineTestRequest, PipelineTestResponse]
):
    def __init__(self, caught_exceptions: list[Exception]) -> None:
        self.caught = caught_exceptions

    def process(
        self,
        request: PipelineTestRequest,
        context: PipelineContext,
        next_step: NextStep[PipelineTestRequest, PipelineTestResponse],
    ) -> PipelineTestResponse:
        try:
            return next_step(request, context)
        except Exception as exc:
            self.caught.append(exc)
            raise exc


def test_pipeline_executes_middlewares_in_onion_order() -> None:
    execution_order: list[str] = []
    m1 = OrderTrackingMiddleware("M1", execution_order)
    m2 = OrderTrackingMiddleware("M2", execution_order)

    def leaf_handler(
        req: PipelineTestRequest, ctx: PipelineContext
    ) -> PipelineTestResponse:
        execution_order.append("LEAF_HANDLER")
        return PipelineTestResponse(data=req.data.upper())

    pipeline = ApplicationPipeline(
        middlewares=[m1, m2],
        handler=leaf_handler,
    )

    context = PipelineContext(request_id="order-req")
    response = pipeline.execute(PipelineTestRequest(data="hello"), context)

    assert response == PipelineTestResponse(data="HELLO")
    assert execution_order == [
        "IN_M1",
        "IN_M2",
        "LEAF_HANDLER",
        "OUT_M2",
        "OUT_M1",
    ]


def test_pipeline_propagates_exceptions_through_middleware_chain() -> None:
    caught_errors: list[Exception] = []
    error_middleware = ExceptionCatchingMiddleware(caught_errors)

    def failing_handler(
        req: PipelineTestRequest, ctx: PipelineContext
    ) -> PipelineTestResponse:
        raise ValueError("Domain calculation failed")

    pipeline = ApplicationPipeline(
        middlewares=[error_middleware],
        handler=failing_handler,
    )

    context = PipelineContext(request_id="err-req")

    with pytest.raises(ValueError, match="Domain calculation failed"):
        pipeline.execute(PipelineTestRequest(data="fail"), context)

    assert len(caught_errors) == 1
    assert str(caught_errors[0]) == "Domain calculation failed"
