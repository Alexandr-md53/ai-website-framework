from dataclasses import dataclass

from ai_framework.application.pipeline.adapter import UseCaseHandlerAdapter
from ai_framework.application.pipeline.contracts import PipelineContext


@dataclass(frozen=True)
class DummyRequest:
    payload: str


@dataclass(frozen=True)
class DummyResponse:
    result: str


class DummyUseCase:
    """Имитация существующего Use Case с методом execute(request)."""

    def __init__(self) -> None:
        self.was_called = False
        self.received_request: DummyRequest | None = None

    def execute(self, request: DummyRequest) -> DummyResponse:
        self.was_called = True
        self.received_request = request
        return DummyResponse(result=f"processed_{request.payload}")


def test_use_case_handler_adapter_executes_underlying_use_case() -> None:
    use_case = DummyUseCase()
    adapter = UseCaseHandlerAdapter(use_case.execute)

    request = DummyRequest(payload="hello")
    context = PipelineContext(request_id="req-001")

    response = adapter.handle(request, context)

    assert use_case.was_called is True
    assert use_case.received_request == request
    assert response == DummyResponse(result="processed_hello")
