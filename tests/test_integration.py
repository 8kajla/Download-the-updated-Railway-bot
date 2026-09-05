import asyncio
from app.execution import FillEngine
from app.models import PendingOrder, OrderStatus
from app.strategy import weighted_target_band

def test_full_pending_to_fill_path():
    now = 1000.0
    engine = FillEngine(clock=lambda: now)
    order = PendingOrder(
        "oid", "condition", "token", "UP",
        target_price=0.25, notional=0.58,
        placed_ts=now, depth_ahead=10,
        window_end_ts=1300,
    )
    engine.place(order)
    assert engine.ledger.signals == 0
    assert engine.on_trade_print("token", 0.26, 100, 1001) == []
    assert order.status == OrderStatus.PENDING
    assert engine.on_trade_print("token", 0.25, 9, 1002) == []
    assert engine.on_trade_print("token", 0.24, 1, 1003) == [order]
    assert order.status == OrderStatus.FILLED
    assert engine.ledger.filled_count == 1

def test_distribution_scheduler_exact_over_1000():
    bands = [weighted_target_band(i) for i in range(1000)]
    assert bands.count("CHEAP") == 484
    assert bands.count("MID") == 306
    assert bands.count("CORE") == 122
    assert bands.count("HIGH") == 88
