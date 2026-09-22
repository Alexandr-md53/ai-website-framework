from __future__ import annotations
from typing import Protocol, runtime_checkable, List
from .generated_page import GeneratedPage


@runtime_checkable
class TemplateRendererProtocol(Protocol):
    def render(self, template_name: str, context: dict) -> str: ...


@runtime_checkable
class StaticSiteGeneratorProtocol(Protocol):
    def generate(self) -> List[GeneratedPage]: ...
