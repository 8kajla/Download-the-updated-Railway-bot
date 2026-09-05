from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    EXPIRED_UNFILLED = "EXPIRED_UNFILLED"
    CANCELLED = "CANCELLED"

@dataclass
class Market:
    condition_id: str
    asset: str
    end_ts: float
    up_token: str
    down_token: str
    active: bool = True

@dataclass
class Candidate:
    market: Market
    token: str
    side: str
    price: float
    band: str
    best_bid: float
    best_ask: Optional[float]
    trajectory_likelihood: float = 0.0
    notional: float = 0.0
    queue_depth: float = 0.0

@dataclass
class PendingOrder:
    order_id: str
    condition_id: str
    token: str
    side: str
    target_price: float
    notional: float
    placed_ts: float
    depth_ahead: float
    window_end_ts: float
    cum_volume: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    fill_price: Optional[float] = None
    fill_ts: Optional[float] = None
    fill_latency_s: Optional[float] = None

@dataclass
class Position:
    order_id: str
    condition_id: str
    token: str
    side: str
    price: float
    notional: float
    filled_ts: float
    resolved: bool = False
    payout: Optional[float] = None

@dataclass
class Ledger:
    filled: list = field(default_factory=list)
    expired: list = field(default_factory=list)
    signals: int = 0

    @property
    def filled_count(self):
        return len(self.filled)

    @property
    def pnl(self):
        return sum((p.payout - p.notional) for p in self.filled
                   if p.resolved and p.payout is not None)
