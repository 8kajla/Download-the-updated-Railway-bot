import asyncio, json, logging
import aiohttp

log = logging.getLogger(__name__)

class PolymarketClient:
    def __init__(self, gamma_url, clob_url):
        self.gamma_url = gamma_url.rstrip("/")
        self.clob_url = clob_url.rstrip("/")
        self.session = None

    async def start(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        )

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def _get_json(self, url, params=None):
        last = None
        for attempt in range(3):
            try:
                async with self.session.get(url, params=params) as r:
                    r.raise_for_status()
                    return await r.json()
            except Exception as e:
                last = e
                await asyncio.sleep(0.5 * (2 ** attempt))
        raise last

    @staticmethod
    def _parse_ts(value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value) / 1000 if value > 1e11 else float(value)
        from datetime import datetime
        s = str(value)
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
        except ValueError:
            try:
                n = float(s)
                return n / 1000 if n > 1e11 else n
            except ValueError:
                return None

    async def discover_markets(self, assets):
        # Gamma is used only for discovery. We deliberately normalize several
        # observed field spellings because API payloads can evolve.
        data = await self._get_json(
            f"{self.gamma_url}/markets",
            {"active": "true", "closed": "false", "limit": 500},
        )
        if isinstance(data, dict):
            data = data.get("data") or data.get("markets") or []
        from .models import Market
        out = []
        for m in data:
            text = " ".join(
                str(m.get(k, "")) for k in
                ("question", "title", "slug", "description")
            ).lower()
            asset = next((a for a in assets if a.lower() in text), None)
            if not asset:
                continue
            # Require an explicit 5-minute signal where available. We do not
            # pretend that every crypto market is a 5-minute market.
            five_min = any(x in text for x in ("5m", "5-min", "5 min", "5 minute", "5-minute"))
            if not five_min:
                start = self._parse_ts(m.get("startDate") or m.get("start_date"))
                end = self._parse_ts(m.get("endDate") or m.get("end_date") or m.get("endDateIso"))
                if start is None or end is None or not (240 <= end - start <= 360):
                    continue
            end_ts = self._parse_ts(
                m.get("endDate") or m.get("end_date") or m.get("endDateIso")
            )
            if end_ts is None:
                continue

            raw_tokens = m.get("clobTokenIds") or m.get("clob_token_ids") or m.get("tokens") or []
            if isinstance(raw_tokens, str):
                try:
                    raw_tokens = json.loads(raw_tokens)
                except Exception:
                    raw_tokens = []
            up = down = None
            ids = []
            for t in raw_tokens:
                if isinstance(t, dict):
                    tid = str(t.get("token_id") or t.get("tokenId") or t.get("id") or "")
                    outcome = str(t.get("outcome") or t.get("name") or "").lower()
                    if tid:
                        ids.append(tid)
                        if outcome in ("up", "yes"):
                            up = tid
                        elif outcome in ("down", "no"):
                            down = tid
                else:
                    ids.append(str(t))
            if up is None or down is None:
                if len(ids) < 2:
                    continue
                up, down = ids[0], ids[1]

            cid = str(m.get("conditionId") or m.get("condition_id") or m.get("id") or "")
            if cid:
                out.append(Market(cid, asset, end_ts, up, down, True))
        return out

    async def book(self, token):
        return await self._get_json(f"{self.clob_url}/book", {"token_id": token})
