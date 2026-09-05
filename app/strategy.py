BANDS = ("CHEAP", "MID", "CORE", "HIGH")
BAND_INDEX = {b:i for i,b in enumerate(BANDS)}
BAND_RANGES = {
    "CHEAP": (0.00, 0.30),
    "MID":   (0.30, 0.70),
    "CORE":  (0.70, 0.90),
    "HIGH":  (0.90, 1.00),
}
# Confirmed entry-count sizing from the supplied specification.
NOTIONALS = {
    "CHEAP": (0.58, 0.42, 0.22),
    "MID":   (2.02, 2.02, 1.90),
    "CORE":  (7.80, 7.06, 4.40),
    "HIGH":  (22.20, 24.00, 14.99),
}
# Confirmed 4-asset target distribution.
TARGET_DISTRIBUTION = {
    "CHEAP": 0.484,
    "MID": 0.306,
    "CORE": 0.122,
    "HIGH": 0.088,
}

def band_for_price(price):
    if not (0.0 <= price <= 1.0):
        return None
    for band, (lo, hi) in BAND_RANGES.items():
        if band == "HIGH":
            if lo <= price <= hi:
                return band
        elif lo <= price < hi:
            return band
    return None

def target_notional(band, entry_count):
    first, second_third, fourth_plus = NOTIONALS[band]
    if entry_count <= 1:
        return first
    if entry_count <= 3:
        return second_third
    return fourth_plus

def choose_candidate(candidates, target_band, thesis_side=None):
    # The supplied spec explicitly prohibits hard momentum/score/depth/spread gates.
    valid = [c for c in candidates if c is not None]
    if not valid:
        return None
    return min(valid, key=lambda c: (
        abs(BAND_INDEX[c.band] - BAND_INDEX[target_band]),
        -c.trajectory_likelihood,
    ))

def weighted_target_band(sequence_index):
    # Deterministic weighted scheduler: preserves the specified distribution
    # without adding a random gate that can make runs irreproducible.
    x = sequence_index % 1000
    if x < 484:
        return "CHEAP"
    if x < 790:
        return "MID"
    if x < 912:
        return "CORE"
    return "HIGH"
