import asyncio, json, logging, time
import aiohttp

log = logging.getLogger(__name__)

class TradeTape:
    """
    Public CLOB market websocket.
    Subscribes to token IDs and forwards last_trade_price events.
    Reconnects with exponential backoff and sends PING every 10 seconds.
    """
    def __init__(self, url, token_supplier, on_trade):
        self.url = url
        self.token_supplier = token_supplier
        self.on_trade = on_trade
        self._stop = asyncio.Event()
        self._subscribed = set()

    def stop(self):
        self._stop.set()

    async def _subscribe_new(self, ws):
        tokens = set(await self.token_supplier())
        new = sorted(tokens - self._subscribed)
        if new:
            # Initial subscription and subsequent updates are both supported.
            if not self._subscribed:
                await ws.send_json({
                    "assets_ids": new,
                    "type": "market",
                    "custom_feature_enabled": True,
                })
            else:
                for i in range(0, len(new), 200):
                    await ws.send_json({
                        "assets_ids": new[i:i+200],
                        "operation": "subscribe",
                        "custom_feature_enabled": True,
                    })
            self._subscribed.update(new)

    async def run(self):
        backoff = 1.0
        while not self._stop.is_set():
            try:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=None)
                ) as s:
                    async with s.ws_connect(self.url, heartbeat=None) as ws:
                        self._subscribed.clear()
                        await self._subscribe_new(ws)
                        backoff = 1.0
                        last_ping = time.monotonic()
                        last_sub_refresh = 0.0

                        while not self._stop.is_set():
                            now = time.monotonic()
                            if now - last_ping >= 10:
                                await ws.send_str("PING")
                                last_ping = now
                            if now - last_sub_refresh >= 20:
                                await self._subscribe_new(ws)
                                last_sub_refresh = now

                            try:
                                msg = await ws.receive(timeout=1.0)
                            except asyncio.TimeoutError:
                                continue
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                if msg.data == "PONG":
                                    continue
                                try:
                                    data = json.loads(msg.data)
                                except Exception:
                                    continue
                                for event in (data if isinstance(data, list) else [data]):
                                    if event.get("event_type") != "last_trade_price":
                                        continue
                                    token = event.get("asset_id")
                                    price = event.get("price")
                                    size = event.get("size")
                                    ts = event.get("timestamp")
                                    if token is None or price is None or size is None:
                                        continue
                                    try:
                                        t = float(ts) / 1000 if ts is not None and float(ts) > 1e11 else (float(ts) if ts is not None else None)
                                        await self.on_trade(
                                            str(token), float(price), float(size), t
                                        )
                                    except (TypeError, ValueError):
                                        continue
                            elif msg.type in (
                                aiohttp.WSMsgType.CLOSED,
                                aiohttp.WSMsgType.ERROR,
                            ):
                                raise ConnectionError("market websocket closed")
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.warning("WS_RECONNECT err=%s backoff=%s", e, backoff)
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=backoff)
                except asyncio.TimeoutError:
                    pass
                backoff = min(backoff * 2, 30.0)
