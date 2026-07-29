"""Infrastructure - the layer domain.py must never import from."""


def save_order(order_id: str, total: float) -> None:
    """Pretend to persist an order - no real I/O, this is a fixture."""
    return None
