from app.config import Settings
from app.models import Market, Candidate
from app.strategy import choose_candidate

def test_aggressive_defaults():
    s=Settings()
    assert s.book_refresh_seconds <= 0.5
    assert s.poll_seconds <= 5

def test_candidate_selection_does_not_gate_on_depth_or_spread():
    m=Market("c","BTC",9999,"u","d")
    a=Candidate(m,"u","UP",.15,"CHEAP",.15,None,0,0,0)
    b=Candidate(m,"d","DOWN",.16,"CHEAP",.16,.50,0,0,100000)
    assert choose_candidate([a,b],"CHEAP") in (a,b)
