"""Pure domain logic - must never import infrastructure.

tests/architecture/test_layering.py exists to catch a violation of
exactly this rule.
"""


def order_total(unit_price: float, quantity: int) -> str:
    """Total cost of `quantity` units at `unit_price`.

    Deliberately broken: annotated to return str but actually returns a
    float - a pure static-analysis error. Runtime behavior (and therefore
    tests/test_domain.py) is unaffected, since Python never enforces
    return-type annotations - only mypy catches this.
    """
    return unit_price * quantity
