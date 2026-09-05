import asyncio, logging, signal, time, uuid
from .config import Settings
from .client import PolymarketClient
from .book import best_book
from .models import Candidate, PendingOrder
from .strategy import band_for_price, choose_candidate, target_notional
from .execution import FillEngine
from .trade_ws import TradeTape

log = logging.getLogger(__name__)

class Bot:
    """
    Aggressive paper replica:
    - refreshes market discovery periodically
    - refreshes all relevant books concurrently at sub-second intervals
    - evaluates immediately after each book snapshot
    - consumes fills from the websocket trade tape
    - retains the observed ~2s active-entry cadence
    """
    def __init__(self, settings=None, clock=time.time):
        self.settings=settings or Settings()
        self.settings.validate()
        self.clock=clock
        self.client=PolymarketClient(self.settings.gamma_url,self.settings.clob_url)
        self.engine=FillEngine(clock=clock)
        self.stop_event=asyncio.Event()
        self.markets={}
        self.counts={}
        self.last_entry_ts=0.0
        self._book_lock=asyncio.Lock()

    async def token_supplier(self):
        tokens=[]
        now=self.clock()
        for m in self.markets.values():
            if now < m.end_ts-self.settings.cutoff_seconds:
                tokens.extend((m.up_token,m.down_token))
        return tokens

    async def on_trade(self, token, price, size, ts=None):
        filled=self.engine.on_trade_print(token,price,size,ts)
        for order in filled:
            log.info(
                "ORDER_FILLED id=%s token=%s side=%s target=%.4f fill=%.4f latency=%.3fs",
                order.order_id,order.token,order.side,order.target_price,
                order.fill_price,order.fill_latency_s
            )

    async def discover(self):
        markets=await self.client.discover_markets(self.settings.assets)
        self.markets={m.condition_id:m for m in markets}
        log.info("MARKETS discovered=%d assets=%s",len(markets),self.settings.assets)

    async def _candidate_for_token(self,m,token,side):
        try:
            raw=await self.client.book(token)
            bid,ask,depth=best_book(raw)
            if bid is None:
                return None
            if not (self.settings.min_price <= bid <= self.settings.max_price):
                return None
            band=band_for_price(bid)
            if band is None:
                return None
            return Candidate(
                market=m,token=token,side=side,price=bid,band=band,
                best_bid=bid,best_ask=ask,queue_depth=depth
            )
        except Exception as e:
            log.warning("BOOK_ERROR condition=%s token=%s err=%s",m.condition_id,token,e)
            return None

    async def evaluate_books(self):
        now=self.clock()
        if now-self.last_entry_ts < self.settings.cadence_seconds:
            return

        jobs=[]
        for m in self.markets.values():
            if not m.active or now >= m.end_ts-self.settings.cutoff_seconds:
                continue
            if len(self.engine.pending_for_market(m.condition_id)) >= self.settings.max_pending_per_market:
                continue
            jobs.extend([
                self._candidate_for_token(m,m.up_token,"UP"),
                self._candidate_for_token(m,m.down_token,"DOWN")
            ])

        candidates=[c for c in await asyncio.gather(*jobs) if c is not None]
        if not candidates:
            return

        # Aggressive selection: don't impose a momentum/depth/spread gate.
        # Prefer the regime that is currently most under-represented versus
        # the confirmed observed four-asset distribution.
        target={"CHEAP":.484,"MID":.306,"CORE":.122,"HIGH":.088}
        counts={b:0 for b in target}
        for o in self.engine.orders.values():
            if o.status.value not in ("PENDING","FILLED"):
                continue
            # Count by target price, not by signal request.
            b=band_for_price(o.target_price)
            if b: counts[b]+=1

        total=sum(counts.values())
        if total:
            deficits={b:target[b]-(counts[b]/total) for b in target}
            target_band=max(deficits,key=deficits.get)
        else:
            target_band="CHEAP"

        chosen=choose_candidate(candidates,target_band)
        if chosen is None:
            return

        key=(chosen.market.condition_id,chosen.side)
        entry_count=self.counts.get(key,0)+1
        notional=target_notional(chosen.band,entry_count)
        order=PendingOrder(
            order_id=str(uuid.uuid4()),
            condition_id=chosen.market.condition_id,
            token=chosen.token,
            side=chosen.side,
            target_price=chosen.price,
            notional=notional,
            placed_ts=now,
            depth_ahead=max(0.0,chosen.queue_depth),
            window_end_ts=chosen.market.end_ts-self.settings.cutoff_seconds
        )
        self.engine.ledger.signals+=1
        self.engine.place(order)
        self.counts[key]=entry_count
        self.last_entry_ts=now
        log.info(
            "ORDER_PENDING id=%s asset=%s band=%s side=%s price=%.4f "
            "notional=%.2f depth_ahead=%.4f",
            order.order_id,chosen.market.asset,chosen.band,chosen.side,
            chosen.price,notional,order.depth_ahead
        )

    async def run(self):
        await self.client.start()
        await self.discover()
        tape=TradeTape(self.settings.clob_ws_url,self.token_supplier,self.on_trade)
        tape_task=asyncio.create_task(tape.run())
        log.info(
            "START paper_mode=%s assets=%s cutoff=%ss cadence=%ss book_refresh=%ss",
            self.settings.paper_mode,self.settings.assets,
            self.settings.cutoff_seconds,self.settings.cadence_seconds,
            self.settings.book_refresh_seconds
        )
        next_discovery=self.clock()
        try:
            while not self.stop_event.is_set():
                now=self.clock()
                try:
                    if now>=next_discovery:
                        await self.discover()
                        next_discovery=now+self.settings.poll_seconds
                    self.engine.expire(now)
                    await self.evaluate_books()
                except Exception:
                    log.exception("LOOP_ERROR")
                try:
                    await asyncio.wait_for(
                        self.stop_event.wait(),
                        timeout=self.settings.book_refresh_seconds
                    )
                except asyncio.TimeoutError:
                    pass
        finally:
            tape.stop()
            tape_task.cancel()
            await asyncio.gather(tape_task,return_exceptions=True)
            await self.client.close()

    def stop(self):
        self.stop_event.set()

def main():
    settings=Settings()
    logging.basicConfig(
        level=getattr(logging,settings.log_level.upper(),logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    bot=Bot(settings)
    loop=asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGTERM,signal.SIGINT):
        try:
            loop.add_signal_handler(sig,bot.stop)
        except NotImplementedError:
            pass
    try:
        loop.run_until_complete(bot.run())
    finally:
        loop.close()

if __name__=="__main__":
    main()
