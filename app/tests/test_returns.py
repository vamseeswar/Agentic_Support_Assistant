import pytest
from app.services.return_service import return_service

def test_return_eligibility_in_transit():
    # TR-4521 is in_transit
    res = return_service.check_eligibility("TR-4521")
    assert res.eligible is False
    assert any("not yet been delivered" in r for r in res.reasons)

def test_return_eligibility_delivered_eligible():
    # TR-4522 is delivered and eligible (Linen Blazer)
    res = return_service.check_eligibility("TR-4522")
    assert res.eligible is True
    assert "return_for_refund" in res.allowed_actions

def test_return_eligibility_jewellery():
    # TR-4523 is jewellery (Gold Hoop Earrings) AND delivered well outside the 30-day window.
    res = return_service.check_eligibility("TR-4523")
    assert res.eligible is False
    assert any("window" in r.lower() or "expired" in r.lower() for r in res.reasons)
    
def test_return_eligibility_final_sale():
    # TR-4528 is final sale
    res = return_service.check_eligibility("TR-4528")
    assert res.eligible is False
    assert "size_exchange" in res.allowed_actions

def test_exchange_eligibility_final_sale():
    # TR-4528 final sale can be exchanged
    res = return_service.check_eligibility("TR-4528", is_exchange=True)
    assert res.eligible is True
    assert "size_exchange" in res.allowed_actions
