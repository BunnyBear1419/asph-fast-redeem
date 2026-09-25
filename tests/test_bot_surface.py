import ast
from pathlib import Path


def _commands(path):
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        for decorator in getattr(node, "decorator_list", []):
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "bot":
                    if decorator.func.attr == "tree" and isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                        for kw in decorator.keywords:
                            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                                found.append(kw.value.value)
    return found


def test_public_command_surface_is_dashboard_only():
    assert sorted(_commands("bot.py")) == ["dashboard", "tools"]
    assert _commands("alu_tools.py") == []
