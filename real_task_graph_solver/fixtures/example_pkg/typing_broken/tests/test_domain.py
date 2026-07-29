from example_pkg.domain import order_total


def test_order_total_multiplies_price_by_quantity():
    assert order_total(unit_price=2.5, quantity=4) == 10.0
