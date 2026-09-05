import pytest
from app.book import best_book

def test_book_normalization():
    raw={"bids":[{"price":"0.19","size":"4"},{"price":"0.18","size":"9"}],
         "asks":[{"price":"0.21","size":"3"}]}
    bid,ask,depth=best_book(raw)
    assert bid==.19 and ask==.21 and depth==4

def test_empty_book():
    assert best_book({"bids":[],"asks":[]})==(None,None,0)
