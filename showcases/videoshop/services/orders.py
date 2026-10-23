"""Order creation for the checkout (block 3c-2a).

Server-side only: the cart is read from the database, prices are recomputed from
the catalogue, and the order plus its items are written in one transaction.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from ..domain.catalog import Money, NotFoundError
from ..infrastructure.retry import run_transaction_with_retry

LOGGER = logging.getLogger("videoshop.order")

ORDER_STATUS_NEW = "new"
ORDER_STATUSES = ("new", "confirmed", "done", "cancelled")
#: server-side transition table (block 3c-3)
ALLOWED_TRANSITIONS = {
    "new": frozenset({"confirmed", "cancelled"}),
    "confirmed": frozenset({"done", "cancelled"}),
    "done": frozenset(),
    "cancelled": frozenset(),
}
MAX_NAME = 120
MAX_CONTACT = 200
MAX_ADDRESS = 300
MAX_COMMENT = 1000
NUMBER_RETRIES = 5


class OrderError(RuntimeError):
    """Base error for order creation."""


class OrderValidationError(OrderError):
    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code


class OrderUnavailableError(OrderError):
    def __init__(self, names):
        super().__init__("some cart positions are unavailable")
        self.names = tuple(names)


class OrderPriceChangedError(OrderError):
    """The total changed between rendering the checkout and submitting it."""


@dataclass(frozen=True)
class OrderResult:
    order_id: int
    number: str
    total: Money
    created: bool
    #: only present on the very first creation; never stored in the database
    access_token: Optional[str] = None


@dataclass(frozen=True)
class OrderItem:
    product_name: str
    product_slug: str
    price_minor: int
    currency: str
    quantity: int
    line_total_minor: int


@dataclass(frozen=True)
class OrderDetails:
    number: str
    status: str
    currency: str
    total_minor: int
    created_at: str
    items: Tuple[OrderItem, ...]
    #: admin-only fields (the public page never renders them)
    name: str = ""
    contact: str = ""
    address: str = ""
    comment: str = ""
    source_lang: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class OrderSummary:
    number: str
    name: str
    total_minor: int
    currency: str
    status: str
    created_at: str


class InvalidStatusTransition(OrderError):
    def __init__(self, current: str, target: str):
        super().__init__(f"transition {current} -> {target} is not allowed")
        self.current = current
        self.target = target


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())


@dataclass(frozen=True)
class _Line:
    product_id: int
    slug: str
    name: str
    price: Money
    quantity: int

    @property
    def line_total(self) -> Money:
        return Money(minor=self.price.minor * self.quantity, currency=self.price.currency)


class OrderService:
    def __init__(self, provider: Any, catalog: Any, cart: Any) -> None:
        self._provider = provider
        self._catalog = catalog
        self._cart = cart
        self._secret = b""

    def token_hash(self, token: str) -> str:
        return hashlib.sha256((token or "").encode("utf-8")).hexdigest()

    # -- validation ------------------------------------------------------
    @staticmethod
    def _text(value: str, code: str, maximum: int, required: bool) -> str:
        text = (value or "").strip()
        if required and not text:
            raise OrderValidationError(code)
        if len(text) > maximum:
            raise OrderValidationError(code + "_long")
        return text

    def _lines(self, cart_id: int, lang: str) -> List[_Line]:
        lines: List[_Line] = []
        unavailable: List[str] = []
        for row in self._cart._rows(cart_id):
            product_id = row["product_id"]
            product = None
            if product_id is not None:
                try:
                    product = self._catalog.get_product(int(product_id))
                except NotFoundError:
                    product = None
            if product is None or not product.is_published:
                unavailable.append(product.text(lang).name if product is not None else f"#{product_id}")
                continue
            lines.append(
                _Line(
                    product_id=product.id,
                    slug=product.slug,
                    name=product.text(lang).name,
                    price=product.price,
                    quantity=int(row["quantity"]),
                )
            )
        if unavailable:
            raise OrderUnavailableError(unavailable)
        return lines

    # -- creation --------------------------------------------------------
    def create_order(
        self,
        cart_id: int,
        *,
        name: str,
        contact: str,
        address: str = "",
        comment: str = "",
        source_lang: str = "",
        checkout_token: str = "",
        lang: str = "ru",
        expected_total_minor: Optional[int] = None,
    ) -> OrderResult:
        # idempotency first: a repeated submit returns the order created earlier
        if checkout_token:
            existing = self._find_by_token(self.token_hash(checkout_token))
            if existing is not None:
                return existing

        name_text = self._text(name, "order_err_name_required", MAX_NAME, True)
        contact_text = self._text(contact, "order_err_contact_required", MAX_CONTACT, True)
        address_text = self._text(address, "order_err_address_long", MAX_ADDRESS, False)
        comment_text = self._text(comment, "order_err_comment_long", MAX_COMMENT, False)

        currency = self._catalog.get_settings().default_currency
        lines = self._lines(cart_id, lang)
        if not lines:
            raise OrderValidationError("order_error_empty_cart")
        total_minor = sum(line.line_total.minor for line in lines if line.price.currency == currency)
        if expected_total_minor is not None and int(expected_total_minor) != total_minor:
            raise OrderPriceChangedError("prices changed since the checkout was rendered")
        if not checkout_token:
            raise OrderValidationError("order_error_checkout_token")

        token_hash = self.token_hash(checkout_token)
        access_token = secrets.token_urlsafe(32)
        access_hash = self.access_hash(access_token)
        total = Money(minor=total_minor, currency=currency)

        for _attempt in range(NUMBER_RETRIES):
            try:
                result = run_transaction_with_retry(
                    self._provider,
                    lambda tx: self._write(tx, cart_id, name_text, contact_text, address_text,
                                           comment_text, source_lang, token_hash, access_hash,
                                           currency, total_minor, lines, access_token),
                )
                LOGGER.info("order created: %s", result["number"])
                return OrderResult(
                    order_id=result["id"],
                    number=result["number"],
                    total=total,
                    created=result["created"],
                    access_token=result.get("token"),
                )
            except OrderError:
                raise
            except Exception as exc:  # UNIQUE conflict on the number or the token
                message = str(exc).upper()
                if "UNIQUE" not in message and "CONSTRAINT" not in message:
                    LOGGER.error("order creation failed: %s", exc)
                    raise
                existing = self._find_by_token(token_hash)
                if existing is not None:
                    return existing
                continue
        raise OrderError("could not allocate a unique order number")

    def _find_by_token(self, token_hash: str) -> Optional[OrderResult]:
        with self._provider.read_transaction() as tx:
            row = tx.fetchone(
                "SELECT id, number, total_minor, currency FROM orders WHERE checkout_token_hash = ?",
                (token_hash,),
            )
        if row is None:
            return None
        return OrderResult(
            order_id=int(row["id"]),
            number=row["number"],
            total=Money(minor=int(row["total_minor"]), currency=row["currency"]),
            created=False,
        )

    @staticmethod
    def access_hash(token: str) -> str:
        """Hash of the buyer access token (the raw token is never stored)."""
        return hashlib.sha256((token or "").encode("utf-8")).hexdigest()

    def find_order(self, number: str, token: str) -> Optional[OrderDetails]:
        """Return the order only when the access token matches (constant time)."""
        number = (number or "").strip()
        token = token or ""
        if not number or not token:
            return None
        with self._provider.read_transaction() as tx:
            row = tx.fetchone("SELECT * FROM orders WHERE number = ?", (number,))
            if row is None:
                return None
            if not hmac.compare_digest(row["access_token_hash"], self.access_hash(token)):
                return None
            items = [
                OrderItem(
                    product_name=item["product_name"],
                    product_slug=item["product_slug"],
                    price_minor=int(item["price_minor"]),
                    currency=item["currency"],
                    quantity=int(item["quantity"]),
                    line_total_minor=int(item["line_total_minor"]),
                )
                for item in tx.fetchall(
                    "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (int(row["id"]),)
                )
            ]
        return OrderDetails(
            number=row["number"],
            status=row["status"],
            currency=row["currency"],
            total_minor=int(row["total_minor"]),
            created_at=row["created_at"],
            items=tuple(items),
        )


    # -- admin (block 3c-3) ----------------------------------------------
    def list_orders(self, status: Optional[str] = None, limit: int = 200) -> List[OrderSummary]:
        query = "SELECT * FROM orders"
        params: List[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(int(limit))
        with self._provider.read_transaction() as tx:
            rows = tx.fetchall(query, tuple(params))
        return [
            OrderSummary(
                number=row["number"], name=row["name"], total_minor=int(row["total_minor"]),
                currency=row["currency"], status=row["status"], created_at=row["created_at"],
            )
            for row in rows
        ]

    def count_by_status(self, status: str) -> int:
        with self._provider.read_transaction() as tx:
            return int(tx.scalar("SELECT COUNT(*) FROM orders WHERE status = ?", (status,)))

    def admin_get(self, number: str) -> Optional[OrderDetails]:
        number = (number or "").strip()
        if not number:
            return None
        with self._provider.read_transaction() as tx:
            row = tx.fetchone("SELECT * FROM orders WHERE number = ?", (number,))
            if row is None:
                return None
            items = tuple(
                OrderItem(
                    product_name=item["product_name"], product_slug=item["product_slug"],
                    price_minor=int(item["price_minor"]), currency=item["currency"],
                    quantity=int(item["quantity"]), line_total_minor=int(item["line_total_minor"]),
                )
                for item in tx.fetchall(
                    "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (int(row["id"]),)
                )
            )
        return OrderDetails(
            number=row["number"], status=row["status"], currency=row["currency"],
            total_minor=int(row["total_minor"]), created_at=row["created_at"], items=items,
            name=row["name"], contact=row["contact"], address=row["address"],
            comment=row["comment"], source_lang=row["source_lang"], updated_at=row["updated_at"],
        )

    def allowed_targets(self, status: str) -> Tuple[str, ...]:
        return tuple(sorted(ALLOWED_TRANSITIONS.get(status, frozenset())))

    def set_status(self, number: str, target: str) -> Tuple[OrderDetails, str]:
        current = self.admin_get(number)
        if current is None:
            raise NotFoundError(f"order {number} does not exist")
        candidate = (target or "").strip().lower()
        if candidate not in ALLOWED_TRANSITIONS.get(current.status, frozenset()):
            LOGGER.warning("rejected status transition %s -> %s for %s", current.status, candidate, number)
            raise InvalidStatusTransition(current.status, candidate)

        def operation(tx):
            tx.execute(
                "UPDATE orders SET status = ?, updated_at = ? WHERE number = ?",
                (candidate, _now(), number),
            )

        run_transaction_with_retry(self._provider, operation)
        LOGGER.info("order %s status %s -> %s", number, current.status, candidate)
        updated = self.admin_get(number)
        return updated, current.status

    def _write(self, tx, cart_id, name_text, contact_text, address_text, comment_text,
               source_lang, token_hash, access_hash, currency, total_minor, lines,
               access_token=None):
        existing = tx.fetchone(
            "SELECT id, number, total_minor, currency FROM orders WHERE checkout_token_hash = ?",
            (token_hash,),
        )
        if existing is not None:
            return {
                "id": int(existing["id"]),
                "number": existing["number"],
                "created": False,
            }
        year = time.strftime("%Y", time.gmtime())
        seq = int(tx.scalar(
            "SELECT COUNT(*) FROM orders WHERE number LIKE ?", (f"VS-{year}-%",)
        )) + 1
        number = f"VS-{year}-{seq:06d}"
        now = _now()
        cursor = tx.execute(
            "INSERT INTO orders (number, name, contact, address, comment, source_lang, currency, "
            "total_minor, status, checkout_token_hash, access_token_hash, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (number, name_text, contact_text, address_text, comment_text,
             (source_lang or "")[:5], currency, total_minor, ORDER_STATUS_NEW,
             token_hash, access_hash, now, now),
        )
        order_id = int(cursor.lastrowid)
        for line in lines:
            tx.execute(
                "INSERT INTO order_items (order_id, product_id, product_slug, product_name, "
                "price_minor, currency, quantity, line_total_minor) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (order_id, line.product_id, line.slug, line.name, line.price.minor,
                 line.price.currency, line.quantity, line.line_total.minor),
            )
        tx.execute("DELETE FROM cart_items WHERE cart_id = ?", (int(cart_id),))
        tx.execute("UPDATE carts SET updated_at = ? WHERE id = ?", (now, int(cart_id)))
        return {"id": order_id, "number": number, "created": True, "token": access_token}
