import time
from collections import defaultdict
from .models import PendingOrder, OrderStatus, Position, Ledger

class FillEngine:
    """Realistic paper fill simulator: resting BUYs fill only from qualifying trade prints."""
    def __init__(self, ledger=None, clock=time.time):
        self.clock = clock
        self.orders = {}
        self.by_token = defaultdict(set)
        self.ledger = ledger or Ledger()

    def place(self, order: PendingOrder):
        if order.status != OrderStatus.PENDING:
            raise ValueError("Only PENDING orders can be placed")
        self.orders[order.order_id] = order
        self.by_token[order.token].add(order.order_id)

    def on_trade_print(self, token, trade_price, trade_size, trade_ts=None):
        if trade_ts is None:
            trade_ts = self.clock()
        if trade_size <= 0 or trade_price <= 0:
            return []
        filled = []
        for oid in list(self.by_token.get(token, ())):
            o = self.orders[oid]
            if o.status != OrderStatus.PENDING:
                continue
            if trade_price <= o.target_price:
                o.cum_volume += trade_size
                if o.cum_volume >= max(0.0, o.depth_ahead):
                    o.status = OrderStatus.FILLED
                    o.fill_price = min(trade_price, o.target_price)
                    o.fill_ts = trade_ts
                    o.fill_latency_s = max(0.0, trade_ts - o.placed_ts)
                    pos = Position(o.order_id, o.condition_id, o.token, o.side,
                                   o.fill_price, o.notional, trade_ts)
                    self.ledger.filled.append(pos)
                    filled.append(o)
        return filled

    def expire(self, now=None):
        now = self.clock() if now is None else now
        expired = []
        for o in self.orders.values():
            if o.status == OrderStatus.PENDING and now >= o.window_end_ts:
                o.status = OrderStatus.EXPIRED_UNFILLED
                self.ledger.expired.append(o)
                expired.append(o)
        return expired

    def pending_for_market(self, condition_id):
        return [o for o in self.orders.values()
                if o.condition_id == condition_id and o.status == OrderStatus.PENDING]
