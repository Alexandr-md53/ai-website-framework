from decimal import Decimal
import pytest

from showcases.plant_nursery.domain.pricing import PriceCalculator, DiscountPolicy


class TestPlantPricing:
    def test_calculate_base_price_without_discount(self):
        """Базовый расчёт стоимости позиции без скидок."""
        calculator = PriceCalculator()
        total = calculator.calculate_total(
            unit_price=Decimal("1500.00"),
            quantity=3,
            discount_policy=DiscountPolicy.NONE,
        )
        assert total == Decimal("4500.00")

    def test_apply_volume_discount_for_large_orders(self):
        """Скидка 10% при заказе от 10 единиц одного наименования."""
        calculator = PriceCalculator()
        total = calculator.calculate_total(
            unit_price=Decimal("1000.00"),
            quantity=10,
            discount_policy=DiscountPolicy.VOLUME,
        )
        # 10 * 1000 * 0.90 = 9000.00
        assert total == Decimal("9000.00")

    def test_apply_seasonal_discount(self):
        """Сезонная скидка 15% на саженцы."""
        calculator = PriceCalculator()
        total = calculator.calculate_total(
            unit_price=Decimal("2000.00"),
            quantity=2,
            discount_policy=DiscountPolicy.SEASONAL,
        )
        # 2 * 2000 * 0.85 = 3400.00
        assert total == Decimal("3400.00")

    def test_reject_negative_or_zero_price(self):
        """Проверка защиты от некорректной цены."""
        calculator = PriceCalculator()
        with pytest.raises(ValueError, match="Unit price must be positive"):
            calculator.calculate_total(
                unit_price=Decimal("-100.00"),
                quantity=1,
                discount_policy=DiscountPolicy.NONE,
            )
