from __future__ import annotations
from typing import Protocol, runtime_checkable

@runtime_checkable
class TemplateRendererProtocol(Protocol):
    def render(self, template_name: str, context: dict) -> str:
        ...
