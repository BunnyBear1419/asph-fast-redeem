import ast
from pathlib import Path

from alu_tool_engine import TOOL_GROUPS, validate_tool_registry


TOOLS_FILE = Path("alu_tools.py")


def _literal_assignment(name):
    tree = ast.parse(TOOLS_FILE.read_text(encoding="utf-8"))
    node = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)
    )
    return ast.literal_eval(node.value)


def test_every_tool_is_categorized_exactly_once():
    definitions = _literal_assignment("TOOL_DEFINITIONS")
    categories = _literal_assignment("TOOL_CATEGORIES")
    grouped = [tool for category in categories.values() for tool in category["tools"]]
    assert set(grouped) == set(definitions)
    assert len(grouped) == len(set(grouped))


def test_category_tools_are_real_tools():
    definitions = _literal_assignment("TOOL_DEFINITIONS")
    categories = _literal_assignment("TOOL_CATEGORIES")
    unknown = {
        tool
        for category in categories.values()
        for tool in category["tools"]
        if tool not in definitions
    }
    assert unknown == set()


def test_engine_groups_match_tool_registry():
    definitions = _literal_assignment("TOOL_DEFINITIONS")
    assert validate_tool_registry(definitions) == []
    assert set(TOOL_GROUPS) == {
        "garage", "planning", "events", "tracks", "player", "redeem", "progress"
    }
