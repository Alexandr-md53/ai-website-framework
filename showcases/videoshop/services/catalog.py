"""VideoShop catalog service: the admin manages the assortment through data.

The service is the single place where the catalog is written. Rules:

* every write runs in ONE transaction through the S6 retry wrapper, so a failed
  save never leaves a product half-created (texts, attributes and images are
  written in the same scope as the product row);
* the live slug is never duplicated: it lives in the S3 ``slug_registry`` and is
  read back with a join; creating/renaming/deleting an entity uses the registry
  primitives inside the same transaction (``within(tx)``);
* deleting a category that still holds products is REFUSED unless the caller
  explicitly passes ``reassign_to`` - products are never destroyed or orphaned;
* uploaded image files are stored BEFORE the database row (a bad file never
  reaches the database) and removed again if the row cannot be written; on
  product/image deletion the files are removed after the commit (file deletion
  cannot be transactional);
* demo data is inserted only when the catalog is completely empty, so user data
  is never overwritten.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from ..domain.catalog import (
    _effective_pairs,
    CONTENT_LANGUAGES,
    normalize_attribute_rows,
    RequestValidationError,
    REQUEST_STATES,
    StoreRequest,
    Category,
    CategoryInUseError,
    CategoryText,
    DEFAULT_LANGUAGE,
    DEFAULT_LANGUAGES,
    Money,
    NotFoundError,
    Page,
    PageText,
    Product,
    ProductImage,
    ProductText,
    ShopSettings,
    ValidationError,
    normalize_attributes,
    validate_language,
    validate_text,
)
from ..infrastructure.image_store import STORED_NAME_PATTERN, ImageStore
from ..infrastructure.migrations.catalog import (
    CATALOG_VERSION,
    migrate_catalog,
)
from ..infrastructure.retry import run_transaction_with_retry
from ..infrastructure.slug_registry import (
    SlugRegistry,
    SlugTaken,
    normalize_slug,
    validate_slug,
)
from .entity_lifecycle import EntityLifecycleService

PRODUCT_TYPE = "product"
CATEGORY_TYPE = "category"
PAGE_TYPE = "page"

SETTING_KEYS = (
    "shop_name",
    "shop_description",
    "shop_logo",
    "contact_email",
    "contact_phone",
    "contact_address",
    "default_currency",
    "tagline",
    "social_facebook",
    "social_instagram",
    "social_telegram",
    "seo_title",
    "seo_description",
)

#: settings validated as public http(s) links
SOCIAL_KEYS = ("social_facebook", "social_instagram", "social_telegram")

_SOCIAL_URL = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)

#: sentinel for "argument not provided" in partial updates
UNSET: Any = object()

#: convenience transliteration for the admin slug field (the framework slug VO
#: deliberately does NOT transliterate; this only pre-fills the form and the
#: admin can always overwrite it)
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "ă": "a", "â": "a", "î": "i", "ș": "s", "ş": "s", "ț": "t", "ţ": "t",
}

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slugify(text: str) -> str:
    """Suggest a slug-safe string; the admin may always overwrite it."""
    lowered = (text or "").strip().lower()
    transliterated = "".join(_TRANSLIT.get(char, char) for char in lowered)
    decomposed = unicodedata.normalize("NFKD", transliterated)
    ascii_only = decomposed.encode("ascii", "ignore").decode("ascii")
    collapsed = _NON_SLUG.sub("-", ascii_only).strip("-")
    return collapsed[:200].strip("-")


class CatalogService:
    """Catalog operations used by the admin panel and the public site."""

    def __init__(
        self,
        provider: Any,
        registry: SlugRegistry,
        images: ImageStore,
        *,
        default_language: str = DEFAULT_LANGUAGE,
    ) -> None:
        self._provider = provider
        self._registry = registry
        self._images = images
        #: informational pages reuse the S4 resolver (slug history + one hop)
        self._pages_lifecycle = EntityLifecycleService(provider, registry, PAGE_TYPE, "pages")
        self._default_language = validate_language(default_language)
        self._products = EntityLifecycleService(provider, registry, PRODUCT_TYPE, "products")

    # --- schema ---------------------------------------------------------

    def migrate(self) -> int:
        return migrate_catalog(self._provider)

    @property
    def schema_version(self) -> int:
        return CATALOG_VERSION

    # --- helpers --------------------------------------------------------

    @staticmethod
    def _require_slug(raw: Optional[str], fallback_text: str) -> str:
        candidate = (raw or "").strip() or slugify(fallback_text)
        if not candidate:
            raise ValidationError(
                "a slug is required (the name has no latin characters to derive one)"
            )
        try:
            return validate_slug(normalize_slug(candidate))
        except Exception as exc:  # InvalidSlug from the registry
            raise ValidationError(f"invalid slug {candidate!r}: {exc}") from exc

    @staticmethod
    def _normalize_texts(raw: Optional[Mapping], *, required: bool) -> Dict[str, Tuple[str, str]]:
        if raw is None:
            return {}
        if not isinstance(raw, Mapping):
            raise ValidationError("texts must be a mapping of language code to name/description")
        texts: Dict[str, Tuple[str, str]] = {}
        for lang, value in raw.items():
            code = validate_language(lang)
            if isinstance(value, Mapping):
                name, description = value.get("name"), value.get("description", "")
            elif isinstance(value, (list, tuple)) and len(value) == 2:
                name, description = value
            else:
                raise ValidationError(f"text for {code!r} must be a name/description pair")
            if not (name or "").strip() and not required:
                continue
            texts[code] = (
                validate_text(name, field_name=f"name[{code}]", required=required),
                validate_text(description, field_name=f"description[{code}]", required=False, max_length=8000),
            )
        return texts

    def _row_to_image(self, row: Any) -> ProductImage:
        file_name = row["file_name"]
        # packaged storefront assets (product-1.jpg, category-*.jpg) have no
        # generated derivatives; only managed uploads get preset variants
        managed = bool(STORED_NAME_PATTERN.match(file_name or ""))
        return ProductImage(
            id=int(row["id"]),
            file_name=file_name,
            original_name=row["original_name"],
            content_type=row["content_type"],
            size_bytes=int(row["size_bytes"]),
            position=int(row["position"]),
            catalog_name=(
                self._images.variant_name(file_name, "catalog") if managed else file_name
            ),
            detail_name=(
                self._images.variant_name(file_name, "detail") if managed else file_name
            ),
        )

    # --- settings (the shop itself, step 3.2) ---------------------------

    def list_languages(self) -> Tuple[Tuple[str, str], ...]:
        with self._provider.read_transaction() as tx:
            rows = tx.fetchall(
                "SELECT code, title FROM shop_languages ORDER BY position, code"
            )
        return tuple((row["code"], row["title"]) for row in rows)

    def get_settings(self) -> ShopSettings:
        with self._provider.read_transaction() as tx:
            values = {
                row["key"]: row["value"]
                for row in tx.fetchall("SELECT key, value FROM shop_settings")
            }
            default_row = tx.fetchone(
                "SELECT code FROM shop_languages WHERE is_default = 1"
            )
            languages = tuple(
                (row["code"], row["title"])
                for row in tx.fetchall(
                    "SELECT code, title FROM shop_languages ORDER BY position, code"
                )
            )
        default_language = (
            default_row["code"] if default_row is not None else self._default_language
        )
        currency = (values.get("default_currency") or "MDL").strip().upper()
        try:
            Money(minor=0, currency=currency)
        except ValidationError:
            currency = "MDL"
        return ShopSettings(
            name=values.get("shop_name", ""),
            description=values.get("shop_description", ""),
            logo=values.get("shop_logo", ""),
            contact_email=values.get("contact_email", ""),
            contact_phone=values.get("contact_phone", ""),
            contact_address=values.get("contact_address", ""),
            default_language=default_language,
            languages=languages or DEFAULT_LANGUAGES,
            default_currency=currency,
            tagline=values.get("tagline", ""),
            social_facebook=values.get("social_facebook", ""),
            social_instagram=values.get("social_instagram", ""),
            social_telegram=values.get("social_telegram", ""),
            seo_title=values.get("seo_title", ""),
            seo_description=values.get("seo_description", ""),
        )

    def update_settings(self, values: Mapping[str, Any]) -> ShopSettings:
        cleaned: Dict[str, str] = {}
        for key in SETTING_KEYS:
            if key not in values:
                continue
            raw = values.get(key) or ""
            if key == "default_currency":
                currency = str(raw).strip().upper()
                if not currency:
                    continue  # an empty field means "keep the current value"
                Money(minor=0, currency=currency)  # validates the code
                cleaned[key] = currency
                continue
            if key in SOCIAL_KEYS:
                link = str(raw).strip()
                if link and not _SOCIAL_URL.match(link):
                    raise ValidationError(
                        f"{key} must be a public http(s) link, got {link!r}"
                    )
                cleaned[key] = link
                continue
            cleaned[key] = validate_text(
                str(raw), field_name=key, required=False, max_length=2000
            )

        def operation(tx):
            for key, value in cleaned.items():
                tx.execute(
                    "INSERT INTO shop_settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, value),
                )
            return len(cleaned)

        run_transaction_with_retry(self._provider, operation)
        return self.get_settings()

    def set_languages(
        self, languages: Sequence[Tuple[str, str]], default_language: Optional[str] = None
    ) -> ShopSettings:
        pairs: List[Tuple[str, str]] = []
        for item in languages:
            code = validate_language(item[0])
            title = validate_text(item[1], field_name=f"language title[{code}]", max_length=80)
            if any(code == existing for existing, _ in pairs):
                raise ValidationError(f"duplicate language {code!r}")
            pairs.append((code, title))
        if not pairs:
            raise ValidationError("at least one language must be configured")
        codes = [code for code, _ in pairs]
        default = validate_language(default_language or codes[0])
        if default not in codes:
            raise ValidationError(f"default language {default!r} is not in the configured list")

        def operation(tx):
            tx.execute("DELETE FROM shop_languages")
            for position, (code, title) in enumerate(pairs):
                tx.execute(
                    "INSERT INTO shop_languages (code, title, position, is_default) "
                    "VALUES (?, ?, ?, ?)",
                    (code, title, position, 1 if code == default else 0),
                )
            return len(pairs)

        run_transaction_with_retry(self._provider, operation)
        return self.get_settings()

    # --- categories -----------------------------------------------------

    def _load_categories(self, tx: Any, rows: Sequence[Any]) -> List[Category]:
        if not rows:
            return []
        ids = [int(row["id"]) for row in rows]
        placeholders = ", ".join("?" for _ in ids)
        texts: Dict[int, Dict[str, CategoryText]] = {category_id: {} for category_id in ids}
        for row in tx.fetchall(
            f"SELECT category_id, lang, name, description FROM category_texts "
            f"WHERE category_id IN ({placeholders})",
            tuple(ids),
        ):
            texts[int(row["category_id"])][row["lang"]] = CategoryText(
                lang=row["lang"], name=row["name"], description=row["description"]
            )
        return [
            Category(
                id=int(row["id"]),
                slug=row["live_slug"] or "",
                is_published=bool(row["is_published"]),
                position=int(row["position"]),
                texts=texts[int(row["id"])],
                image=row["image"] or "",
            )
            for row in rows
        ]

    def list_categories(
        self, *, published_only: bool = False, q: Optional[str] = None
    ) -> List[Category]:
        query = (
            "SELECT c.*, r.slug AS live_slug FROM categories c "
            f"LEFT JOIN slug_registry r ON r.entity_type = '{CATEGORY_TYPE}' "
            "AND r.entity_id = c.id AND r.state = 'live' "
        )
        conditions: List[str] = []
        params: List[Any] = []
        if published_only:
            conditions.append("c.is_published = 1")
        term = (q or "").strip()
        if term:
            # SQLite's LIKE is case-insensitive for ASCII only, which breaks
            # Cyrillic and Romanian searches; the loaded rows are filtered
            # below with Unicode-aware casefold instead.
            pass
        if conditions:
            query += "WHERE " + " AND ".join(conditions) + " "
        query += "ORDER BY c.position, c.id"
        with self._provider.read_transaction() as tx:
            rows = tx.fetchall(query, tuple(params))
            categories = self._load_categories(tx, rows)
        needle = (q or "").strip().casefold()
        if not needle:
            return categories
        return [
            category
            for category in categories
            if needle in (category.slug or "").casefold()
            or any(needle in (text.name or "").casefold() for text in category.texts.values())
        ]

    def get_category(self, category_id: int) -> Category:
        with self._provider.read_transaction() as tx:
            row = tx.fetchone(
                "SELECT c.*, r.slug AS live_slug FROM categories c "
                f"LEFT JOIN slug_registry r ON r.entity_type = '{CATEGORY_TYPE}' "
                "AND r.entity_id = c.id AND r.state = 'live' WHERE c.id = ?",
                (category_id,),
            )
            if row is None:
                raise NotFoundError(f"category {category_id} does not exist")
            return self._load_categories(tx, [row])[0]

    def create_category(
        self,
        *,
        slug: Optional[str] = None,
        texts: Optional[Mapping] = None,
        is_published: bool = True,
        position: int = 0,
        image: str = "",
    ) -> Category:
        normalized = self._normalize_texts(texts, required=True)
        if self._default_language not in normalized and normalized:
            first_lang, (name, description) = next(iter(normalized.items()))
            normalized.setdefault(self._default_language, (name, description))
        if not normalized:
            raise ValidationError("a category name is required")
        reference_name = normalized[self._default_language][0]
        final_slug = self._require_slug(slug, reference_name)

        def operation(tx):
            cursor = tx.execute(
                "INSERT INTO categories (is_published, position, image, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (1 if is_published else 0, int(position), (image or "").strip(), _now(), _now()),
            )
            category_id = int(cursor.lastrowid)
            self._registry.within(tx).register(CATEGORY_TYPE, final_slug, category_id)
            for lang, (name, description) in normalized.items():
                tx.execute(
                    "INSERT INTO category_texts (category_id, lang, name, description) "
                    "VALUES (?, ?, ?, ?)",
                    (category_id, lang, name, description),
                )
            return category_id

        try:
            category_id = run_transaction_with_retry(self._provider, operation)
        except SlugTaken as exc:
            raise ValidationError(f"the slug is not available: {exc}") from exc
        return self.get_category(category_id)

    def update_category(
        self,
        category_id: int,
        *,
        slug: Optional[str] = None,
        texts: Optional[Mapping] = None,
        is_published: Optional[bool] = None,
        position: Optional[int] = None,
        image: Any = UNSET,
    ) -> Category:
        self.get_category(category_id)
        normalized = self._normalize_texts(texts, required=True) if texts is not None else None
        final_slug = None
        if slug is not None:
            final_slug = self._require_slug(slug, "")

        def operation(tx):
            session = self._registry.within(tx)
            if final_slug is not None:
                current = session.live_slug(CATEGORY_TYPE, category_id)
                if current is None:
                    session.register(CATEGORY_TYPE, final_slug, category_id)
                elif current != final_slug:
                    session.replace_slug(CATEGORY_TYPE, category_id, current, final_slug)
            if normalized:
                tx.execute("DELETE FROM category_texts WHERE category_id = ?", (category_id,))
                for lang, (name, description) in normalized.items():
                    tx.execute(
                        "INSERT INTO category_texts (category_id, lang, name, description) "
                        "VALUES (?, ?, ?, ?)",
                        (category_id, lang, name, description),
                    )
            sets: List[str] = []
            params: List[Any] = []
            if is_published is not None:
                sets.append("is_published = ?")
                params.append(1 if is_published else 0)
            if position is not None:
                sets.append("position = ?")
                params.append(int(position))
            if image is not UNSET:
                sets.append("image = ?")
                params.append((image or "").strip())
            sets.append("updated_at = ?")
            params.append(_now())
            params.append(category_id)
            tx.execute(f"UPDATE categories SET {', '.join(sets)} WHERE id = ?", tuple(params))
            return category_id

        try:
            run_transaction_with_retry(self._provider, operation)
        except SlugTaken as exc:
            raise ValidationError(f"the slug is not available: {exc}") from exc
        return self.get_category(category_id)

    def delete_category(self, category_id: int, *, reassign_to: Optional[int] = None) -> dict:
        """Delete a category safely: never destroys or orphans products."""
        self.get_category(category_id)
        if reassign_to is not None and int(reassign_to) == int(category_id):
            raise ValidationError("reassign_to must be a different category")

        def operation(tx):
            product_count = int(
                tx.scalar("SELECT COUNT(*) FROM products WHERE category_id = ?", (category_id,))
            )
            if product_count and reassign_to is None:
                raise CategoryInUseError(
                    category_id,
                    product_count,
                    "pass reassign_to=<category id> to move the products first",
                )
            moved = 0
            if reassign_to is not None:
                target = tx.fetchone("SELECT id FROM categories WHERE id = ?", (reassign_to,))
                if target is None:
                    raise NotFoundError(f"target category {reassign_to} does not exist")
                cursor = tx.execute(
                    "UPDATE products SET category_id = ?, updated_at = ? WHERE category_id = ?",
                    (int(reassign_to), _now(), category_id),
                )
                moved = int(cursor.rowcount or 0)
            slug = self._registry.within(tx).live_slug(CATEGORY_TYPE, category_id)
            if slug is not None:
                self._registry.within(tx).release(CATEGORY_TYPE, slug, category_id)
            tx.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            return {"category_id": category_id, "moved_products": moved, "released_slug": slug}

        return run_transaction_with_retry(self._provider, operation)

    # --- products -------------------------------------------------------

    def _load_products(self, tx: Any, rows: Sequence[Any]) -> List[Product]:
        if not rows:
            return []
        ids = [int(row["id"]) for row in rows]
        placeholders = ", ".join("?" for _ in ids)
        texts: Dict[int, Dict[str, ProductText]] = {product_id: {} for product_id in ids}
        attribute_rows: Dict[int, List[Tuple[str, str, str]]] = {product_id: [] for product_id in ids}
        images: Dict[int, List[ProductImage]] = {product_id: [] for product_id in ids}
        for row in tx.fetchall(
            f"SELECT product_id, lang, name, description FROM product_texts "
            f"WHERE product_id IN ({placeholders})",
            tuple(ids),
        ):
            texts[int(row["product_id"])][row["lang"]] = ProductText(
                lang=row["lang"], name=row["name"], description=row["description"]
            )
        for row in tx.fetchall(
            f"SELECT product_id, lang, name, value FROM product_attributes "
            f"WHERE product_id IN ({placeholders}) ORDER BY position, id",
            tuple(ids),
        ):
            attribute_rows.setdefault(int(row["product_id"]), []).append((row["lang"], row["name"], row["value"]))
        for row in tx.fetchall(
            f"SELECT * FROM product_images WHERE product_id IN ({placeholders}) "
            f"ORDER BY position, id",
            tuple(ids),
        ):
            images[int(row["product_id"])].append(self._row_to_image(row))
        return [
            Product(
                id=int(row["id"]),
                slug=row["live_slug"] or "",
                category_id=None if row["category_id"] is None else int(row["category_id"]),
                price=Money(minor=int(row["price_minor"]), currency=row["currency"]),
                is_published=bool(row["is_published"]),
                texts=texts[int(row["id"])],
                attributes=_effective_pairs(attribute_rows.get(int(row["id"]), ()), DEFAULT_LANGUAGE),
                attribute_rows=tuple(attribute_rows.get(int(row["id"]), ())),
                images=tuple(images[int(row["id"])]),
            )
            for row in rows
        ]

    def list_products(
        self,
        *,
        category_id: Optional[int] = None,
        published_only: bool = False,
        q: Optional[str] = None,
        incomplete: bool = False,
    ) -> List[Product]:
        query = (
            "SELECT p.*, r.slug AS live_slug FROM products p "
            f"LEFT JOIN slug_registry r ON r.entity_type = '{PRODUCT_TYPE}' "
            "AND r.entity_id = p.id AND r.state = 'live' "
        )
        conditions: List[str] = []
        params: List[Any] = []
        if published_only:
            conditions.append("p.is_published = 1")
        if category_id is not None:
            conditions.append("p.category_id = ?")
            params.append(int(category_id))
        term = (q or "").strip()
        if term:
            # products are filtered in Python below (Unicode-aware, see the
            # categories implementation); the database keeps only the cheap
            # structural conditions here
            pass
        if conditions:
            query += "WHERE " + " AND ".join(conditions) + " "
        query += "ORDER BY p.position, p.id"
        with self._provider.read_transaction() as tx:
            rows = tx.fetchall(query, tuple(params))
            products = self._load_products(tx, rows)
        needle = (q or "").strip().casefold()
        if not needle and not incomplete:
            return products
        # phase 2: an incomplete product misses a name for at least one of
        # CONTENT_LANGUAGES; descriptions and attributes are only warnings
        # and therefore never take part in this filter
        selected: List[Product] = []
        for product in products:
            if incomplete and all(
                product.has_text(code) for code in CONTENT_LANGUAGES
            ):
                continue
            if needle and not (
                needle in (product.slug or "").casefold()
                or any(needle in (text.name or "").casefold() for text in product.texts.values())
            ):
                continue
            selected.append(product)
        return selected

    def get_product(self, product_id: int) -> Product:
        with self._provider.read_transaction() as tx:
            row = tx.fetchone(
                "SELECT p.*, r.slug AS live_slug FROM products p "
                f"LEFT JOIN slug_registry r ON r.entity_type = '{PRODUCT_TYPE}' "
                "AND r.entity_id = p.id AND r.state = 'live' WHERE p.id = ?",
                (product_id,),
            )
            if row is None:
                raise NotFoundError(f"product {product_id} does not exist")
            return self._load_products(tx, [row])[0]

    def resolve_product(self, slug: str) -> Tuple[Optional[Product], Optional[str]]:
        """Return ``(product, redirect_slug)`` for a public URL.

        Historical slugs resolve directly to the current live product (one hop,
        reuse of the S4 resolver). Unknown or unpublished products yield
        ``(None, None)``.
        """
        try:
            resolution = self._products.resolve(slug)
        except Exception:
            return None, None
        if resolution.is_not_found:
            return None, None
        product = self.get_product(int(resolution.entity_id))
        if not product.is_published:
            return None, None
        if resolution.is_redirect:
            return product, resolution.current_slug
        return product, None

    def create_product(
        self,
        *,
        slug: Optional[str] = None,
        category_id: Optional[int] = None,
        price: Any = None,
        currency: str = "MDL",
        texts: Optional[Mapping] = None,
        attributes: Iterable = (),
        is_published: bool = False,
        position: int = 0,
    ) -> Product:
        normalized = self._normalize_texts(texts, required=True)
        if not normalized:
            raise ValidationError("a product name is required")
        if self._default_language not in normalized:
            first_lang, (name, description) = next(iter(normalized.items()))
            normalized.setdefault(self._default_language, (name, description))
        money = Money.parse(price, currency)
        final_slug = self._require_slug(slug, normalized[self._default_language][0])
        pairs = normalize_attribute_rows(attributes)

        def operation(tx):
            if category_id is not None:
                if tx.fetchone("SELECT id FROM categories WHERE id = ?", (category_id,)) is None:
                    raise NotFoundError(f"category {category_id} does not exist")
            cursor = tx.execute(
                "INSERT INTO products "
                "(category_id, price_minor, currency, is_published, position, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    None if category_id is None else int(category_id),
                    money.minor,
                    money.currency,
                    1 if is_published else 0,
                    int(position),
                    _now(),
                    _now(),
                ),
            )
            product_id = int(cursor.lastrowid)
            self._registry.within(tx).register(PRODUCT_TYPE, final_slug, product_id)
            for lang, (name, description) in normalized.items():
                tx.execute(
                    "INSERT INTO product_texts (product_id, lang, name, description) "
                    "VALUES (?, ?, ?, ?)",
                    (product_id, lang, name, description),
                )
            for index, (lang, name, value) in enumerate(pairs):
                tx.execute(
                    "INSERT INTO product_attributes (product_id, position, lang, name, value) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (product_id, index, lang, name, value),
                )
            return product_id

        try:
            product_id = run_transaction_with_retry(self._provider, operation)
        except SlugTaken as exc:
            raise ValidationError(f"the slug is not available: {exc}") from exc
        return self.get_product(product_id)

    def update_product(
        self,
        product_id: int,
        *,
        slug: Optional[str] = None,
        category_id: Any = UNSET,
        price: Any = UNSET,
        currency: Any = UNSET,
        texts: Optional[Mapping] = None,
        attributes: Any = UNSET,
        is_published: Optional[bool] = None,
        position: Optional[int] = None,
    ) -> Product:
        current = self.get_product(product_id)
        normalized = self._normalize_texts(texts, required=True) if texts is not None else None
        pairs = normalize_attribute_rows(attributes) if attributes is not UNSET else None
        money = None
        if price is not UNSET:
            money = Money.parse(price, currency if currency is not UNSET else current.price.currency)
        final_slug = self._require_slug(slug, "") if slug is not None else None

        def operation(tx):
            session = self._registry.within(tx)
            if final_slug is not None:
                live = session.live_slug(PRODUCT_TYPE, product_id)
                if live is None:
                    session.register(PRODUCT_TYPE, final_slug, product_id)
                elif live != final_slug:
                    session.replace_slug(PRODUCT_TYPE, product_id, live, final_slug)
            if category_id is not UNSET and category_id is not None:
                if tx.fetchone("SELECT id FROM categories WHERE id = ?", (category_id,)) is None:
                    raise NotFoundError(f"category {category_id} does not exist")
            if normalized:
                tx.execute("DELETE FROM product_texts WHERE product_id = ?", (product_id,))
                for lang, (name, description) in normalized.items():
                    tx.execute(
                        "INSERT INTO product_texts (product_id, lang, name, description) "
                        "VALUES (?, ?, ?, ?)",
                        (product_id, lang, name, description),
                    )
            if pairs is not None:
                # block 3b-1-fix-TABLE: language-neutral rows (lang = '') belong to
                # the owner and are not part of the admin table, so a form save
                # replaces only the localized rows
                tx.execute(
                    "DELETE FROM product_attributes WHERE product_id = ? "
                    "AND lang IN ('ru', 'ro', 'en')",
                    (product_id,),
                )
                for index, (lang, name, value) in enumerate(pairs):
                    tx.execute(
                        "INSERT INTO product_attributes (product_id, position, lang, name, value) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (product_id, index, lang, name, value),
                    )
            sets: List[str] = []
            params: List[Any] = []
            if category_id is not UNSET:
                sets.append("category_id = ?")
                params.append(None if category_id is None else int(category_id))
            if money is not None:
                sets.append("price_minor = ?")
                params.append(money.minor)
                sets.append("currency = ?")
                params.append(money.currency)
            if is_published is not None:
                sets.append("is_published = ?")
                params.append(1 if is_published else 0)
            if position is not None:
                sets.append("position = ?")
                params.append(int(position))
            sets.append("updated_at = ?")
            params.append(_now())
            params.append(product_id)
            tx.execute(f"UPDATE products SET {', '.join(sets)} WHERE id = ?", tuple(params))
            return product_id

        try:
            run_transaction_with_retry(self._provider, operation)
        except SlugTaken as exc:
            raise ValidationError(f"the slug is not available: {exc}") from exc
        return self.get_product(product_id)

    def set_product_published(
        self, product_id: int, published: bool
    ) -> Tuple[Product, List[str]]:
        """Toggle publication; report the languages that have no name row.

        Phase 3: an incomplete product is still published. The missing
        languages travel back as a warning and never turn into a refusal,
        so unpublishing always reports nothing and existing products are
        only inspected at the moment their state is switched.
        """
        product = self.get_product(product_id)
        missing: List[str] = []
        if published:
            missing = [
                code for code in CONTENT_LANGUAGES if not product.has_text(code)
            ]
        return self.update_product(product_id, is_published=bool(published)), missing

    def delete_product(self, product_id: int) -> dict:
        """Release the slug and hard-delete the product (S4/D5 semantics)."""
        product = self.get_product(product_id)
        file_names = [image.file_name for image in product.images]

        def operation(tx):
            session = self._registry.within(tx)
            slug = session.live_slug(PRODUCT_TYPE, product_id)
            if slug is not None:
                session.release(PRODUCT_TYPE, slug, product_id)
            tx.execute("DELETE FROM products WHERE id = ?", (product_id,))
            return {"product_id": product_id, "released_slug": slug}

        result = run_transaction_with_retry(self._provider, operation)
        # files are removed only after the committed delete; an unreferenced file
        # can never break the catalog
        removed = 0
        for file_name in file_names:
            try:
                if self._images.delete(file_name):
                    removed += 1
            except Exception:
                pass
        result["removed_images"] = removed
        return result

    # --- images ---------------------------------------------------------

    def add_product_image(self, product_id: int, content: bytes, *, original_name: str = "") -> ProductImage:
        self.get_product(product_id)
        stored = self._images.save(content, original_name=original_name)

        def operation(tx):
            position = int(
                tx.scalar(
                    "SELECT COALESCE(MAX(position), -1) + 1 FROM product_images WHERE product_id = ?",
                    (product_id,),
                )
            )
            cursor = tx.execute(
                "INSERT INTO product_images "
                "(product_id, file_name, original_name, content_type, size_bytes, position, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    product_id,
                    stored.file_name,
                    stored.original_name,
                    stored.content_type,
                    stored.size_bytes,
                    position,
                    _now(),
                ),
            )
            return int(cursor.lastrowid)

        try:
            image_id = run_transaction_with_retry(self._provider, operation)
        except Exception:
            self._images.delete(stored.file_name)
            raise
        return ProductImage(
            id=image_id,
            file_name=stored.file_name,
            original_name=stored.original_name,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            position=0,
        )

    def delete_product_image(self, product_id: int, image_id: int) -> bool:
        self.get_product(product_id)

        def operation(tx):
            row = tx.fetchone(
                "SELECT file_name FROM product_images WHERE id = ? AND product_id = ?",
                (image_id, product_id),
            )
            if row is None:
                return None
            tx.execute("DELETE FROM product_images WHERE id = ?", (image_id,))
            return row["file_name"]

        file_name = run_transaction_with_retry(self._provider, operation)
        if file_name is None:
            raise NotFoundError(f"image {image_id} does not belong to product {product_id}")
        self._images.delete(file_name)
        return True

    # --- demo data (never overwrites an existing catalog) ---------------

    def seed_demo_catalog(self) -> int:
        """Insert demo data ONLY when the shop is still completely untouched."""
        with self._provider.read_transaction() as tx:
            products = int(tx.scalar("SELECT COUNT(*) FROM products"))
            categories = int(tx.scalar("SELECT COUNT(*) FROM categories"))
            pages = int(tx.scalar("SELECT COUNT(*) FROM pages"))
            languages = int(tx.scalar("SELECT COUNT(*) FROM shop_languages"))
            configured = int(
                tx.scalar(
                    "SELECT COUNT(*) FROM shop_settings WHERE key = 'shop_name' AND value <> ''"
                )
            )
        if products or categories or pages or configured:
            return 0

        if not languages:
            self.set_languages(list(DEFAULT_LANGUAGES), self._default_language)
        if not self.get_settings().name:
            self.update_settings(
                {
                    "shop_name": "VideoShop Demo",
                    "shop_description": "Universal storefront template - demo assortment",
                    "contact_email": "shop@example.com",
                    "contact_phone": "",
                    "contact_address": "",
                    "default_currency": "MDL",
                }
            )

        cameras = self.create_category(
            slug="cameras",
            image="category-camera.jpg",
            texts={
                "ru": {"name": "Камеры", "description": "Фото и видеокамеры"},
                "ro": {"name": "Camere", "description": "Camere foto si video"},
                "en": {"name": "Cameras", "description": "Photo and video cameras"},
            },
        )
        lenses = self.create_category(
            slug="objektivy",
            image="category-lens.jpg",
            texts={
                "ru": {"name": "Объективы", "description": "Сменная оптика"},
                "ro": {"name": "Obiective", "description": "Optică interschimbabilă"},
                "en": {"name": "Lenses", "description": "Interchangeable optics"},
            },
        )
        self.create_category(
            slug="svet",
            image="category-light.jpg",
            texts={
                "ru": {"name": "Свет", "description": "Панели, софтбоксы, вспышки"},
                "ro": {"name": "Lumină", "description": "Panouri, softbox, flash"},
                "en": {"name": "Light", "description": "Panels, softboxes, flashes"},
            },
        )
        self.create_category(
            slug="zvuk",
            image="category-mic.png",
            texts={
                "ru": {"name": "Звук", "description": "Микрофоны и петлички"},
                "ro": {"name": "Sunet", "description": "Microfoane și lavaliere"},
                "en": {"name": "Sound", "description": "Microphones and lavaliers"},
            },
        )
        tripods = self.create_category(
            slug="shtativy",
            image="category-tripod.jpg",
            texts={
                "ru": {"name": "Штативы", "description": "Штативы и головы"},
                "ro": {"name": "Treppiede", "description": "Treppiede și capete"},
                "en": {"name": "Tripods", "description": "Tripods and heads"},
            },
        )
        self.create_category(
            slug="stabilizatory",
            image="category-gimbal.jpg",
            texts={
                "ru": {"name": "Стабилизаторы", "description": "Гимбалы и стабилизация"},
                "ro": {"name": "Stabilizatoare", "description": "Gimbaluri și stabilizare"},
                "en": {"name": "Gimbals", "description": "Gimbals and stabilisation"},
            },
        )
        accessories = lenses
        self.create_product(
            slug="demo-camera-x100",
            category_id=cameras.id,
            price="1299.00",
            currency="MDL",
            texts={
                "ru": {"name": "Камера X100", "description": "Компактная камера с фиксированным объективом"},
                "en": {"name": "Camera X100", "description": "Compact camera with a fixed lens"},
            },
            attributes=[("Сенсор", "APS-C"), ("Видео", "4K/30p"), ("Вес", "480 г")],
            is_published=True,
        )
        self.create_product(
            slug="demo-camera-pro",
            category_id=cameras.id,
            price="2499.50",
            currency="MDL",
            texts={"ru": {"name": "Камера Pro", "description": "Полнокадровая камера"}},
            attributes=[("Сенсор", "Full Frame"), ("Стабилизация", "IBIS")],
            is_published=True,
        )
        self.create_product(
            slug="demo-tripod",
            category_id=tripods.id,
            price="59.99",
            currency="MDL",
            texts={"ru": {"name": "Штатив", "description": "Алюминиевый штатив"}},
            attributes=[("Высота", "160 см"), ("Материал", "Алюминий")],
            is_published=True,
        )
        # demo photos: packaged assets are imported through the normal image
        # pipeline, so the storefront shows real photos out of the box
        from pathlib import Path as _Path

        media_dir = _Path(__file__).resolve().parents[1] / "web" / "static" / "media"
        photos = ("product-1.jpg", "product-2.jpg", "product-3.jpg")
        for product, photo in zip(self.list_products(), photos):
            source = media_dir / photo
            try:
                if source.is_file():
                    self.add_product_image(product.id, source.read_bytes(), original_name=photo)
            except Exception:  # demo photos must never break seeding
                continue
        return 3


    # --- requests (public request form, block 3a) -----------------------

    def _row_to_request(self, row: Any) -> StoreRequest:
        return StoreRequest(
            id=int(row["id"]),
            name=row["name"],
            contact=row["contact"],
            message=row["message"],
            source_lang=row["source_lang"],
            state=row["state"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def add_request(
        self,
        *,
        name: str,
        contact: str,
        message: str = "",
        source_lang: str = "",
    ) -> StoreRequest:
        """Validate and store a public request (state is always ``new``)."""
        name_text = (name or "").strip()
        if not name_text:
            raise RequestValidationError("request_err_name_required", "name is required")
        if len(name_text) > 120:
            raise RequestValidationError("request_err_name_long", "name is too long")
        contact_text = (contact or "").strip()
        if not contact_text:
            raise RequestValidationError("request_err_contact_required", "contact is required")
        if len(contact_text) > 200:
            raise RequestValidationError("request_err_contact_long", "contact is too long")
        message_text = (message or "").strip()
        if len(message_text) > 2000:
            raise RequestValidationError("request_err_message_long", "message is too long")
        language = (source_lang or "").strip().lower()
        known = {code for code, _title in self.list_languages()}
        if language not in known:
            language = self.get_settings().default_language
        now = _now()

        def operation(tx):
            cursor = tx.execute(
                "INSERT INTO requests "
                "(name, contact, message, source_lang, state, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, 'new', ?, ?)",
                (name_text, contact_text, message_text, language, now, now),
            )
            return int(cursor.lastrowid)

        request_id = run_transaction_with_retry(self._provider, operation)
        return self.get_request(request_id)

    def get_request(self, request_id: int) -> StoreRequest:
        with self._provider.read_transaction() as tx:
            row = tx.fetchone("SELECT * FROM requests WHERE id = ?", (int(request_id),))
            if row is None:
                raise NotFoundError(f"request {request_id} does not exist")
            return self._row_to_request(row)

    def list_requests(self, *, state: Optional[str] = None, limit: int = 200) -> List[StoreRequest]:
        query = "SELECT * FROM requests"
        params: List[Any] = []
        if state:
            query += " WHERE state = ?"
            params.append(state)
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(int(limit))
        with self._provider.read_transaction() as tx:
            return [self._row_to_request(row) for row in tx.fetchall(query, tuple(params))]

    def set_request_state(self, request_id: int, state: str) -> StoreRequest:
        candidate = (state or "").strip().lower()
        if candidate not in REQUEST_STATES:
            raise ValidationError(f"unknown request state: {state!r}")
        self.get_request(request_id)

        def operation(tx):
            tx.execute(
                "UPDATE requests SET state = ?, updated_at = ? WHERE id = ?",
                (candidate, _now(), int(request_id)),
            )
            return int(request_id)

        run_transaction_with_retry(self._provider, operation)
        return self.get_request(request_id)

    def ensure_contacts_page(self) -> Page:
        """Create the contacts page (request form anchor) if it is missing."""
        for page in self.list_pages():
            if page.slug == "contacts":
                return page
        return self.create_page(
            slug="contacts",
            texts={
                "ru": {
                    "title": "Контакты",
                    "body": "Напишите нам через форму ниже — ответим в рабочее время.",
                },
                "ro": {
                    "title": "Contacte",
                    "body": "Scrieți-ne prin formularul de mai jos — răspundem în timpul programului.",
                },
                "en": {
                    "title": "Contacts",
                    "body": "Write to us through the form below — we answer during business hours.",
                },
            },
            is_published=True,
        )

    # --- informational pages (about / contacts / delivery ...) ----------

    @staticmethod
    def _normalize_page_texts(
        raw: Optional[Mapping], *, required: bool = True
    ) -> Dict[str, Tuple[str, str]]:
        if raw is None:
            return {}
        if not isinstance(raw, Mapping):
            raise ValidationError("texts must be a mapping of language code to title/body")
        texts: Dict[str, Tuple[str, str]] = {}
        for lang, value in raw.items():
            code = validate_language(lang)
            if isinstance(value, Mapping):
                title, body = value.get("title"), value.get("body", "")
            elif isinstance(value, (list, tuple)) and len(value) == 2:
                title, body = value
            else:
                raise ValidationError(f"text for {code!r} must be a title/body pair")
            if not (title or "").strip() and not required:
                continue
            texts[code] = (
                validate_text(title, field_name=f"title[{code}]", required=required, max_length=200),
                validate_text(body, field_name=f"body[{code}]", required=False, max_length=20000),
            )
        return texts

    def _load_pages(self, tx: Any, rows: Sequence[Any]) -> List[Page]:
        if not rows:
            return []
        ids = [int(row["id"]) for row in rows]
        placeholders = ", ".join("?" for _ in ids)
        texts: Dict[int, Dict[str, PageText]] = {page_id: {} for page_id in ids}
        for row in tx.fetchall(
            f"SELECT page_id, lang, title, body FROM page_texts "
            f"WHERE page_id IN ({placeholders})",
            tuple(ids),
        ):
            texts[int(row["page_id"])][row["lang"]] = PageText(
                lang=row["lang"], title=row["title"], body=row["body"]
            )
        return [
            Page(
                id=int(row["id"]),
                slug=row["live_slug"] or "",
                is_published=bool(row["is_published"]),
                position=int(row["position"]),
                texts=texts[int(row["id"])],
            )
            for row in rows
        ]

    def list_pages(self, *, published_only: bool = False) -> List[Page]:
        query = (
            "SELECT p.*, r.slug AS live_slug FROM pages p "
            f"LEFT JOIN slug_registry r ON r.entity_type = '{PAGE_TYPE}' "
            "AND r.entity_id = p.id AND r.state = 'live' "
        )
        if published_only:
            query += "WHERE p.is_published = 1 "
        query += "ORDER BY p.position, p.id"
        with self._provider.read_transaction() as tx:
            return self._load_pages(tx, tx.fetchall(query))

    def get_page(self, page_id: int) -> Page:
        with self._provider.read_transaction() as tx:
            row = tx.fetchone(
                "SELECT p.*, r.slug AS live_slug FROM pages p "
                f"LEFT JOIN slug_registry r ON r.entity_type = '{PAGE_TYPE}' "
                "AND r.entity_id = p.id AND r.state = 'live' WHERE p.id = ?",
                (page_id,),
            )
            if row is None:
                raise NotFoundError(f"page {page_id} does not exist")
            return self._load_pages(tx, [row])[0]

    def create_page(
        self,
        *,
        slug: Optional[str] = None,
        texts: Optional[Mapping] = None,
        is_published: bool = True,
        position: int = 0,
    ) -> Page:
        normalized = self._normalize_page_texts(texts, required=True)
        if not normalized:
            raise ValidationError("a page title is required")
        if self._default_language not in normalized:
            first_lang, (title, body) = next(iter(normalized.items()))
            normalized.setdefault(self._default_language, (title, body))
        final_slug = self._require_slug(slug, normalized[self._default_language][0])

        def operation(tx):
            cursor = tx.execute(
                "INSERT INTO pages (is_published, position, created_at, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (1 if is_published else 0, int(position), _now(), _now()),
            )
            page_id = int(cursor.lastrowid)
            self._registry.within(tx).register(PAGE_TYPE, final_slug, page_id)
            for lang, (title, body) in normalized.items():
                tx.execute(
                    "INSERT INTO page_texts (page_id, lang, title, body) VALUES (?, ?, ?, ?)",
                    (page_id, lang, title, body),
                )
            return page_id

        try:
            page_id = run_transaction_with_retry(self._provider, operation)
        except SlugTaken as exc:
            raise ValidationError(f"the slug is not available: {exc}") from exc
        return self.get_page(page_id)

    def update_page(
        self,
        page_id: int,
        *,
        slug: Optional[str] = None,
        texts: Optional[Mapping] = None,
        is_published: Optional[bool] = None,
        position: Optional[int] = None,
    ) -> Page:
        self.get_page(page_id)
        normalized = self._normalize_page_texts(texts, required=True) if texts is not None else None
        final_slug = self._require_slug(slug, "") if slug is not None else None

        def operation(tx):
            session = self._registry.within(tx)
            if final_slug is not None:
                current = session.live_slug(PAGE_TYPE, page_id)
                if current is None:
                    session.register(PAGE_TYPE, final_slug, page_id)
                elif current != final_slug:
                    session.replace_slug(PAGE_TYPE, page_id, current, final_slug)
            if normalized:
                tx.execute("DELETE FROM page_texts WHERE page_id = ?", (page_id,))
                for lang, (title, body) in normalized.items():
                    tx.execute(
                        "INSERT INTO page_texts (page_id, lang, title, body) VALUES (?, ?, ?, ?)",
                        (page_id, lang, title, body),
                    )
            sets: List[str] = []
            params: List[Any] = []
            if is_published is not None:
                sets.append("is_published = ?")
                params.append(1 if is_published else 0)
            if position is not None:
                sets.append("position = ?")
                params.append(int(position))
            sets.append("updated_at = ?")
            params.append(_now())
            params.append(page_id)
            tx.execute(f"UPDATE pages SET {', '.join(sets)} WHERE id = ?", tuple(params))
            return page_id

        try:
            run_transaction_with_retry(self._provider, operation)
        except SlugTaken as exc:
            raise ValidationError(f"the slug is not available: {exc}") from exc
        return self.get_page(page_id)

    def delete_page(self, page_id: int) -> dict:
        self.get_page(page_id)

        def operation(tx):
            slug = self._registry.within(tx).live_slug(PAGE_TYPE, page_id)
            if slug is not None:
                self._registry.within(tx).release(PAGE_TYPE, slug, page_id)
            tx.execute("DELETE FROM pages WHERE id = ?", (page_id,))
            return {"page_id": page_id, "released_slug": slug}

        return run_transaction_with_retry(self._provider, operation)

    def resolve_page(self, slug: str) -> Tuple[Optional[Page], Optional[str]]:
        """Return ``(page, redirect_slug)`` for a public URL (history one hop)."""
        try:
            resolution = self._pages_lifecycle.resolve(slug)
        except Exception:
            return None, None
        if resolution.is_not_found:
            return None, None
        page = self.get_page(int(resolution.entity_id))
        if not page.is_published:
            return None, None
        if resolution.is_redirect:
            return page, resolution.current_slug
        return page, None
