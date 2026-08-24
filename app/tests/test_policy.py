from app.services.policy_service import policy_service

def test_search_policy_exact_match():
    res = policy_service.search("return window")
    assert res.found is True
    # Should match section 2.1
    assert any("2.1" in sec["section_number"] for sec in res.matched_sections)

def test_search_policy_shoes_box():
    res = policy_service.search("shoes box")
    assert res.found is True
    # Should match section 2.5
    assert any("2.5" in sec["section_number"] for sec in res.matched_sections)

def test_search_policy_missing():
    res = policy_service.search("xyz_unmatched_query")
    assert res.found is False
    assert not res.matched_sections
