"""Product-slice schema, applied through the EXISTING migration runner (S3).

This is the catalog schema of the VideoShop product slice. It is deliberately
added as migration **step 3 on top of the S3 steps**, through the same
``migrations.runner`` mechanism (``PRAGMA user_version``, one transaction per
step, idempotent, fail-closed), so:

* ``S3_MIGRATIONS`` and ``SlugRegistry.migrate()`` keep their exact S3-only
  behaviour - the S1-S7 contracts and their tests are untouched;
* callers that need the catalog use :func:`migrate_catalog`, which applies the
  S3 steps plus this step.

The slug itself is NOT duplicated here: the live slug of a product/category is
read from the S3 ``slug_registry`` (design decision D1 - the slug lives in the
registry only). Foreign keys are enforced (S6 enables ``foreign_keys=ON``), so
child rows (texts, attributes, images) cascade with their parent, and deleting a
category can never destroy a product (``ON DELETE SET NULL`` plus an explicit
application-level refusal).
"""
from __future__ import annotations

from typing import Any, Tuple

from .runner import Migration, migrate
from .publications import PUBLICATIONS_MIGRATIONS
from .s3 import S3_MIGRATIONS

#: version of the product-slice catalog schema
#: (3 = catalog, 4 = info pages, 5 = category main photo, 6 = requests, 7 = attributes lang, 8 = cart/orders, 9 = publications core)
CATALOG_VERSION = 9

CATALOG_DDL: Tuple[str, ...] = (
    "CREATE TABLE IF NOT EXISTS shop_settings ("
    " key TEXT PRIMARY KEY,"
    " value TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS shop_languages ("
    " code TEXT PRIMARY KEY,"
    " title TEXT NOT NULL,"
    " position INTEGER NOT NULL DEFAULT 0,"
    " is_default INTEGER NOT NULL DEFAULT 0)",
    "CREATE TABLE IF NOT EXISTS categories ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " is_published INTEGER NOT NULL DEFAULT 1,"
    " position INTEGER NOT NULL DEFAULT 0,"
    " created_at TEXT NOT NULL,"
    " updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS category_texts ("
    " category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,"
    " lang TEXT NOT NULL,"
    " name TEXT NOT NULL,"
    " description TEXT NOT NULL DEFAULT '',"
    " PRIMARY KEY (category_id, lang))",
    "CREATE TABLE IF NOT EXISTS products ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,"
    " price_minor INTEGER NOT NULL,"
    " currency TEXT NOT NULL,"
    " is_published INTEGER NOT NULL DEFAULT 0,"
    " position INTEGER NOT NULL DEFAULT 0,"
    " created_at TEXT NOT NULL,"
    " updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS product_texts ("
    " product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,"
    " lang TEXT NOT NULL,"
    " name TEXT NOT NULL,"
    " description TEXT NOT NULL DEFAULT '',"
    " PRIMARY KEY (product_id, lang))",
    "CREATE TABLE IF NOT EXISTS product_attributes ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,"
    " position INTEGER NOT NULL DEFAULT 0,"
    " name TEXT NOT NULL,"
    " value TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS product_images ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,"
    " file_name TEXT NOT NULL,"
    " original_name TEXT NOT NULL DEFAULT '',"
    " content_type TEXT NOT NULL,"
    " size_bytes INTEGER NOT NULL,"
    " position INTEGER NOT NULL DEFAULT 0,"
    " created_at TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS ix_products_category ON products (category_id)",
    "CREATE INDEX IF NOT EXISTS ix_products_published ON products (is_published, position)",
    "CREATE INDEX IF NOT EXISTS ix_category_texts_lang ON category_texts (lang)",
    "CREATE INDEX IF NOT EXISTS ix_product_texts_lang ON product_texts (lang)",
    "CREATE INDEX IF NOT EXISTS ix_product_attributes_product "
    "ON product_attributes (product_id, position)",
    "CREATE INDEX IF NOT EXISTS ix_product_images_product "
    "ON product_images (product_id, position)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_shop_languages_default "
    "ON shop_languages (is_default) WHERE is_default = 1",
)


def _apply_catalog(tx: Any) -> None:
    for statement in CATALOG_DDL:
        tx.execute(statement)


#: informational pages (about/contacts/delivery...): their texts are DATA, not
#: templates - the lesson the Nursery admin learned late (its contacts and
#: advantages texts live hard-coded in ``templates/components/*.html``)
PAGE_DDL: Tuple[str, ...] = (
    "CREATE TABLE IF NOT EXISTS pages ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " is_published INTEGER NOT NULL DEFAULT 1,"
    " position INTEGER NOT NULL DEFAULT 0,"
    " created_at TEXT NOT NULL,"
    " updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS page_texts ("
    " page_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,"
    " lang TEXT NOT NULL,"
    " title TEXT NOT NULL,"
    " body TEXT NOT NULL DEFAULT '',"
    " PRIMARY KEY (page_id, lang))",
    "CREATE INDEX IF NOT EXISTS ix_page_texts_lang ON page_texts (lang)",
)


def _apply_pages(tx: Any) -> None:
    for statement in PAGE_DDL:
        tx.execute(statement)


#: step 5: a main photo for each category (storefront grid)
CATALOG_IMAGE_DDL: Tuple[str, ...] = (
    "ALTER TABLE categories ADD COLUMN image TEXT NOT NULL DEFAULT ''",
)


def _apply_catalog_image(tx: Any) -> None:
    for statement in CATALOG_IMAGE_DDL:
        tx.execute(statement)


#: step 6: requests submitted through the public request form (block 3a)
REQUESTS_DDL: Tuple[str, ...] = (
    "CREATE TABLE IF NOT EXISTS requests ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " name TEXT NOT NULL,"
    " contact TEXT NOT NULL,"
    " message TEXT NOT NULL DEFAULT '',"
    " source_lang TEXT NOT NULL DEFAULT '',"
    " state TEXT NOT NULL DEFAULT 'new',"
    " created_at TEXT NOT NULL,"
    " updated_at TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS ix_requests_state_created "
    "ON requests (state, created_at DESC)",
)


def _apply_requests(tx: Any) -> None:
    for statement in REQUESTS_DDL:
        tx.execute(statement)


#: step 7: multilingual attributes (lang on product_attributes)
ATTRIBUTES_LANG_DDL: Tuple[str, ...] = (
    "ALTER TABLE product_attributes ADD COLUMN lang TEXT NOT NULL DEFAULT ''",
    "CREATE INDEX IF NOT EXISTS ix_product_attributes_lang "
    "ON product_attributes (product_id, lang, position)",
)


def _apply_attributes_lang(tx: Any) -> None:
    for statement in ATTRIBUTES_LANG_DDL:
        tx.execute(statement)


#: step 8: server-side cart and order tables (block 3c-1; orders used in 3c-2)
CART_ORDER_DDL: Tuple[str, ...] = (
    "CREATE TABLE IF NOT EXISTS carts ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " token TEXT NOT NULL UNIQUE,"
    " created_at TEXT NOT NULL,"
    " updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS cart_items ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " cart_id INTEGER NOT NULL REFERENCES carts(id) ON DELETE CASCADE,"
    " product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,"
    " quantity INTEGER NOT NULL,"
    " added_at TEXT NOT NULL,"
    " UNIQUE(cart_id, product_id))",
    "CREATE TABLE IF NOT EXISTS orders ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " number TEXT NOT NULL UNIQUE,"
    " name TEXT NOT NULL,"
    " contact TEXT NOT NULL,"
    " address TEXT NOT NULL DEFAULT '',"
    " comment TEXT NOT NULL DEFAULT '',"
    " source_lang TEXT NOT NULL DEFAULT '',"
    " currency TEXT NOT NULL,"
    " total_minor INTEGER NOT NULL,"
    " status TEXT NOT NULL DEFAULT 'new',"
    " checkout_token_hash TEXT NOT NULL UNIQUE,"
    " access_token_hash TEXT NOT NULL,"
    " created_at TEXT NOT NULL,"
    " updated_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS order_items ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,"
    " product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,"
    " product_slug TEXT NOT NULL DEFAULT '',"
    " product_name TEXT NOT NULL,"
    " price_minor INTEGER NOT NULL,"
    " currency TEXT NOT NULL,"
    " quantity INTEGER NOT NULL,"
    " line_total_minor INTEGER NOT NULL)",
    "CREATE INDEX IF NOT EXISTS ix_cart_items_cart ON cart_items (cart_id)",
    "CREATE INDEX IF NOT EXISTS ix_orders_status_created ON orders (status, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_order_items_order ON order_items (order_id)",
)


def _apply_cart_orders(tx: Any) -> None:
    for statement in CART_ORDER_DDL:
        tx.execute(statement)


#: S3 steps plus the catalog, page, category-image, requests and attributes steps
CATALOG_MIGRATIONS: Tuple[Migration, ...] = tuple(S3_MIGRATIONS) + (
    Migration(version=3, name="catalog_schema", apply=_apply_catalog),
    Migration(version=4, name="pages_schema", apply=_apply_pages),
    Migration(version=5, name="category_image", apply=_apply_catalog_image),
    Migration(version=6, name="requests_table", apply=_apply_requests),
    Migration(version=7, name="attributes_lang", apply=_apply_attributes_lang),
    Migration(version=8, name="carts_orders_tables", apply=_apply_cart_orders),
) + PUBLICATIONS_MIGRATIONS


def migrate_catalog(provider: Any) -> int:
    """Apply the S3 steps and the catalog step; returns the schema version."""
    return migrate(provider, CATALOG_MIGRATIONS)
