# coding: utf-8, ASCII only
"""C3.4 - Product/Showcase registry via filesystem discovery."""

from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class ProductInfo:
    name: str
    path: Path
    manifest: dict


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def discover_showcases() -> List[ProductInfo]:
    root = _root() / "showcases"
    result: List[ProductInfo] = []
    if not root.exists():
        return result
    for mf in sorted(root.glob("*/manifest.json")):
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
            result.append(
                ProductInfo(
                    name=data.get("name", mf.parent.name), path=mf, manifest=data
                )
            )
        except Exception:
            continue
    return result


def get_showcase(name: str) -> Optional[ProductInfo]:
    for s in discover_showcases():
        if s.name == name:
            return s
    return None


def framework_manifest() -> Optional[dict]:
    p = _root() / "ai_framework" / "manifest.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None
