from app.execution import FillEngine
from app.models import PendingOrder, OrderStatus

def make(clock=100):
    e=FillEngine(clock=lambda: clock)
    o=PendingOrder("1","c","t","UP",.20,1.0,100,5.0,200)
    e.place(o)
    return e,o

def test_trade_print_does_not_fill_before_queue():
    e,o=make()
    assert e.on_trade_print("t",.19,2,101)==[]
    assert o.status==OrderStatus.PENDING

def test_trade_print_fills_after_queue():
    e,o=make()
    assert e.on_trade_print("t",.19,5,101)==[o]
    assert o.status==OrderStatus.FILLED
    assert o.fill_price==.19
    assert o.fill_latency_s==1

def test_trade_above_target_does_not_fill():
    e,o=make()
    e.on_trade_print("t",.21,100,101)
    assert o.status==OrderStatus.PENDING

def test_expiry():
    e,o=make()
    out=e.expire(200)
    assert out==[o]
    assert o.status==OrderStatus.EXPIRED_UNFILLED
    assert len(e.ledger.expired)==1
