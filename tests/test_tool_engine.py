from alu_tool_engine import resolve_tool_key, search_tools, tool_is_current_safe, validate_tool_registry

DEFINITIONS = {
    "upgrades": {"label": "Car Upgrades Calculator", "description": "Plan upgrades.", "fields": ["Car"]},
    "search": {"label": "Global ALU Search", "description": "Search cars and events.", "fields": ["Query"]},
}


def test_tool_alias_resolution():
    assert resolve_tool_key("upgrade", DEFINITIONS) == "upgrades"
    assert resolve_tool_key("car search", DEFINITIONS) == "search"


def test_tool_search_returns_ranked_match():
    results = search_tools("upgrade", DEFINITIONS)
    assert results and results[0]["key"] == "upgrades"


def test_tool_search_is_bounded_and_empty_safe():
    assert search_tools("", DEFINITIONS) == []
    assert len(search_tools("a", {str(i): {"label": str(i), "description": "a", "fields": []} for i in range(20)}, limit=5)) <= 5


def test_verified_data_gate():
    assert tool_is_current_safe("upgrades", requires_verified_data=False, verified=False)
    assert not tool_is_current_safe("upgrades", requires_verified_data=True, verified=False)
    assert tool_is_current_safe("upgrades", requires_verified_data=True, verified=True)


def test_tool_registry_validation():
    assert validate_tool_registry(DEFINITIONS, {"garage": {"upgrades"}, "player": {"search"}}) == []
    assert validate_tool_registry(DEFINITIONS, {"garage": {"upgrades"}})
