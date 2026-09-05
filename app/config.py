from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    gamma_url: str = os.getenv("GAMMA_URL", "https://gamma-api.polymarket.com")
    clob_url: str = os.getenv("CLOB_URL", "https://clob.polymarket.com")
    clob_ws_url: str = os.getenv("CLOB_WS_URL", "wss://ws-subscriptions-clob.polymarket.com/ws/market")
    assets: tuple = tuple(x.strip().upper() for x in os.getenv("ASSETS", "BTC,ETH,SOL,BNB").split(",") if x.strip())
    paper_mode: bool = os.getenv("PAPER_MODE", "true").lower() == "true"
    poll_seconds: float = float(os.getenv("MARKET_POLL_SECONDS", "5"))
    book_refresh_seconds: float = float(os.getenv("BOOK_REFRESH_SECONDS", "0.5"))
    cadence_seconds: float = float(os.getenv("ENTRY_CADENCE_SECONDS", "2"))
    cutoff_seconds: int = int(os.getenv("CUTOFF_SECONDS", "90"))
    min_price: float = float(os.getenv("MIN_PRICE", "0.001"))
    max_price: float = float(os.getenv("MAX_PRICE", "0.999"))
    max_pending_per_market: int = int(os.getenv("MAX_PENDING_PER_MARKET", "50"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    def validate(self):
        if not self.assets:
            raise ValueError("ASSETS must contain at least one asset")
        if self.cutoff_seconds < 1:
            raise ValueError("CUTOFF_SECONDS must be positive")
        if self.cadence_seconds <= 0:
            raise ValueError("ENTRY_CADENCE_SECONDS must be positive")
        if not (0 < self.min_price < self.max_price < 1):
            raise ValueError("MIN_PRICE/MAX_PRICE must satisfy 0 < min < max < 1")
