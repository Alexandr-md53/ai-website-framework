"""
Models v0.1 contract tests — derived from showcases/cafe/domain/models_v01.py
No invented requirements, only existing validations.
"""

import uuid
from decimal import Decimal
import pytest

from showcases.cafe.domain.models_v01 import (
    MenuCategory,
    MenuItem,
    MenuItemStatus,
    Order,
    OrderLine,
    OrderStatus,
    validate_slug,
)


class TestValidateSlug:
    def test_valid_slug(self):
        assert validate_slug("coffee") == "coffee"
        assert validate_slug("espresso-latte") == "espresso-latte"
        assert validate_slug("cat-123") == "cat-123"

    def test_invalid_slug_traversal(self):
        with pytest.raises(ValueError):
            validate_slug("../etc")
        with pytest.raises(ValueError):
            validate_slug("a/b")
        with pytest.raises(ValueError):
            validate_slug("")

    def test_invalid_slug_format(self):
        with pytest.raises(ValueError):
            validate_slug("Coffee")  # uppercase not allowed by _SLUG_RE
        with pytest.raises(ValueError):
            validate_slug("-invalid")
        with pytest.raises(ValueError):
            validate_slug("invalid-")


class TestMenuCategory:
    def test_valid_construction(self):
        cat_id = uuid.uuid4()
        cat = MenuCategory(id=cat_id, name="Coffee", slug="coffee")
        assert cat.slug == "coffee"
        assert cat.name_ru == "Coffee"  # fallback to base
        assert cat.name_en == "Coffee"

    def test_name_min_length(self):
        with pytest.raises(ValueError, match=">=2"):
            MenuCategory(id=uuid.uuid4(), name="A", slug="a-valid")

    def test_slug_validation_in_post_init(self):
        with pytest.raises(ValueError):
            MenuCategory(id=uuid.uuid4(), name="Coffee", slug="InvalidSlug")

    def test_translated_fallbacks(self):
        cat = MenuCategory(
            id=uuid.uuid4(), name="Base", slug="base", name_ru="Кофе", name_en="Coffee"
        )
        assert cat.name_ru == "Кофе"
        assert cat.name_en == "Coffee"
        assert cat.name_ro == "Base"  # fallback


class TestMenuItem:
    def test_valid_construction(self):
        cat_id = uuid.uuid4()
        item = MenuItem(
            id=uuid.uuid4(),
            title="Latte",
            slug="latte",
            description="Tasty coffee with milk and foam",
            price=Decimal("4.5"),
            category_id=cat_id,
        )
        assert item.slug == "latte"
        assert item.title_ru == "Latte"
        assert item.is_available is False  # not published yet

    def test_title_min_length(self):
        with pytest.raises(ValueError, match="Title must be >=2"):
            MenuItem(
                id=uuid.uuid4(),
                title="A",
                slug="a",
                description="Long enough description",
                price=Decimal("1"),
                category_id=uuid.uuid4(),
            )

    def test_price_must_be_positive(self):
        with pytest.raises(ValueError, match="Price must be >0"):
            MenuItem(
                id=uuid.uuid4(),
                title="Latte",
                slug="latte",
                description="Long enough description",
                price=Decimal("0"),
                category_id=uuid.uuid4(),
            )

    def test_stock_quantity_negative(self):
        with pytest.raises(ValueError, match="stock_quantity must be >=0"):
            MenuItem(
                id=uuid.uuid4(),
                title="Latte",
                slug="latte",
                description="Long enough description",
                price=Decimal("1"),
                category_id=uuid.uuid4(),
                stock_quantity=-1,
            )

    def test_published_description_gate(self):
        # When status is PUBLISHED, description <10 should fail in __post_init__
        with pytest.raises(ValueError, match="Description must be >=10"):
            MenuItem(
                id=uuid.uuid4(),
                title="Latte",
                slug="latte",
                description="short",
                price=Decimal("1"),
                category_id=uuid.uuid4(),
                status=MenuItemStatus.PUBLISHED,
            )

    def test_localized_title_fallback(self):
        cat_id = uuid.uuid4()
        item = MenuItem(
            id=uuid.uuid4(),
            title="Base",
            slug="base",
            description="Long enough description for publish",
            price=Decimal("2"),
            category_id=cat_id,
            title_ru="Латте",
            title_en="",
            title_ro=None,
        )
        # en empty -> fallback to ru per get_localized_title
        assert item.get_localized_title("en") == "Латте"
        assert (
            item.get_localized_title("ro") == "Base"
            or item.get_localized_title("ro") == "Латте"
        )  # fallback chain
        assert item.get_localized_title("ru") == "Латте"

    def test_is_available_logic(self):
        cat_id = uuid.uuid4()
        item = MenuItem(
            id=uuid.uuid4(),
            title="Latte",
            slug="latte",
            description="Long enough description",
            price=Decimal("1"),
            category_id=cat_id,
            stock_quantity=5,
            is_published=True,
            status=MenuItemStatus.PUBLISHED,
        )
        assert item.is_available is True
        item.stock_quantity = 0
        assert item.is_available is False
        item.stock_quantity = None
        assert item.is_available is True  # unlimited


class TestOrderLineAndOrder:
    def test_order_line_quantity_positive(self):
        with pytest.raises(ValueError):
            OrderLine(
                menu_item_id=uuid.uuid4(), quantity=0, price_snapshot=Decimal("1")
            )

    def test_order_total_mismatch(self):
        line = OrderLine(
            menu_item_id=uuid.uuid4(), quantity=2, price_snapshot=Decimal("5")
        )
        with pytest.raises(ValueError, match="Total mismatch"):
            Order(id=uuid.uuid4(), lines=[line], total=Decimal("9"))  # should be 10

    def test_order_valid_total(self):
        line = OrderLine(
            menu_item_id=uuid.uuid4(), quantity=2, price_snapshot=Decimal("5")
        )
        order = Order(id=uuid.uuid4(), lines=[line], total=Decimal("10"))
        assert order.total == Decimal("10")

    def test_order_must_have_lines(self):
        with pytest.raises(ValueError, match="at least 1 line"):
            Order(id=uuid.uuid4(), lines=[], total=Decimal("0"))
