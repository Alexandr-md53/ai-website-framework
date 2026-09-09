# coding: utf-8, ASCII only
"""Showcase Manifest Contract - C3.1 canonical."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def _get_version() -> str:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["project"]["version"]


FRAMEWORK_VERSION = _get_version()


@dataclass(frozen=True)
class ShowcaseManifest:
    """Minimal contract for showcase/manifest.json - based on real showcases/."""

    name: str  # cafe, lawyer, plant_nursery - directory name
    product: str  # crud | api | pipeline - must be in PRODUCTS
    version: str = FRAMEWORK_VERSION
    package: str = ""  # showcases.cafe
    description: str = ""
    domain: List[str] = field(default_factory=list)  # ["menu_item"] - files in domain/
    metadata: str = (
        ""  # dotted path: showcases.cafe.metadata.cafe_metadata.get_cafe_ui_schema
    )
    services: List[str] = field(default_factory=list)  # dotted paths to services

    def __post_init__(self):
        if not self.name:
            raise ValueError("name required")
        if self.product not in ("crud", "api", "pipeline"):
            raise ValueError(f"product must be crud|api|pipeline, got {self.product}")
        if not self.package:
            object.__setattr__(self, "package", f"showcases.{self.name}")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "product": self.product,
            "version": self.version,
            "package": self.package,
            "description": self.description,
            "domain": self.domain,
            "metadata": self.metadata,
            "services": self.services,
        }


# Real showcases as per actual code - source of truth for C3.2 generation
KNOWN_SHOWCASES = [
    ShowcaseManifest(
        name="cafe",
        product="crud",
        description="Cafe menu with RBAC (barista/manager)",
        domain=["menu_item"],
        metadata="showcases.cafe.metadata.cafe_metadata.get_cafe_ui_schema",
        services=["showcases.cafe.services.cafe_service.CafeService"],
    ),
    ShowcaseManifest(
        name="lawyer",
        product="crud",
        description="Lawyer practice areas and consultation requests",
        domain=["models"],
        metadata="showcases.lawyer.domain.models",
        services=["showcases.lawyer.services.lawyer_service"],
    ),
    ShowcaseManifest(
        name="plant_nursery",
        product="crud",
        description="Plant nursery with light/water requirements",
        domain=["category", "plant", "pricing"],
        metadata="showcases.plant_nursery.metadata.plant_metadata.get_plant_ui_schema",
        services=["showcases.plant_nursery.services.catalog_service"],
    ),
]
