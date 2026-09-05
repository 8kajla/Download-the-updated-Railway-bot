# Realistic CLOB Trader Replica — Railway

Paper-trading implementation based on the supplied strategy specification.

## Safety
This repository is **paper trading only**. It does not submit live orders. `PAPER_MODE=true` is the default.

## Core behavior
- Gamma market discovery
- CLOB REST book reads
- Trigger-free candidate selection
- CHEAP/MID/CORE/HIGH bands
- Confirmed entry sizing ladder
- Pending maker-order simulation
- Trade-tape fill callback
- Queue-depth approximation
- 90-second expiry cutoff
- Filled-only ledger
- WebSocket reconnect loop

The supplied specification explicitly says a signal must become a pending order and only real trade prints can cause a simulated fill; unfilled orders expire at the cutoff.

## Railway
1. Create a Railway service from this repository.
2. Railway will use the Dockerfile.
3. Add the variables from `.env.example`.
4. Keep `PAPER_MODE=true`.
5. Deploy and inspect logs for `START`, `MARKETS`, `ORDER_PENDING`, `EXPIRED`, and fill events.

## Important implementation note
The queue-depth approximation is intentionally conservative only when the book reports depth. A real exchange's exact private queue position is not observable. The current scaffold therefore keeps the fill model isolated in `app/execution.py` so the queue model can be calibrated against collected tape/book data before any live execution is considered.

## API verification
The market websocket implementation follows the documented public market channel subscription, `last_trade_price` event, and 10-second PING heartbeat pattern. See the official Polymarket market-channel documentation.


## Aggressive scanning
The strategy now separates **scan frequency** from **entry cadence**. Books are refreshed concurrently every 0.5s by default, while new entries retain the observed ~2s active cadence. Market discovery refreshes every 5s. This avoids waiting 2s to notice a new opportunity while avoiding uncontrolled REST request bursts.
