"""
Cafe Menu Service v0.1 — showcase-local Dict persistence, no generic abstraction
Follows docs_site pattern: global slug index, list_published, get_published_by_slug

Stock/Order semantics: cafe-local, NOT generic StockManager
Lifecycle: DRAFT → VALIDATED → CONFIRMED (decrement) → CANCELLED (restore)
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import datetime, UTC

from showcases.cafe.domain.models_v01 import (
    MenuCategory,
    MenuItem,
    MenuItemStatus,
    Order,
    OrderLine,
    OrderStatus,
    SeoMeta,
    validate_slug,
)


class NotFoundError(Exception):
    pass


class DuplicateSlugError(Exception):
    pass


class ValidationError(Exception):
    pass


class OutOfStockError(Exception):
    pass


class InsufficientStockError(Exception):
    pass


class CafeMenuService:
    def __init__(self) -> None:
        self._categories: Dict[uuid.UUID, MenuCategory] = {}
        self._items: Dict[uuid.UUID, MenuItem] = {}
        self._slug_index: Dict[str, uuid.UUID] = {}  # global unique slug for items
        self._cat_slug_index: Dict[str, uuid.UUID] = {}
        self._orders: Dict[uuid.UUID, Order] = {}

    # ---- Category ----

    def create_category(self, name: str, slug: str) -> MenuCategory:
        validate_slug(slug)
        if slug in self._cat_slug_index:
            raise DuplicateSlugError(f"Category slug duplicate: {slug}")
        cat_id = uuid.uuid4()
        cat = MenuCategory(id=cat_id, name=name, slug=slug, is_published=True)
        self._categories[cat_id] = cat
        self._cat_slug_index[slug] = cat_id
        return cat

    def list_categories(self) -> List[MenuCategory]:
        return list(self._categories.values())

    def get_category(self, cat_id: uuid.UUID) -> MenuCategory:
        if cat_id not in self._categories:
            raise NotFoundError(f"Category {cat_id} not found")
        return self._categories[cat_id]

    # ---- MenuItem ----

    def create_item(
        self,
        title: str,
        slug: str,
        description: str,
        price: Decimal,
        category_id: uuid.UUID,
        stock_quantity: Optional[int] = None,
        dietary_tags: Optional[List[str]] = None,
    ) -> MenuItem:
        validate_slug(slug)
        if slug in self._slug_index:
            raise DuplicateSlugError(f"Item slug duplicate: {slug}")
        if category_id not in self._categories:
            raise NotFoundError(f"Category {category_id} not found")
        if price <= Decimal("0"):
            raise ValidationError("price must be >0")
        if stock_quantity is not None and stock_quantity < 0:
            raise ValidationError("stock_quantity must be >=0")

        item_id = uuid.uuid4()
        item = MenuItem(
            id=item_id,
            title=title,
            slug=slug,
            description=description,
            price=price,
            category_id=category_id,
            stock_quantity=stock_quantity,
            is_published=False,
            seo=None,
            dietary_tags=dietary_tags or [],
            status=MenuItemStatus.DRAFT,
        )
        self._items[item_id] = item
        self._slug_index[slug] = item_id
        return item

    def get_item(self, item_id: uuid.UUID) -> MenuItem:
        if item_id not in self._items:
            raise NotFoundError(f"Item {item_id} not found")
        return self._items[item_id]

    def list_items(self) -> List[MenuItem]:
        return list(self._items.values())

    def list_published(self, category_slug: Optional[str] = None) -> List[MenuItem]:
        items = [
            i
            for i in self._items.values()
            if i.is_published and i.status == MenuItemStatus.PUBLISHED
        ]
        if category_slug:
            cat_id = self._cat_slug_index.get(category_slug)
            if not cat_id:
                return []
            items = [i for i in items if i.category_id == cat_id]
        return items

    def get_published_by_slug(self, slug: str) -> MenuItem:
        item_id = self._slug_index.get(slug)
        if not item_id:
            raise NotFoundError(f"Slug {slug} not found")
        item = self._items[item_id]
        if not item.is_published or item.status != MenuItemStatus.PUBLISHED:
            raise NotFoundError(f"Item {slug} not published")
        return item

    def update_item(
        self,
        item_id: uuid.UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[Decimal] = None,
        stock_quantity: Optional[int] = None,
        category_id: Optional[uuid.UUID] = None,
    ) -> MenuItem:
        item = self.get_item(item_id)
        if title is not None:
            if len(title.strip()) < 2:
                raise ValidationError("title >=2")
            item.title = title
        if description is not None:
            item.description = description
        if price is not None:
            if price <= Decimal("0"):
                raise ValidationError("price >0")
            item.price = price
        if stock_quantity is not None:
            if stock_quantity < 0:
                raise ValidationError("stock >=0")
            item.stock_quantity = stock_quantity
        if category_id is not None:
            if category_id not in self._categories:
                raise NotFoundError(f"Category {category_id} not found")
            item.category_id = category_id
        return item

    def update_seo(
        self,
        item_id: uuid.UUID,
        seo_title: Optional[str],
        seo_description: Optional[str],
        canonical_url: Optional[str],
    ) -> MenuItem:
        item = self.get_item(item_id)
        item.seo = SeoMeta(
            seo_title=seo_title,
            seo_description=seo_description,
            canonical_url=canonical_url,
        )
        return item

    def publish(self, item_id: uuid.UUID) -> MenuItem:
        item = self.get_item(item_id)
        if len(item.description.strip()) < 10:
            raise ValidationError("Cannot publish: description <10")
        if item.price <= Decimal("0"):
            raise ValidationError("Cannot publish: price <=0")
        item.is_published = True
        item.status = MenuItemStatus.PUBLISHED
        return item

    def unpublish(self, item_id: uuid.UUID) -> MenuItem:
        item = self.get_item(item_id)
        item.is_published = False
        item.status = MenuItemStatus.DRAFT
        return item

    def set_availability(
        self, item_id: uuid.UUID, stock_quantity: Optional[int]
    ) -> MenuItem:
        item = self.get_item(item_id)
        if stock_quantity is not None and stock_quantity < 0:
            raise ValidationError("stock >=0")
        item.stock_quantity = stock_quantity
        return item

    # ---- Order ----

    def create_order(self, lines: List[dict]) -> Order:
        """
        lines: [{"menu_item_id": UUID|str, "quantity": int}]
        Server calculates price_snapshot and total, validates stock
        """
        if not lines:
            raise ValidationError("Order must have at least 1 line")

        order_lines: List[OrderLine] = []
        total = Decimal("0")

        for raw in lines:
            mid = raw["menu_item_id"]
            if isinstance(mid, str):
                mid = uuid.UUID(mid)
            qty = int(raw["quantity"])
            if qty <= 0:
                raise ValidationError("quantity must be >0")
            item = self.get_item(mid)
            if not item.is_published:
                raise ValidationError(f"Item {item.slug} not published")
            # stock check at creation (quote)
            if item.stock_quantity is not None:
                if item.stock_quantity == 0:
                    raise OutOfStockError(f"Item {item.slug} OUT_OF_STOCK")
                if qty > item.stock_quantity:
                    raise InsufficientStockError(
                        f"Item {item.slug} INSUFFICIENT_STOCK: requested {qty} > stock {item.stock_quantity}"
                    )

            line = OrderLine(menu_item_id=mid, quantity=qty, price_snapshot=item.price)
            order_lines.append(line)
            total += item.price * qty

        order_id = uuid.uuid4()
        order = Order(
            id=order_id,
            lines=order_lines,
            total=total,
            status=OrderStatus.DRAFT,
            created_at=datetime.now(UTC).isoformat(),
        )
        self._orders[order_id] = order
        return order

    def get_order(self, order_id: uuid.UUID) -> Order:
        if order_id not in self._orders:
            raise NotFoundError(f"Order {order_id} not found")
        return self._orders[order_id]

    def list_orders(self) -> List[Order]:
        return list(self._orders.values())

    def validate_order(self, order_id: uuid.UUID) -> Order:
        order = self.get_order(order_id)
        if order.status != OrderStatus.DRAFT:
            raise ValidationError(
                f"Only DRAFT can be validated, current {order.status}"
            )
        # re-check stock
        for line in order.lines:
            item = self.get_item(line.menu_item_id)
            if item.stock_quantity is not None:
                if item.stock_quantity == 0:
                    raise OutOfStockError(f"Item {item.slug} OUT_OF_STOCK")
                if line.quantity > item.stock_quantity:
                    raise InsufficientStockError(f"Item {item.slug} INSUFFICIENT_STOCK")
        order.status = OrderStatus.VALIDATED
        return order

    def confirm_order(self, order_id: uuid.UUID) -> Order:
        order = self.get_order(order_id)
        if order.status not in (OrderStatus.DRAFT, OrderStatus.VALIDATED):
            raise ValidationError(
                f"Only DRAFT/VALIDATED can be confirmed, current {order.status}"
            )
        # final stock check and decrement
        for line in order.lines:
            item = self.get_item(line.menu_item_id)
            if item.stock_quantity is not None:
                if item.stock_quantity == 0:
                    raise OutOfStockError(f"Item {item.slug} OUT_OF_STOCK")
                if line.quantity > item.stock_quantity:
                    raise InsufficientStockError(f"Item {item.slug} INSUFFICIENT_STOCK")
        # decrement
        for line in order.lines:
            item = self.get_item(line.menu_item_id)
            if item.stock_quantity is not None:
                item.stock_quantity -= line.quantity

        order.status = OrderStatus.CONFIRMED
        return order

    def cancel_order(self, order_id: uuid.UUID) -> Order:
        order = self.get_order(order_id)
        if order.status == OrderStatus.CANCELLED:
            return order
        if order.status == OrderStatus.CONFIRMED:
            # restore stock
            for line in order.lines:
                item = self.get_item(line.menu_item_id)
                if item.stock_quantity is not None:
                    item.stock_quantity += line.quantity
        order.status = OrderStatus.CANCELLED
        return order
