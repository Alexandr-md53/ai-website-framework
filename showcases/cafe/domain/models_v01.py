"""
Cafe Vertical v0.1 — Domain Contract — showcase-local, not framework

Evidence gate: Publishable NOT reused, cafe-local DRAFT/PUBLISHED with own lifecycle.
Slug VO reused from ai_framework/content/slug.py (proven primitive).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List, Optional


# ---- Slug VO reuse (copy validation from framework to avoid import coupling) ----
# Framework Slug regex: lowercase alphanumeric + hyphen, no traversal
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FORBIDDEN_SLUGS = {"..", ".", ""}


def validate_slug(slug: str) -> str:
    if not slug or not isinstance(slug, str):
        raise ValueError("Slug must be non-empty string")
    if "/" in slug or "\\" in slug or ".." in slug:
        raise ValueError(f"Invalid slug traversal: {slug}")
    if not _SLUG_RE.match(slug):
        raise ValueError(f"Invalid slug format: {slug} — must match {_SLUG_RE.pattern}")
    if slug in _FORBIDDEN_SLUGS:
        raise ValueError(f"Forbidden slug: {slug}")
    return slug


class MenuItemStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


@dataclass
class SeoMeta:
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    canonical_url: Optional[str] = None


@dataclass
class MenuCategory:
    id: uuid.UUID
    name: str
    slug: str
    is_published: bool = False

    def __post_init__(self):
        self.slug = validate_slug(self.slug)
        if not self.name or len(self.name.strip()) < 2:
            raise ValueError("Category name must be >=2 chars")


@dataclass
class MenuItem:
    id: uuid.UUID
    title: str
    slug: str
    description: str
    price: Decimal
    category_id: uuid.UUID
    stock_quantity: Optional[int] = None  # None = unlimited
    is_published: bool = False
    seo: Optional[SeoMeta] = None
    dietary_tags: List[str] = field(default_factory=list)
    status: MenuItemStatus = MenuItemStatus.DRAFT

    def __post_init__(self):
        self.slug = validate_slug(self.slug)
        if not self.title or len(self.title.strip()) < 2:
            raise ValueError("Title must be >=2 chars")
        if not self.description or len(self.description.strip()) < 10:
            # publish requires >=10, but draft can have shorter? Enforce for publish gate in service
            if (
                self.status == MenuItemStatus.PUBLISHED
                and len(self.description.strip()) < 10
            ):
                raise ValueError("Description must be >=10 for published")
        if self.price <= Decimal("0"):
            raise ValueError("Price must be >0")
        if self.stock_quantity is not None and self.stock_quantity < 0:
            raise ValueError("stock_quantity must be >=0")

    @property
    def is_available(self) -> bool:
        if not self.is_published:
            return False
        if self.stock_quantity is None:
            return True
        return self.stock_quantity > 0

    def can_publish(self) -> bool:
        return len(self.description.strip()) >= 10 and self.price > Decimal("0")


@dataclass
class OrderLine:
    menu_item_id: uuid.UUID
    quantity: int
    price_snapshot: Decimal

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("quantity must be >0")
        if self.price_snapshot <= Decimal("0"):
            raise ValueError("price_snapshot must be >0")


@dataclass
class Order:
    id: uuid.UUID
    lines: List[OrderLine]
    total: Decimal
    status: OrderStatus = OrderStatus.DRAFT
    created_at: Optional[str] = None

    def __post_init__(self):
        if not self.lines:
            raise ValueError("Order must have at least 1 line")
        # total server-calculated, verify
        calc = sum((l.price_snapshot * l.quantity for l in self.lines), Decimal("0"))
        if calc != self.total:
            raise ValueError(f"Total mismatch: calc {calc} vs {self.total}")
