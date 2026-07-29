"""Pure domain logic - must never import infrastructure.

tests/architecture/test_layering.py exists to catch a violation of
exactly this rule.
"""

import os  # deliberate ruff break: unused import (F401)


def order_total(unit_price: float, quantity: int) -> float:
    """Total cost of `quantity` units at `unit_price`."""
    return unit_price * quantity
