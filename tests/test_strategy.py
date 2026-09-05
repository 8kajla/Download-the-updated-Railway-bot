from app.strategy import band_for_price, target_notional, choose_candidate
from app.models import Candidate, Market

def test_bands():
    assert band_for_price(.10)=="CHEAP"
    assert band_for_price(.30)=="MID"
    assert band_for_price(.70)=="CORE"
    assert band_for_price(.90)=="HIGH"

def test_sizing_ladder():
    assert target_notional("CHEAP",1)==.58
    assert target_notional("CHEAP",2)==.42
    assert target_notional("CHEAP",4)==.22
    assert target_notional("HIGH",2)==24.00
    assert target_notional("HIGH",4)==14.99

def test_candidate_has_no_signal_gate():
    m=Market("c","BTC",999,"u","d")
    c=Candidate(m,"u","UP",.15,"CHEAP",.15,.16,0)
    assert choose_candidate([c],"CHEAP") is c
