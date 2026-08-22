from dataclasses import FrozenInstanceError
import pytest

from ai_framework.application.pipeline.contracts import PipelineContext


def test_pipeline_context_creation() -> None:
    context = PipelineContext(request_id="req-123", metadata={"tenant": "alpha"})

    assert context.request_id == "req-123"
    assert context.metadata["tenant"] == "alpha"


def test_pipeline_context_default_metadata() -> None:
    context = PipelineContext(request_id="req-456")

    assert context.request_id == "req-456"
    assert context.metadata == {}


def test_pipeline_context_immutability() -> None:
    context = PipelineContext(request_id="req-789")

    with pytest.raises(FrozenInstanceError):
        context.request_id = "req-999"  # type: ignore[misc]
