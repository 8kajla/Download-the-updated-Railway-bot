def normalize_book(raw):
    bids = raw.get("bids") or []
    asks = raw.get("asks") or []
    def norm(rows):
        out=[]
        for x in rows:
            if isinstance(x, dict):
                p=x.get("price"); s=x.get("size")
            else:
                p=x[0] if len(x)>0 else None; s=x[1] if len(x)>1 else None
            try:
                out.append((float(p), float(s)))
            except (TypeError, ValueError):
                pass
        return out
    bids=sorted(norm(bids), reverse=True)
    asks=sorted(norm(asks))
    return bids, asks

def best_book(raw):
    bids, asks = normalize_book(raw)
    best_bid = bids[0][0] if bids else None
    best_ask = asks[0][0] if asks else None
    bid_depth = sum(s for p,s in bids if best_bid is not None and abs(p-best_bid)<1e-12)
    return best_bid, best_ask, bid_depth
