"""Server-side cart (block 3c-1).

The cookie holds only an opaque, HMAC-signed identifier (cart id + issue time);
contents, quantities and prices are read from the database on every request.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from ..domain.catalog import Money, NotFoundError
from ..infrastructure.retry import run_transaction_with_retry

CART_COOKIE = "videoshop_cart"
CART_TTL_SECONDS = 30 * 24 * 60 * 60
MAX_QUANTITY = 99
MAX_ITEMS = 50
CLEANUP_LIMIT = 100

LOGGER = logging.getLogger("videoshop.cart")


class CartError(RuntimeError):
    """Base error for cart problems."""


class CartBadSignature(CartError):
    """The cookie signature does not match (tampering)."""


class CartLimitError(CartError):
    """A cart limit was exceeded (quantity or positions)."""


class CartItemNotFound(CartError):
    """The requested cart line does not exist."""


@dataclass(frozen=True)
class Cart:
    id: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class CartLine:
    item_id: int
    product_id: Optional[int]
    slug: str
    name: str
    price: Optional[Money]
    quantity: int
    line_total: Optional[Money]
    available: bool


@dataclass(frozen=True)
class CartView:
    cart: Cart
    lines: Tuple[CartLine, ...]
    total: Money
    currency: str
    count: int


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())


class CartService:
    def __init__(self, provider: Any, catalog: Any, *, secret: bytes) -> None:
        self._provider = provider
        self._catalog = catalog
        self._secret = secret

    # -- token -----------------------------------------------------------
    def issue_token(self, cart_id: int, issued_at: Optional[int] = None) -> str:
        issued = int(issued_at if issued_at is not None else time.time())
        payload = f"{int(cart_id)}:{issued}".encode("ascii")
        body = base64.urlsafe_b64encode(payload).decode("ascii")
        mac = hmac.new(self._secret, body.encode("ascii"), hashlib.sha256).hexdigest()
        return f"{body}.{mac}"

    def parse_token(self, token: str) -> Tuple[int, int]:
        try:
            body, mac = (token or "").split(".", 1)
            expected = hmac.new(self._secret, body.encode("ascii"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(mac, expected):
                raise CartBadSignature("cart cookie signature mismatch")
            cart_id_text, issued_text = base64.urlsafe_b64decode(body.encode("ascii")).decode("ascii").split(":", 1)
            return int(cart_id_text), int(issued_text)
        except CartBadSignature:
            raise
        except Exception as exc:  # malformed payload
            raise CartBadSignature("malformed cart cookie") from exc

    @staticmethod
    def is_expired(issued_at: int, now: Optional[float] = None) -> bool:
        moment = time.time() if now is None else now
        return (moment - int(issued_at)) > CART_TTL_SECONDS

    # -- storage ---------------------------------------------------------
    def _cleanup(self, tx: Any) -> None:
        threshold = time.strftime(
            "%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(time.time() - CART_TTL_SECONDS)
        )
        tx.execute(
            "DELETE FROM carts WHERE id IN ("
            "SELECT id FROM carts WHERE updated_at < ? LIMIT ?)",
            (threshold, CLEANUP_LIMIT),
        )

    def new_cart(self) -> Cart:
        now = _now()

        def operation(tx):
            self._cleanup(tx)
            cursor = tx.execute(
                "INSERT INTO carts (token, created_at, updated_at) VALUES (?, ?, ?)",
                (secrets.token_hex(16), now, now),
            )
            return int(cursor.lastrowid)

        cart_id = run_transaction_with_retry(self._provider, operation)
        return self.load(cart_id)

    def load(self, cart_id: int) -> Optional[Cart]:
        with self._provider.read_transaction() as tx:
            row = tx.fetchone("SELECT * FROM carts WHERE id = ?", (int(cart_id),))
        if row is None:
            return None
        return Cart(id=int(row["id"]), created_at=row["created_at"], updated_at=row["updated_at"])

    def peek(self, token: Optional[str]) -> Optional[Cart]:
        """Return the cart for a cookie without creating anything (for counters)."""
        if not token:
            return None
        cart_id, issued = self.parse_token(token)
        if self.is_expired(issued):
            return None
        return self.load(cart_id)

    def resolve(self, token: Optional[str]) -> Tuple[Cart, bool, bool]:
        """Return ``(cart, expired, fresh)``; a bad signature raises CartBadSignature.

        ``fresh`` is True only when a new cart was created (no cookie, expired
        cookie or a missing row): only then is a new cookie issued, so a valid
        token is never auto-renewed (block 3c decision 3).
        """
        if not token:
            return self.new_cart(), False, True
        cart_id, issued = self.parse_token(token)
        if self.is_expired(issued):
            return self.new_cart(), True, True
        cart = self.load(cart_id)
        if cart is None:
            return self.new_cart(), False, True
        return cart, False, False

    # -- contents --------------------------------------------------------
    def _rows(self, cart_id: int) -> List[Any]:
        with self._provider.read_transaction() as tx:
            return tx.fetchall(
                "SELECT * FROM cart_items WHERE cart_id = ? ORDER BY id", (int(cart_id),)
            )

    def count(self, cart: Cart) -> int:
        return len(self._rows(cart.id))

    def read(self, cart: Cart, lang: str) -> CartView:
        currency = self._catalog.get_settings().default_currency
        total_minor = 0
        lines: List[CartLine] = []
        for row in self._rows(cart.id):
            quantity = int(row["quantity"])
            product_id = row["product_id"]
            name = ""
            slug = ""
            price = None
            available = False
            if product_id is not None:
                try:
                    product = self._catalog.get_product(int(product_id))
                except NotFoundError:
                    product = None
                if product is not None:
                    name = product.text(lang).name
                    slug = product.slug
                    available = product.is_published
                    if available:
                        price = product.price
                        if price.currency == currency:
                            total_minor += price.minor * quantity
            if not name:
                name = f"#{product_id}" if product_id is not None else "-"
            line_total = (
                Money(minor=price.minor * quantity, currency=price.currency) if price else None
            )
            lines.append(
                CartLine(
                    item_id=int(row["id"]),
                    product_id=int(product_id) if product_id is not None else None,
                    slug=slug,
                    name=name,
                    price=price,
                    quantity=quantity,
                    line_total=line_total,
                    available=available,
                )
            )
        return CartView(
            cart=cart,
            lines=tuple(lines),
            total=Money(minor=total_minor, currency=currency),
            currency=currency,
            count=len(lines),
        )

    # -- mutations -------------------------------------------------------
    def _touch(self, tx: Any, cart_id: int) -> None:
        tx.execute("UPDATE carts SET updated_at = ? WHERE id = ?", (_now(), int(cart_id)))

    def add(self, cart: Cart, product_id: int, quantity: int) -> Cart:
        amount = int(quantity)
        if amount < 1 or amount > MAX_QUANTITY:
            raise CartLimitError("quantity must be between 1 and 99")
        product = self._catalog.get_product(int(product_id))
        if not product.is_published:
            raise NotFoundError(f"product {product_id} is not available")

        def operation(tx):
            self._cleanup(tx)
            existing = tx.fetchone(
                "SELECT * FROM cart_items WHERE cart_id = ? AND product_id = ?",
                (cart.id, int(product_id)),
            )
            if existing is not None:
                merged = min(MAX_QUANTITY, int(existing["quantity"]) + amount)
                tx.execute(
                    "UPDATE cart_items SET quantity = ? WHERE id = ?",
                    (merged, int(existing["id"])),
                )
            else:
                positions = int(
                    tx.scalar("SELECT COUNT(*) FROM cart_items WHERE cart_id = ?", (cart.id,))
                )
                if positions >= MAX_ITEMS:
                    raise CartLimitError("a cart can hold at most 50 positions")
                tx.execute(
                    "INSERT INTO cart_items (cart_id, product_id, quantity, added_at) "
                    "VALUES (?, ?, ?, ?)",
                    (cart.id, int(product_id), amount, _now()),
                )
            self._touch(tx, cart.id)

        run_transaction_with_retry(self._provider, operation)
        return self.load(cart.id)

    def update(self, cart: Cart, item_id: int, quantity: int) -> Cart:
        amount = int(quantity)
        if amount < 1 or amount > MAX_QUANTITY:
            raise CartLimitError("quantity must be between 1 and 99")

        def operation(tx):
            row = tx.fetchone(
                "SELECT * FROM cart_items WHERE id = ? AND cart_id = ?", (int(item_id), cart.id)
            )
            if row is None:
                raise CartItemNotFound(f"cart item {item_id} does not exist")
            tx.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (amount, int(item_id)))
            self._touch(tx, cart.id)

        run_transaction_with_retry(self._provider, operation)
        return self.load(cart.id)

    def remove(self, cart: Cart, item_id: int) -> Cart:
        def operation(tx):
            row = tx.fetchone(
                "SELECT * FROM cart_items WHERE id = ? AND cart_id = ?", (int(item_id), cart.id)
            )
            if row is None:
                raise CartItemNotFound(f"cart item {item_id} does not exist")
            tx.execute("DELETE FROM cart_items WHERE id = ?", (int(item_id),))
            self._touch(tx, cart.id)

        run_transaction_with_retry(self._provider, operation)
        return self.load(cart.id)

    def clear(self, cart: Cart) -> Cart:
        def operation(tx):
            tx.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart.id,))
            self._touch(tx, cart.id)

        run_transaction_with_retry(self._provider, operation)
        return self.load(cart.id)
