from dataclasses import dataclass
from typing import Any

from ai_framework.application.pipeline.contracts import (
    MiddlewareProtocol,
    NextStep,
    PipelineContext,
)


@dataclass(frozen=True)
class MockRequest:
    value: int


@dataclass(frozen=True)
class MockResponse:
    value: int


class LoggingMiddleware(MiddlewareProtocol[MockRequest, MockResponse]):
    def __init__(self, log_accumulator: list[str]) -> None:
        self._logs = log_accumulator

    def process(
        self,
        request: MockRequest,
        context: PipelineContext,
        next_step: NextStep[MockRequest, MockResponse],
    ) -> MockResponse:
        self._logs.append(f"PRE:{context.request_id}:{request.value}")
        response = next_step(request, context)
        self._logs.append(f"POST:{context.request_id}:{response.value}")
        return response


def test_middleware_onion_execution_and_passthrough() -> None:
    logs: list[str] = []
    middleware = LoggingMiddleware(logs)
    context = PipelineContext(request_id="test-ctx")
    request = MockRequest(value=10)

    def dummy_next(req: MockRequest, ctx: PipelineContext) -> MockResponse:
        logs.append("HANDLER_EXECUTED")
        return MockResponse(value=req.value * 2)

    response = middleware.process(request, context, dummy_next)

    assert response == MockResponse(value=20)
    assert logs == [
        "PRE:test-ctx:10",
        "HANDLER_EXECUTED",
        "POST:test-ctx:20",
    ]
