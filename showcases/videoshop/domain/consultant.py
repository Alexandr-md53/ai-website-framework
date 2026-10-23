"""Deterministic kit consultant for the VideoShop catalogue (layer 4 MVP).

Pure functions only: the engine receives already-loaded products plus the
scenario rules, performs no I/O, and never fabricates a fact. Every value it
reports comes from ``Product.attribute_rows``; what the catalogue cannot answer
is reported as a gap (``gaps``) instead of being filled in.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .scenarios import (
    CATEGORY_CAMERAS,
    CATEGORY_LENSES,
    Check,
    Scenario,
    VIDEO_EQUIVALENCES,
)

STATUS_FULL = "full"
STATUS_PARTIAL = "partial"
STATUS_INCOMPATIBLE = "incompatible"
STATUS_NO_DATA = "no_data"
STATUS_OVER_BUDGET = "over_budget"
STATUS_EMPTY = "empty"

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def format_minor(minor: int, currency: str) -> str:
    """Render minor units as ``140 980 MDL`` (no locale dependency)."""
    whole, cents = divmod(int(minor), 100)
    grouped = "{:,}".format(whole).replace(",", " ")
    return f"{grouped}.{cents:02d} {currency}" if cents else f"{grouped} {currency}"


def normalize_number(attr: str, raw: Optional[str]) -> Optional[float]:
    """Numeric reading of a free-text attribute value, or ``None``."""
    text = (raw or "").strip().lower()
    if not text:
        return None
    if attr == "Aperture":
        match = _NUMBER.search(text.replace("f/", ""))
        return float(match.group().replace(",", ".")) if match else None
    match = _NUMBER.search(text.replace("sm", "cm"))
    if match is None:
        return None
    value = float(match.group().replace(",", "."))
    if attr in ("Weight", "Payload", "Load capacity") and "kg" in text:
        return value * 1000
    return value


def match_value(attr: str, raw: Optional[str], op: str, expected: Any) -> bool:
    """Apply one deterministic operator to one stored value."""
    if op == "eq":
        return (raw or "") == expected
    if op == "in":
        return (raw or "") in tuple(expected)
    if op == "contains":
        return str(expected) in (raw or "")
    if op == "num_le":
        number = normalize_number(attr, raw)
        return number is not None and number <= expected
    if op == "num_ge":
        number = normalize_number(attr, raw)
        return number is not None and number >= expected
    if op == "equiv":
        return str(expected) in VIDEO_EQUIVALENCES.get((raw or "").strip(), ())
    raise ValueError(f"unknown operator {op!r}")


def facts(product: Any, lang: str = "en") -> Dict[str, str]:
    """Canonical attribute pairs; rules are written against the English names."""
    pairs = {name: value for name, value in product.attributes_for("en")}
    if pairs:
        return pairs
    return {name: value for name, value in product.attributes_for(lang)}


@dataclass(frozen=True)
class RecomItem:
    product: Any
    matched: Tuple[Tuple[str, str], ...]


@dataclass(frozen=True)
class RecomGroup:
    key: str
    items: Tuple[RecomItem, ...]


@dataclass(frozen=True)
class Recommendation:
    scenario_id: str
    status: str
    currency: str
    groups: Tuple[RecomGroup, ...]
    optional_groups: Tuple[RecomGroup, ...]
    total_minor: int
    total_display: str
    min_total_minor: int
    min_total_display: str
    missing_keys: Tuple[str, ...]
    already_have: Tuple[str, ...]
    proxy_used: bool
    mount_missing: bool
    gaps: Tuple[str, ...]


def _matched(scenario: Scenario, key: str, pairs: Mapping[str, str]) -> Tuple[Tuple[str, str], ...]:
    return tuple(
        (check.attr, pairs.get(check.attr, ""))
        for check in scenario.checks
        if check.category == key
    )


def _candidates(
    products: Iterable[Any],
    scenario: Scenario,
    key: str,
    category_id: Optional[int],
    lang: str,
) -> List[Tuple[Any, Dict[str, str]]]:
    if category_id is None:
        return []
    checks = [check for check in scenario.checks if check.category == key]
    found: List[Tuple[Any, Dict[str, str]]] = []
    for product in products:
        if not product.is_published or product.category_id != category_id:
            continue
        pairs = facts(product, lang)
        if all(match_value(check.attr, pairs.get(check.attr), check.op, check.value) for check in checks):
            found.append((product, pairs))
    found.sort(key=lambda pair: (pair[0].price.minor, pair[0].id))
    return found


def recommend(
    products: Iterable[Any],
    scenario: Scenario,
    *,
    category_ids: Mapping[str, int],
    budget_minor: Optional[int] = None,
    already_have: Sequence[str] = (),
    lang: str = "en",
) -> Recommendation:
    """Pick a kit for one scenario, or report honestly why it is impossible."""
    products = tuple(products)
    owned = set(already_have)
    have = tuple(key for key in scenario.categories if key in owned)
    required = tuple(
        key for key in scenario.categories if key not in owned and key not in scenario.optional
    )
    optional_keys = tuple(key for key in scenario.optional if key not in owned)

    pools = {
        key: _candidates(products, scenario, key, category_ids.get(key), lang)
        for key in required + optional_keys
    }
    blocked: Dict[str, str] = {}
    incompatible = False
    no_data = False

    if scenario.mount_required and CATEGORY_CAMERAS in scenario.categories and CATEGORY_LENSES in scenario.categories:
        needs_camera = CATEGORY_CAMERAS in required
        needs_lens = CATEGORY_LENSES in required
        if needs_camera and needs_lens:
            known_cameras = [(p, m) for p, m in pools[CATEGORY_CAMERAS] if scenario.mount_map.get(p.slug)]
            known_lenses = [(p, m) for p, m in pools[CATEGORY_LENSES] if scenario.mount_map.get(p.slug)]
            unknown = (
                len(known_cameras) != len(pools[CATEGORY_CAMERAS])
                or len(known_lenses) != len(pools[CATEGORY_LENSES])
            )
            camera_mounts = {scenario.mount_map[p.slug] for p, _ in known_cameras}
            lens_mounts = {scenario.mount_map[p.slug] for p, _ in known_lenses}
            shared = camera_mounts & lens_mounts
            if known_cameras and known_lenses and not shared:
                incompatible = True
            else:
                pools[CATEGORY_CAMERAS] = [
                    pair for pair in known_cameras if scenario.mount_map[pair[0].slug] in shared
                ]
                pools[CATEGORY_LENSES] = [
                    pair for pair in known_lenses if scenario.mount_map[pair[0].slug] in shared
                ]
                if unknown and (not pools[CATEGORY_CAMERAS] or not pools[CATEGORY_LENSES]):
                    no_data = True
        elif needs_lens and CATEGORY_CAMERAS in have:
            # the mount of the owned camera is unknown: fail closed
            blocked[CATEGORY_LENSES] = "mount"
            no_data = True
        elif needs_camera and CATEGORY_LENSES in have:
            blocked[CATEGORY_CAMERAS] = "mount"
            no_data = True

    missing = tuple(
        key for key in required if key in blocked or not pools.get(key)
    )
    available = [key for key in required if key in pools and pools[key] and key not in blocked]

    chosen = [(key,) + pools[key][0] for key in available]
    min_total = sum(product.price.minor for _, product, _ in chosen)
    over_budget = bool(chosen) and budget_minor is not None and min_total > budget_minor

    if incompatible:
        status = STATUS_INCOMPATIBLE
    elif no_data:
        status = STATUS_NO_DATA
    elif not chosen:
        status = STATUS_EMPTY
    elif over_budget:
        status = STATUS_OVER_BUDGET
    elif missing:
        status = STATUS_PARTIAL
    else:
        status = STATUS_FULL

    groups: Tuple[RecomGroup, ...] = ()
    optional_groups: Tuple[RecomGroup, ...] = ()
    if status in (STATUS_FULL, STATUS_PARTIAL, STATUS_NO_DATA):
        order = {key: index for index, key in enumerate(required)}
        groups = tuple(
            RecomGroup(
                key=key,
                items=tuple(
                    RecomItem(product=product, matched=_matched(scenario, key, pairs))
                    for product, pairs in pools[key][: scenario.per_category_limit]
                ),
            )
            for key in sorted(available, key=lambda item: order[item])
        )
        optional_groups = tuple(
            RecomGroup(
                key=key,
                items=tuple(
                    RecomItem(product=product, matched=_matched(scenario, key, pairs))
                    for product, pairs in pools[key][: scenario.per_category_limit]
                ),
            )
            for key in optional_keys
            if pools.get(key)
        )

    currency = scenario.budget_currency
    return Recommendation(
        scenario_id=scenario.scenario_id,
        status=status,
        currency=currency,
        groups=groups,
        optional_groups=optional_groups,
        total_minor=min_total,
        total_display=format_minor(min_total, currency),
        min_total_minor=min_total,
        min_total_display=format_minor(min_total, currency),
        missing_keys=missing,
        already_have=have,
        proxy_used=any(check.proxy for check in scenario.checks),
        mount_missing=no_data and CATEGORY_LENSES in blocked,
        gaps=scenario.gaps,
    )
