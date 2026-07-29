"""Pure domain logic - must never import infrastructure.

tests/architecture/test_layering.py exists to catch a violation of
exactly this rule. Deliberately broken below: domain.py imports and calls
infrastructure directly. mypy and ruff both stay clean (the call is
correctly typed and the import is used) and the unit test's return value
is unaffected - only the architecture test catches this.
"""

from example_pkg.infrastructure import save_order


def order_total(unit_price: float, quantity: int) -> float:
    """Total cost of `quantity` units at `unit_price`."""
    total = unit_price * quantity
    save_order(order_id="fixture", total=total)
    return total
