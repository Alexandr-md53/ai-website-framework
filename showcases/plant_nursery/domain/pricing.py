from decimal import Decimal
from enum import Enum


class DiscountPolicy(str, Enum):
    NONE = "NONE"
    VOLUME = "VOLUME"
    SEASONAL = "SEASONAL"


class PriceCalculator:
    _DISCOUNTS = {
        DiscountPolicy.NONE: Decimal("0.00"),
        DiscountPolicy.VOLUME: Decimal("0.10"),
        DiscountPolicy.SEASONAL: Decimal("0.15"),
    }

    def calculate_total(
        self,
        unit_price: Decimal,
        quantity: int,
        discount_policy: DiscountPolicy = DiscountPolicy.NONE,
    ) -> Decimal:
        if unit_price <= Decimal("0.00"):
            raise ValueError("Unit price must be positive")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")

        discount_rate = self._DISCOUNTS.get(discount_policy, Decimal("0.00"))
        subtotal = unit_price * Decimal(quantity)
        total = subtotal * (Decimal("1.00") - discount_rate)

        return total.quantize(Decimal("0.01"))
