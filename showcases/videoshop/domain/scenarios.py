"""Layer 4 scenario rules: the four approved scenarios as data.

The rules are configuration, not code. Every attribute name below is a real key
of ``product_attributes`` (canonical English), every threshold was approved by
the owner, and prices are compared in minor units. Nothing is converted,
guessed or invented; a fact the catalogue cannot answer is listed in ``gaps``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

CATEGORY_CAMERAS = "cameras"
CATEGORY_LENSES = "lenses"
CATEGORY_MICROPHONES = "microphones"
CATEGORY_LIGHTING = "lighting"
CATEGORY_STABILIZERS = "stabilizers"
CATEGORY_TRIPODS = "tripods"

#: the six catalogue categories, in display order
CATEGORY_KEYS: Tuple[str, ...] = (
    CATEGORY_CAMERAS,
    CATEGORY_LENSES,
    CATEGORY_MICROPHONES,
    CATEGORY_LIGHTING,
    CATEGORY_STABILIZERS,
    CATEGORY_TRIPODS,
)

#: rule category key -> live catalogue slug. The shop keeps transliterated
#: slugs (``obektivy``, ``svet``); the rules stay readable in English. Only
#: keys whose live slug differs need an entry here, and ``cameras`` doubles
#: as both a rule key and a live slug.
CATEGORY_ALIASES: Mapping[str, str] = {
    "lenses": "obektivy",
    "microphones": "mikrofony",
    "lighting": "svet",
    "stabilizers": "stabilizatory",
    "tripods": "shtativy",
}

#: owner-approved manual table: product slug -> lens mount (no schema change)
MOUNT_MAP: Mapping[str, str] = {
    "canon-eos-r5": "RF",
    "sony-alpha-a7-iv": "FE",
    "canon-rf-24-70mm-f-2-8-l-is-usm": "RF",
    "sony-fe-50mm-f-1-4-gm": "FE",
}

#: approved equivalence table: a stored value proves the listed facts
VIDEO_EQUIVALENCES: Mapping[str, Tuple[str, ...]] = {
    "8K": ("gte_4k",),
    "4K60": ("gte_4k",),
}

#: facts the catalogue cannot answer for these scenarios
GAPS: Tuple[str, ...] = (
    "fps",
    "autofocus",
    "iso",
    "weather_sealing",
    "payload_vs_kit_weight",
    "monopod",
)


@dataclass(frozen=True)
class Check:
    """One deterministic predicate over a single attribute."""

    category: str
    attr: str
    op: str
    value: Any
    proxy: str = ""


@dataclass(frozen=True)
class Scenario:
    """One approved scenario rule (JSON-shaped, see the layer 4 contract)."""

    scenario_id: str
    categories: Tuple[str, ...]
    checks: Tuple[Check, ...]
    per_category_limit: int = 3
    order: str = "price_asc"
    optional: Tuple[str, ...] = ()
    gaps: Tuple[str, ...] = ()
    budget_currency: str = "MDL"
    mount_required: bool = True
    mount_map: Mapping[str, str] = field(default_factory=lambda: dict(MOUNT_MAP))
    equivalences: Mapping[str, Tuple[str, ...]] = field(
        default_factory=lambda: dict(VIDEO_EQUIVALENCES)
    )


INTERVIEW = Scenario(
    scenario_id="interview",
    categories=(
        CATEGORY_CAMERAS,
        CATEGORY_LENSES,
        CATEGORY_MICROPHONES,
        CATEGORY_LIGHTING,
        CATEGORY_TRIPODS,
    ),
    checks=(
        Check(CATEGORY_CAMERAS, "Type", "eq", "Full Frame"),
        Check(CATEGORY_LENSES, "Aperture", "num_le", 2.8),
        Check(CATEGORY_MICROPHONES, "Type", "in", ("Lavalier", "Shotgun")),
        Check(CATEGORY_LIGHTING, "Color temp", "contains", "-"),
        Check(CATEGORY_TRIPODS, "Head", "eq", "Fluid head"),
    ),
    per_category_limit=3,
)

VLOG = Scenario(
    scenario_id="vlog",
    categories=(CATEGORY_CAMERAS, CATEGORY_LENSES, CATEGORY_MICROPHONES, CATEGORY_STABILIZERS),
    optional=(CATEGORY_STABILIZERS,),
    checks=(
        Check(CATEGORY_CAMERAS, "Stabilization", "eq", "IBIS"),
        Check(CATEGORY_LENSES, "Type", "eq", "Fix"),
        Check(CATEGORY_MICROPHONES, "Type", "eq", "Lavalier"),
        Check(CATEGORY_STABILIZERS, "Type", "eq", "3-axis gimbal"),
    ),
    per_category_limit=3,
)

WEDDING = Scenario(
    scenario_id="wedding",
    categories=(
        CATEGORY_CAMERAS,
        CATEGORY_LENSES,
        CATEGORY_MICROPHONES,
        CATEGORY_LIGHTING,
        CATEGORY_STABILIZERS,
        CATEGORY_TRIPODS,
    ),
    checks=(
        Check(CATEGORY_CAMERAS, "Type", "eq", "Full Frame"),
        Check(CATEGORY_CAMERAS, "Stabilization", "eq", "IBIS"),
        Check(CATEGORY_LENSES, "Type", "in", ("Zoom", "Fix")),
        Check(CATEGORY_MICROPHONES, "Type", "in", ("Lavalier", "Shotgun")),
        Check(CATEGORY_LIGHTING, "Color temp", "contains", "-"),
        Check(CATEGORY_STABILIZERS, "Type", "eq", "3-axis gimbal"),
        Check(CATEGORY_TRIPODS, "Head", "eq", "Fluid head"),
    ),
    per_category_limit=3,
)

#: the catalogue has no compatible zoom lens for the only 60 fps camera, so this
#: scenario ends with an honest refusal; the rule is intentionally not widened
SPORT = Scenario(
    scenario_id="sport",
    categories=(
        CATEGORY_CAMERAS,
        CATEGORY_LENSES,
        CATEGORY_MICROPHONES,
        CATEGORY_STABILIZERS,
    ),
    checks=(
        Check(CATEGORY_CAMERAS, "Stabilization", "eq", "IBIS"),
        Check(CATEGORY_CAMERAS, "Video", "contains", "60", proxy="fps"),
        Check(CATEGORY_LENSES, "Type", "eq", "Zoom"),
        Check(CATEGORY_LENSES, "Aperture", "num_le", 2.8),
        Check(CATEGORY_MICROPHONES, "Type", "eq", "Shotgun"),
        Check(CATEGORY_STABILIZERS, "Type", "eq", "3-axis gimbal"),
    ),
    per_category_limit=2,
    gaps=("fps", "autofocus"),
)

SCENARIOS: Tuple[Scenario, ...] = (INTERVIEW, VLOG, WEDDING, SPORT)
SCENARIOS_BY_ID = {scenario.scenario_id: scenario for scenario in SCENARIOS}
