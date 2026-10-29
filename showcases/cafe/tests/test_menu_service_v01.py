"""
Menu service contract tests — derived from showcases/cafe/services/cafe_menu_service.py
No production code change, only existing behaviors.
"""

import uuid
from decimal import Decimal
import pytest

from showcases.cafe.services.cafe_menu_service import (
    CafeMenuService,
    DuplicateSlugError,
    NotFoundError,
    ValidationError,
    OutOfStockError,
    InsufficientStockError,
)


class TestCategoryOperations:
    def test_create_category_success(self):
        svc = CafeMenuService()
        cat = svc.create_category(name="Coffee", slug="coffee")
        assert cat.slug == "coffee"
        assert cat.is_published is True
        assert len(svc.list_categories()) == 1

    def test_create_category_duplicate_slug(self):
        svc = CafeMenuService()
        svc.create_category(name="Coffee", slug="coffee")
        with pytest.raises(DuplicateSlugError):
            svc.create_category(name="Coffee2", slug="coffee")

    def test_get_category_not_found(self):
        svc = CafeMenuService()
        with pytest.raises(NotFoundError):
            svc.get_category(uuid.uuid4())


class TestMenuItemOperations:
    def setup_method(self):
        self.svc = CafeMenuService()
        self.cat = self.svc.create_category(name="Coffee", slug="coffee")

    def test_create_item_success(self):
        item = self.svc.create_item(
            title="Latte",
            slug="latte",
            description="Tasty coffee with milk foam long",
            price=Decimal("4.5"),
            category_id=self.cat.id,
        )
        assert item.slug == "latte"
        assert item.is_published is False
        assert len(self.svc.list_items()) == 1

    def test_create_item_duplicate_slug(self):
        self.svc.create_item(
            title="Latte",
            slug="latte",
            description="Long enough description for item",
            price=Decimal("1"),
            category_id=self.cat.id,
        )
        with pytest.raises(DuplicateSlugError):
            self.svc.create_item(
                title="Latte2",
                slug="latte",
                description="Long enough description",
                price=Decimal("1"),
                category_id=self.cat.id,
            )

    def test_create_item_missing_category(self):
        with pytest.raises(NotFoundError):
            self.svc.create_item(
                title="Latte",
                slug="latte",
                description="Long enough description",
                price=Decimal("1"),
                category_id=uuid.uuid4(),
            )

    def test_create_item_invalid_price(self):
        with pytest.raises(ValidationError):
            self.svc.create_item(
                title="Latte",
                slug="latte",
                description="Long enough description",
                price=Decimal("0"),
                category_id=self.cat.id,
            )

    def test_create_item_invalid_stock(self):
        with pytest.raises(ValidationError, match="stock_quantity"):
            self.svc.create_item(
                title="Latte",
                slug="latte",
                description="Long enough description",
                price=Decimal("1"),
                category_id=self.cat.id,
                stock_quantity=-5,
            )

    def test_publish_gate_description_too_short(self):
        item = self.svc.create_item(
            title="Latte",
            slug="latte",
            description="short",
            price=Decimal("1"),
            category_id=self.cat.id,
        )
        # description <10 should fail on publish
        with pytest.raises(ValidationError, match="description <10"):
            self.svc.publish(item.id)

    def test_publish_success(self):
        item = self.svc.create_item(
            title="Latte",
            slug="latte",
            description="Long enough for publish gate",
            price=Decimal("2"),
            category_id=self.cat.id,
        )
        published = self.svc.publish(item.id)
        assert published.is_published is True
        assert len(self.svc.list_published()) == 1

    def test_list_published_filtered_by_category(self):
        cat2 = self.svc.create_category(name="Tea", slug="tea")
        item1 = self.svc.create_item(
            title="Latte",
            slug="latte",
            description="Long enough description",
            price=Decimal("1"),
            category_id=self.cat.id,
        )
        item2 = self.svc.create_item(
            title="Green Tea",
            slug="green-tea",
            description="Long enough description",
            price=Decimal("1"),
            category_id=cat2.id,
        )
        self.svc.publish(item1.id)
        self.svc.publish(item2.id)
        assert len(self.svc.list_published(category_slug="coffee")) == 1
        assert len(self.svc.list_published(category_slug="tea")) == 1
        assert len(self.svc.list_published(category_slug="nonexistent")) == 0

    def test_get_published_by_slug_not_published(self):
        item = self.svc.create_item(
            title="Latte",
            slug="latte",
            description="Long enough description",
            price=Decimal("1"),
            category_id=self.cat.id,
        )
        with pytest.raises(NotFoundError):
            self.svc.get_published_by_slug("latte")


class TestStockAndOrder:
    def setup_method(self):
        self.svc = CafeMenuService()
        self.cat = self.svc.create_category(name="Coffee", slug="coffee")
        self.item = self.svc.create_item(
            title="Latte",
            slug="latte",
            description="Long enough description for order",
            price=Decimal("5"),
            category_id=self.cat.id,
            stock_quantity=5,
        )
        self.svc.publish(self.item.id)

    def test_create_order_success(self):
        order = self.svc.create_order([{"menu_item_id": self.item.id, "quantity": 2}])
        assert order.total == Decimal("10")
        assert len(order.lines) == 1

    def test_create_order_out_of_stock(self):
        self.svc.set_availability(self.item.id, 0)
        with pytest.raises(OutOfStockError):
            self.svc.create_order([{"menu_item_id": self.item.id, "quantity": 1}])

    def test_create_order_insufficient_stock(self):
        with pytest.raises(InsufficientStockError):
            self.svc.create_order([{"menu_item_id": self.item.id, "quantity": 10}])

    def test_confirm_order_decrements_stock(self):
        order = self.svc.create_order([{"menu_item_id": self.item.id, "quantity": 2}])
        self.svc.confirm_order(order.id)
        assert self.svc.get_item(self.item.id).stock_quantity == 3

    def test_cancel_confirmed_restores_stock(self):
        order = self.svc.create_order([{"menu_item_id": self.item.id, "quantity": 2}])
        self.svc.confirm_order(order.id)
        self.svc.cancel_order(order.id)
        assert self.svc.get_item(self.item.id).stock_quantity == 5

    def test_update_item_invalid_stock(self):
        with pytest.raises(ValidationError, match="stock >=0"):
            self.svc.update_item(self.item.id, stock_quantity=-1)
