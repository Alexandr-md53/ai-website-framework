# coding: utf-8, ASCII only
"""Product Manifest - C2.2 canonical registry."""

from __future__ import annotations
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def _get_framework_version() -> str:
    root = Path(__file__).resolve().parents[2] # было [1]
    with (root / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["project"]["version"]


FRAMEWORK_VERSION = _get_framework_version()

# Canonical product IDs - stable boundaries
PRODUCTS = {
    "crud": {
        "version": FRAMEWORK_VERSION,
        "package": "ai_framework.crud",
        "description": "CRUD engine with contracts and persistence",
        "contracts": [
            "CrudContract",
            "CrudEngine",
            "PersistenceProtocol",
            "SQLitePersistence",
            "SlugOrchestrator",
        ],
    },
    "api": {
        "version": FRAMEWORK_VERSION,
        "package": "ai_framework.api",
        "description": "API layer with router and registry",
        "contracts": [
            "APIAdapter",
            "Router",
            "APIRegistry",
            "Endpoint",
            "APIResponse",
        ],
    },
    "pipeline": {
        "version": FRAMEWORK_VERSION,
        "package": "ai_framework.pipeline",
        "description": "Pipeline parser and service",
        "contracts": [
            "PipelineStep",
            "PromptPipeline",
            "StructuredOutputParser",
            "AIService",
            "PipelineContract",
        ],
    },
}


def get_product(name: str) -> dict:
    if name not in PRODUCTS:
        raise KeyError(f"Unknown product: {name}. Available: {list(PRODUCTS)}")
    return PRODUCTS[name]


def list_products() -> list[str]:
    return list(PRODUCTS.keys())


def get_framework_version() -> str:
    return FRAMEWORK_VERSION
