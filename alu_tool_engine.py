"""Shared ALU tool-engine helpers.

Keeps tool discovery, aliases, and safety metadata out of Discord view code.
"""
from __future__ import annotations

from typing import Any, Mapping


TOOL_ALIASES = {
    "upgrade": "upgrades",
    "upgrades": "upgrades",
    "calculator": "upgrades",
    "calc": "upgrades",
    "car search": "search",
    "track search": "maps",
    "event search": "calendar",
    "favorite": "favorites",
    "prefs": "settings",
    "redeem codes": "redeem",
}

TOOL_GROUPS = {
    "garage": {"upgrades", "blueprints", "upgrade_planner", "import_parts", "rank", "star_up", "garage_progress", "evo", "car_compare"},
    "planning": {"comparator", "priority", "hunt", "simulation", "rating", "cost"},
    "events": {"calendar", "events", "event_rewards"},
    "tracks": {"maps", "faq"},
    "player": {"garage", "favorites", "search", "settings"},
    "redeem": {"redeem"},
    "progress": {"data_health", "notes", "garage_progress"},
}


def resolve_tool_key(query: str, definitions: Mapping[str, Mapping[str, Any]]) -> str | None:
    raw = (query or "").strip().casefold()
    if not raw:
        return None
    candidate = TOOL_ALIASES.get(raw, raw)
    if candidate in definitions:
        return candidate
    matches = []
    for key, tool in definitions.items():
        haystack = " ".join([key, str(tool.get("label", "")), str(tool.get("description", ""))]).casefold()
        if raw in key.casefold() or raw in haystack:
            matches.append(key)
    return sorted(matches, key=lambda key: (len(key), key))[0] if matches else None


def search_tools(query: str, definitions: Mapping[str, Mapping[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    raw = (query or "").strip().casefold()
    if not raw:
        return []
    alias = TOOL_ALIASES.get(raw)
    results = []
    for key, tool in definitions.items():
        haystack = " ".join([key, str(tool.get("label", "")), str(tool.get("description", "")), *map(str, tool.get("fields", []))]).casefold()
        if alias == key:
            score = 100
        elif raw == key.casefold():
            score = 90
        elif raw in str(tool.get("label", "")).casefold():
            score = 75
        elif raw in haystack:
            score = 50
        else:
            continue
        results.append((score, key, tool))
    results.sort(key=lambda item: (-item[0], str(item[2].get("label", ""))))
    return [{"key": key, **dict(tool)} for _, key, tool in results[:limit]]


def tool_is_current_safe(tool_key: str, requires_verified_data: bool = False, verified: bool = False) -> bool:
    return not requires_verified_data or verified


def validate_tool_registry(
    definitions: Mapping[str, Mapping[str, Any]],
    groups: Mapping[str, set[str]] = TOOL_GROUPS,
) -> list[str]:
    """Return registry consistency errors without mutating either registry."""
    errors: list[str] = []
    definition_keys = set(definitions)
    grouped_keys = {key for keys in groups.values() for key in keys}
    missing_groups = sorted(definition_keys - grouped_keys)
    unknown_groups = sorted(grouped_keys - definition_keys)
    if missing_groups:
        errors.append(f"Uncategorized tools: {', '.join(missing_groups)}")
    if unknown_groups:
        errors.append(f"Unknown grouped tools: {', '.join(unknown_groups)}")
    for category, keys in groups.items():
        if not keys:
            errors.append(f"Empty tool group: {category}")
    return errors
