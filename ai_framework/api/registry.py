# CODING: utf-8, ASCII only
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import json

from ai_framework.api.endpoint import Endpoint


# --- legacy EndpointRegistry (Phase 10.1 A1.4) - KEEP for adapter/router ---
class EndpointRegistry:
    def __init__(self):
        self.routes: Dict[Tuple[str, str], Endpoint] = {}

    def register(self, method: str, path: str, endpoint: Endpoint) -> None:
        self.routes[(method, path)] = endpoint

    def get(self, method: str, path: str) -> Optional[Endpoint]:
        return self.routes.get((method, path))

    def list(self) -> List[Tuple[str, str]]:
        return list(self.routes.keys())


# backward compat aliases expected by old __init__.py
APIRegistry = EndpointRegistry
Registry = EndpointRegistry
registry = EndpointRegistry  # just in case


# --- NEW C5.1 Product registry - filesystem-only ---
@dataclass(frozen=True)
class ProductInfo:
    name: str
    product: str
    version: str
    package: str
    description: str
    path: Path


def _showcases_root() -> Path:
    # ai_framework/api/registry.py -> parents[2] = project root
    return Path(__file__).resolve().parents[2] / "showcases"


def _load_manifest(manifest_path: Path) -> Optional[ProductInfo]:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    name = data.get("name")
    if not name:
        return None
    # version from manifest, fallback to pyproject.toml will be handled in list_products if needed
    return ProductInfo(
        name=name,
        product=data.get("product", "crud"),
        version=data.get("version", ""),
        package=data.get("package", f"showcases.{name}"),
        description=data.get("description", ""),
        path=manifest_path.parent,
    )


def list_products() -> List[ProductInfo]:
    root = _showcases_root()
    if not root.exists():
        return []
    result: List[ProductInfo] = []
    for manifest_path in sorted(root.glob("*/manifest.json")):
        info = _load_manifest(manifest_path)
        if info is None:
            continue
        # if version missing, try pyproject.toml
        if not info.version:
            pyproj = info.path / "pyproject.toml"
            if pyproj.exists():
                try:
                    text = pyproj.read_text(encoding="utf-8")
                    # simple parse version = "..."
                    import re

                    m = re.search(r'version\s*=\s*["\']([^"\']+)["\']', text)
                    if m:
                        info = ProductInfo(
                            name=info.name,
                            product=info.product,
                            version=m.group(1),
                            package=info.package,
                            description=info.description,
                            path=info.path,
                        )
                except Exception:
                    pass
        result.append(info)
    return result


def get_product(name: str) -> Optional[ProductInfo]:
    for p in list_products():
        if p.name == name:
            return p
    return None
