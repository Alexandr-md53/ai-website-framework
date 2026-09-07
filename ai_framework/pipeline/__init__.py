"""
ai_framework.pipeline - canonical public API for Phase 10.1 A1.3

Engine layer: PromptPipeline + Parser + AIService orchestration
No application/pipeline duplicate - single source.

Structure:
- contracts.py -> PipelineStep
- parser.py -> StructuredOutputParser
- prompt.py -> PromptPipeline
- service.py -> AIService
- exceptions.py -> PromptError, OutputParseError, etc.
"""

from .contracts import PipelineStep
from .service import AIService

# Optional imports - available if modules exist
try:
    from .prompt import PromptPipeline
except ImportError:
    PromptPipeline = None  # type: ignore

try:
    from .parser import StructuredOutputParser
except ImportError:
    StructuredOutputParser = None  # type: ignore

try:
    from .exceptions import (
        PipelineError,
        PromptError,
        OutputParseError,
    )
except ImportError:
    # Fallback if exceptions module has different names
    try:
        from .exceptions import *  # noqa: F401,F403
    except ImportError:
        pass

__all__ = [
    "PipelineStep",
    "AIService",
    "PromptPipeline",
    "StructuredOutputParser",
    "PipelineError",
    "PromptError",
    "OutputParseError",
]
