"""VideoShop product-slice domain: money, languages and validation.

Design rules (approved product-slice scope):

* money is exact: amounts are stored as integer **minor units** plus an ISO-4217
  style currency code. ``float`` is rejected everywhere - parsing goes through
  ``decimal.Decimal`` and only integer minor units reach the database;
* the catalog model is universal: a product has a slug, a category, a price, a
  publication flag, per-language texts and an arbitrary ordered list of
  name/value attributes. Nothing about cameras, clothes or electronics is
  hard-coded, so any assortment fits the same model and the same code;
* languages are data, not code: the shop configures them (first example RU/RO/EN)
  and picks a default; the architecture is not limited to two or three.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

LANG_PATTERN = re.compile(r"^[a-z]{2}(?:-[a-z]{2})?$")
CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
MINOR_UNITS = 2
PRICE_MAX_MINOR = 10**12

DEFAULT_LANGUAGES: Tuple[Tuple[str, str], ...] = (
    ("ru", "Русский"),
    ("ro", "Română"),
    ("en", "English"),
)
DEFAULT_LANGUAGE = "ru"
#: content languages whose names every product must carry
CONTENT_LANGUAGES: Tuple[str, ...] = ("en", "ru", "ro")


class CatalogError(Exception):
    """Base error of the catalog domain."""

    code = "CATALOG_ERROR"


class ValidationError(CatalogError, ValueError):
    code = "VALIDATION_ERROR"


class NotFoundError(CatalogError):
    code = "NOT_FOUND"


class CategoryInUseError(CatalogError):
    code = "CATEGORY_IN_USE"

    def __init__(self, category_id: int, product_count: int, reassign_hint: str = "") -> None:
        self.category_id = category_id
        self.product_count = product_count
        message = (
            f"{self.code}: category {category_id} still holds {product_count} "
            f"product(s); products are never destroyed by deleting a category"
        )
        if reassign_hint:
            message += f" ({reassign_hint})"
        super().__init__(message)


class DuplicateSlugError(CatalogError):
    code = "DUPLICATE_SLUG"


@dataclass(frozen=True)
class Money:
    """Exact money value: integer minor units + currency code."""

    minor: int
    currency: str

    def __post_init__(self) -> None:
        if isinstance(self.minor, bool) or not isinstance(self.minor, int):
            raise ValidationError("price must be an integer number of minor units (never float)")
        if self.minor < 0 or self.minor > PRICE_MAX_MINOR:
            raise ValidationError(f"price must be within 0..{PRICE_MAX_MINOR} minor units")
        if not CURRENCY_PATTERN.match(self.currency or ""):
            raise ValidationError(
                f"currency must be a 3-letter uppercase code, got {self.currency!r}"
            )

    @property
    def decimal(self) -> Decimal:
        return (Decimal(self.minor) / (10**MINOR_UNITS)).quantize(
            Decimal(1).scaleb(-MINOR_UNITS)
        )

    def format(self) -> str:
        return f"{self.decimal:.{MINOR_UNITS}f} {self.currency}"

    @classmethod
    def parse(cls, amount, currency: str) -> "Money":
        """Parse an admin-supplied amount (str/Decimal/int) into exact minor units."""
        if isinstance(amount, bool):
            raise ValidationError("price must be a number, got bool")
        if isinstance(amount, float):
            raise ValidationError(
                "price must not be a float; send a decimal string such as '19.99'"
            )
        if isinstance(amount, int):
            value = Decimal(amount)
        elif isinstance(amount, Decimal):
            value = amount
        elif isinstance(amount, str):
            text = amount.strip().replace(",", ".")
            if not text:
                raise ValidationError("price is required")
            try:
                value = Decimal(text)
            except InvalidOperation as exc:
                raise ValidationError(f"price {amount!r} is not a decimal number") from exc
        else:
            raise ValidationError(f"unsupported price type {type(amount).__name__}")
        if value.is_nan() or value.is_infinite():
            raise ValidationError("price must be a finite number")
        if value < 0:
            raise ValidationError("price must not be negative")
        quantized = value.quantize(Decimal(1).scaleb(-MINOR_UNITS), rounding=ROUND_HALF_UP)
        minor = int(quantized.scaleb(MINOR_UNITS))
        return cls(minor=minor, currency=currency)


def validate_language(code: str) -> str:
    value = (code or "").strip().lower()
    if not LANG_PATTERN.match(value):
        raise ValidationError(f"language code must look like 'ru' or 'pt-br', got {code!r}")
    return value


def validate_text(value: Optional[str], *, field_name: str, max_length: int = 2000, required: bool = True) -> str:
    text = (value or "").strip()
    if required and not text:
        raise ValidationError(f"{field_name} is required")
    if len(text) > max_length:
        raise ValidationError(f"{field_name} must be at most {max_length} characters")
    return text


#: the master language of the characteristics table (block 3b-1-fix-TABLE)
ATTRIBUTE_MASTER_LANGUAGE = "en"


def _effective_pairs(
    rows: Iterable, lang: str, fallback: str = DEFAULT_LANGUAGE
) -> Tuple[Tuple[str, str], ...]:
    """Rows for ``lang``, else the master language, plus neutral rows.

    Block 3b-1-fix-TABLE: English is the master column of the characteristics
    table, so a language without rows of its own falls back to ``en`` before the
    language-neutral rows. Neutral rows stay additive, as decision R1 requires.
    """
    rows = tuple(rows or ())
    if not rows:
        return ()
    selected = (lang or "").strip().lower()
    localized = [(name, value) for row_lang, name, value in rows if row_lang == selected]
    if not localized and selected != ATTRIBUTE_MASTER_LANGUAGE:
        localized = [
            (name, value)
            for row_lang, name, value in rows
            if row_lang == ATTRIBUTE_MASTER_LANGUAGE
        ]
    neutral = [(name, value) for row_lang, name, value in rows if row_lang == ""]
    seen = {name.casefold() for name, _value in localized}
    return tuple(localized + [(n, v) for n, v in neutral if n.casefold() not in seen])


def normalize_attribute_rows(raw: Iterable) -> List[Tuple[str, str, str]]:
    """Normalise ``(lang, name, value)`` rows.

    Accepts 2-tuples (language-neutral), 3-tuples and dicts. Empty names are
    dropped, the order is preserved.
    """
    result: List[Tuple[str, str, str]] = []
    for item in raw or ():
        if isinstance(item, dict):
            lang, name, value = item.get("lang", ""), item.get("name"), item.get("value")
        elif isinstance(item, (list, tuple)) and len(item) == 3:
            lang, name, value = item
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            lang, (name, value) = "", item
        else:
            raise ValidationError(f"attribute must be a (lang, name, value) row, got {item!r}")
        name_text = (name or "").strip()
        if not name_text:
            continue
        if len(name_text) > 80:
            raise ValidationError("attribute name must be at most 80 characters")
        value_text = (value or "").strip()
        if len(value_text) > 200:
            raise ValidationError("attribute value must be at most 200 characters")
        lang_text = (lang or "").strip().lower()
        if lang_text:
            lang_text = validate_language(lang_text)
        result.append((lang_text, name_text, value_text))
    return result


def _attribute_cell(cell: Any) -> Tuple[str, str]:
    """``(name, value)`` of one table cell, stripped."""
    if isinstance(cell, dict):
        name, value = cell.get("name"), cell.get("value")
    elif isinstance(cell, (list, tuple)) and len(cell) == 2:
        name, value = cell
    elif cell is None:
        name, value = None, None
    else:
        raise ValidationError(f"attribute cell must be a (name, value) pair, got {cell!r}")
    return str(name or "").strip(), str(value or "").strip()


def fill_attribute_translations(
    groups: Iterable[Sequence[Any]],
    languages: Sequence[str] = ("en", "ru", "ro"),
) -> List[Tuple[str, str, str]]:
    """Expand ``(en, ru, ro)`` cell groups into attribute rows.

    Block 3b-1-fix-TABLE. The first language is the master column: a group is
    stored only when its master name is present, and an empty translation copies
    the master name and value. Rows keep the group order so the stored
    ``position`` follows the table.
    """
    languages = tuple(languages) or ("en",)
    result: List[Tuple[str, str, str]] = []
    for cells in groups or ():
        cells = list(cells or ())
        cells += [(None, None)] * (len(languages) - len(cells))
        master_name, master_value = _attribute_cell(cells[0])
        if not master_name:
            continue
        for index, lang in enumerate(languages):
            if index == 0:
                name, value = master_name, master_value
            else:
                name, value = _attribute_cell(cells[index])
                name, value = name or master_name, value or master_value
            result.append((lang, name, value))
    return result


def normalize_attributes(raw: Iterable) -> List[Tuple[str, str]]:
    """Normalise attribute pairs; empty names are dropped, order is preserved."""
    result: List[Tuple[str, str]] = []
    for item in raw or ():
        if isinstance(item, dict):
            name, value = item.get("name"), item.get("value")
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            name, value = item
        else:
            raise ValidationError(f"attribute must be a name/value pair, got {item!r}")
        name_text = (name or "").strip()
        if not name_text:
            continue
        if len(name_text) > 80:
            raise ValidationError("attribute name must be at most 80 characters")
        value_text = (value or "").strip()
        if len(value_text) > 200:
            raise ValidationError("attribute value must be at most 200 characters")
        result.append((name_text, value_text))
    return result


@dataclass(frozen=True)
class CategoryText:
    lang: str
    name: str
    description: str = ""


@dataclass(frozen=True)
class ProductText:
    lang: str
    name: str
    description: str = ""


@dataclass(frozen=True)
class ProductImage:
    id: int
    file_name: str
    original_name: str
    content_type: str
    size_bytes: int
    position: int
    #: preset derivative names (filled by the service; empty when unavailable)
    catalog_name: str = ""
    detail_name: str = ""


@dataclass(frozen=True)
class Product:
    id: int
    slug: str
    category_id: Optional[int]
    price: Money
    is_published: bool
    texts: Dict[str, ProductText] = field(default_factory=dict)
    attributes: Tuple[Tuple[str, str], ...] = ()
    #: ``(lang, name, value)`` rows; ``lang == ""`` means language-neutral
    attribute_rows: Tuple[Tuple[str, str, str], ...] = ()

    def attributes_for(
        self, lang: str, fallback: str = DEFAULT_LANGUAGE
    ) -> Tuple[Tuple[str, str], ...]:
        """Effective attributes: exact language -> neutral -> hide (decision R1)."""
        return _effective_pairs(self.attribute_rows, lang, fallback)
    images: Tuple[ProductImage, ...] = ()

    def text(self, lang: str, fallback: str = DEFAULT_LANGUAGE) -> ProductText:
        if lang in self.texts:
            return self.texts[lang]
        if fallback in self.texts:
            return self.texts[fallback]
        if self.texts:
            return next(iter(self.texts.values()))
        return ProductText(lang=lang, name=self.slug)

    def has_text(self, lang: str) -> bool:
        """True when a localization row for ``lang`` exists (not a fallback)."""
        return lang in self.texts

    def description(self, lang: str) -> str:
        """Description stored for ``lang`` itself; never the fallback language."""
        text = self.texts.get(lang)
        return text.description if text is not None else ""

    def attribute_count(self, lang: str) -> int:
        """Attribute rows of ``lang`` with a non-empty name."""
        return sum(
            1
            for row_lang, name, _value in self.attribute_rows
            if row_lang == lang and (name or "").strip()
        )


@dataclass(frozen=True)
class Category:
    id: int
    slug: str
    is_published: bool
    position: int
    texts: Dict[str, CategoryText] = field(default_factory=dict)
    #: main photo shown in the storefront grid (managed or packaged name)
    image: str = ""

    def text(self, lang: str, fallback: str = DEFAULT_LANGUAGE) -> CategoryText:
        if lang in self.texts:
            return self.texts[lang]
        if fallback in self.texts:
            return self.texts[fallback]
        if self.texts:
            return next(iter(self.texts.values()))
        return CategoryText(lang=lang, name=self.slug)


class RequestValidationError(ValidationError):
    """A request-form validation failure with a translatable ``code``."""

    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code


#: lifecycle states of a request submitted through the public request form
REQUEST_STATES: Tuple[str, ...] = ("new", "in_progress", "done", "spam")


@dataclass(frozen=True)
class StoreRequest:
    """A request from the public request form (visitka mode)."""

    id: int
    name: str
    contact: str
    message: str
    source_lang: str
    state: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class PageText:
    lang: str
    title: str
    body: str = ""


@dataclass(frozen=True)
class Page:
    """An informational page (about/contacts/delivery): texts are data."""

    id: int
    slug: str
    is_published: bool
    position: int
    texts: Dict[str, PageText] = field(default_factory=dict)

    def text(self, lang: str, fallback: str = DEFAULT_LANGUAGE) -> PageText:
        if lang in self.texts:
            return self.texts[lang]
        if fallback in self.texts:
            return self.texts[fallback]
        if self.texts:
            return next(iter(self.texts.values()))
        return PageText(lang=lang, title=self.slug)


@dataclass(frozen=True)
class ShopSettings:
    """Settings of THIS shop (step 3.2): not part of the template mechanism."""

    name: str
    description: str
    logo: str
    contact_email: str
    contact_phone: str
    contact_address: str
    default_language: str
    languages: Tuple[Tuple[str, str], ...]
    #: shop-wide currency default (Nursery keeps the same idea in SiteSettings)
    default_currency: str = "MDL"
    #: short business tagline (Nursery: SiteSettings.tagline)
    tagline: str = ""
    #: public social links (Nursery keeps the same columns in SiteSettings)
    social_facebook: str = ""
    social_instagram: str = ""
    social_telegram: str = ""
    #: site-wide SEO defaults, injected through the framework SeoInjector
    seo_title: str = ""
    seo_description: str = ""

    @property
    def language_codes(self) -> Tuple[str, ...]:
        return tuple(code for code, _ in self.languages)
