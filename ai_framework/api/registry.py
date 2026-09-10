# CODING: utf-8, ASCII only
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import json
import re
import functools

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

APIRegistry = EndpointRegistry
Registry = EndpointRegistry
registry = EndpointRegistry()

# --- C5.1 Product registry + C5.2 enrichment ---
@dataclass(frozen=True)
class ProductInfo:
    name: str
    product: str
    version: str
    package: str
    description: str
    path: Path
    # C5.2 enrichment - optional, backward compatible
    pyproject_name: Optional[str] = None
    pyproject_version: Optional[str] = None
    requires_python: Optional[str] = None

def _showcases_root() -> Path:
    return Path(__file__).resolve().parents[2] / "showcases"

def _parse_pyproject(pyproject_path: Path) -> Dict[str, Optional[str]]:
    result: Dict[str, Optional[str]] = {"name": None, "version": None, "requires_python": None}
    if not pyproject_path.exists():
        return result
    try:
        text = pyproject_path.read_text(encoding="utf-8")
        m_name = re.search(r'^\s*name\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
        m_ver = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
        m_req = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', text)
        if m_name:
            result["name"] = m_name.group(1)
        if m_ver:
            result["version"] = m_ver.group(1)
        if m_req:
            result["requires_python"] = m_req.group(1)
    except Exception:
        pass
    return result

def _load_manifest(manifest_path: Path) -> Optional[ProductInfo]:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    name = data.get("name")
    if not name:
        return None
    version = data.get("version") or ""
    package = data.get("package", f"showcases.{name}")
    description = data.get("description", "")

    py_info = _parse_pyproject(manifest_path.parent / "pyproject.toml")
    # version fallback if manifest version empty (legacy)
    if not version and py_info.get("version"):
        version = py_info["version"] or ""

    return ProductInfo(
        name=name,
        product=data.get("product", "crud"),
        version=version,
        package=package,
        description=description,
        path=manifest_path.parent,
        pyproject_name=py_info.get("name"),
        pyproject_version=py_info.get("version"),
        requires_python=py_info.get("requires_python"),
    )

@functools.lru_cache(maxsize=1)
def list_products() -> List[ProductInfo]:
    root = _showcases_root()
    if not root.exists():
        return []
    result: List[ProductInfo] = []
    for manifest_path in sorted(root.glob("*/manifest.json")):
        info = _load_manifest(manifest_path)
        if info is None:
            continue
        result.append(info)
    # deterministic order
    result.sort(key=lambda p: p.name)
    return result

@functools.lru_cache(maxsize=32)
def get_product(name: str) -> Optional[ProductInfo]:
    for p in list_products():
        if p.name == name:
            return p
    return None

def clear_cache() -> None:
    list_products.cache_clear()
    get_product.cache_clear()