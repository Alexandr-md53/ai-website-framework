"""Store configuration: the product mode is separate from the theme and from
the capabilities it enables.

The contract (block 3a) fixes three modes:

* ``visitka`` - landing page + request form, no public catalogue;
* ``catalog`` - public catalogue and product pages, no cart (the default and
  the historical behaviour of this slice);
* ``shop``    - catalogue + cart flag (cart/checkout implementation is a later
  block; the flag only describes intent here).

``StoreConfig`` is the single source of truth: routes and templates read the
computed properties, never the raw mode. Unknown modes raise a typed error
instead of silently falling back, so a typo in ``VIDEOSHOP_STORE_MODE`` can
never publish a shop as a visitka card.
"""
from __future__ import annotations

import dataclasses
import os
from typing import Dict, Mapping, Optional, Tuple

MODE_VISITKA = "visitka"
MODE_CATALOG = "catalog"
MODE_SHOP = "shop"

MODES: Tuple[str, ...] = (MODE_VISITKA, MODE_CATALOG, MODE_SHOP)
DEFAULT_MODE = MODE_CATALOG
MODE_ENV_VAR = "VIDEOSHOP_STORE_MODE"


class StoreConfigError(ValueError):
    """Base error for store configuration problems (typed, never silent)."""


class UnknownStoreMode(StoreConfigError):
    """Raised when a mode is not one of :data:`MODES`."""


class StoreConfigConflict(StoreConfigError):
    """Raised when explicit feature overrides contradict the chosen mode."""


#: mode -> capability defaults (before explicit overrides)
_MODES: Dict[str, Mapping[str, bool]] = {
    MODE_VISITKA: {
        "public_catalog": False,
        "product_page": False,
        "request_form": True,
        "cart": False,
        "subscription": False,
        "admin_products": True,
        "admin_pages": True,
        "media": True,
    },
    MODE_CATALOG: {
        "public_catalog": True,
        "product_page": True,
        "request_form": False,
        "cart": False,
        "subscription": True,
        "admin_products": True,
        "admin_pages": True,
        "media": True,
    },
    MODE_SHOP: {
        "public_catalog": True,
        "product_page": True,
        "request_form": False,
        "cart": True,
        "subscription": True,
        "admin_products": True,
        "admin_pages": True,
        "media": True,
    },
}

_FEATURES: Tuple[str, ...] = (
    "public_catalog",
    "product_page",
    "request_form",
    "cart",
    "subscription",
    "admin_products",
    "admin_pages",
    "media",
)


@dataclasses.dataclass(frozen=True)
class StoreConfig:
    """Immutable store configuration (default: the current catalogue shop)."""

    mode: str = DEFAULT_MODE
    enable_public_catalog: Optional[bool] = None
    enable_product_page: Optional[bool] = None
    enable_request_form: Optional[bool] = None
    enable_cart: Optional[bool] = None
    enable_subscription: Optional[bool] = None
    enable_admin_products: Optional[bool] = None
    enable_admin_pages: Optional[bool] = None

    # -- validation ------------------------------------------------------
    def __post_init__(self) -> None:
        mode = (self.mode or "").strip().lower()
        if mode not in MODES:
            raise UnknownStoreMode(
                f"unknown store mode {self.mode!r}; expected one of {', '.join(MODES)}"
            )
        if mode != self.mode:
            object.__setattr__(self, "mode", mode)
        flags = self.to_flags()
        if flags["cart"] and not flags["public_catalog"]:
            raise StoreConfigConflict("a cart requires a public catalogue")
        if flags["product_page"] and not flags["public_catalog"]:
            raise StoreConfigConflict("product pages require a public catalogue")
        if self.mode == MODE_VISITKA and flags["public_catalog"]:
            raise StoreConfigConflict(
                "mode 'visitka' has no public catalogue; use 'catalog' for that"
            )

    # -- computed capabilities --------------------------------------------
    def to_flags(self) -> Dict[str, bool]:
        """All capabilities as a plain dict (templates consume this)."""
        base = dict(_MODES[self.mode])
        for feature in _FEATURES:
            override = getattr(self, f"enable_{feature}", None)
            if override is not None:
                base[feature] = bool(override)
        # product pages are meaningless without a public catalogue
        if not base["public_catalog"]:
            base["product_page"] = False
        return base

    def feature(self, name: str) -> bool:
        try:
            return self.to_flags()[name]
        except KeyError as exc:  # pragma: no cover - programming error
            raise StoreConfigError(f"unknown feature {name!r}") from exc

    @property
    def public_catalog(self) -> bool:
        return self.feature("public_catalog")

    @property
    def product_page(self) -> bool:
        return self.feature("product_page")

    @property
    def request_form(self) -> bool:
        return self.feature("request_form")

    @property
    def cart(self) -> bool:
        return self.feature("cart")

    @property
    def subscription(self) -> bool:
        return self.feature("subscription")

    @property
    def admin_products(self) -> bool:
        return self.feature("admin_products")

    @property
    def admin_pages(self) -> bool:
        return self.feature("admin_pages")

    @property
    def media(self) -> bool:
        return self.feature("media")


def from_env(name: str = MODE_ENV_VAR, env: Optional[Mapping[str, str]] = None) -> StoreConfig:
    """Build a config from the environment (unknown value -> typed error)."""
    source = os.environ if env is None else env
    raw = (source.get(name) or "").strip()
    return StoreConfig(mode=raw or DEFAULT_MODE)


def default_store_config() -> StoreConfig:
    return StoreConfig()
