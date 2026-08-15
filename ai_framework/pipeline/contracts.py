"""
Contracts and data structures for AI Pipeline Stage 4.
"""

from dataclasses import dataclass
from ai_framework.ai_provider.contracts import Role


@dataclass(frozen=True)
class PipelineStep:
    """Элемент цепочки промпта."""

    kind: str  # 'system', 'context', 'history', 'user'
    template: str | None = None
    role: Role = Role.USER
    max_history_messages: int | None = None
