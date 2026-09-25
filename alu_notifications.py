"""Notification preference helpers for player tools."""
from __future__ import annotations

from typing import Any


DEFAULT_NOTIFICATION_SETTINGS = {
    "notifications": "off",
    "reminders": "off",
}


def normalize_notification_settings(settings: dict[str, Any]) -> dict[str, str]:
    result = dict(DEFAULT_NOTIFICATION_SETTINGS)
    for key in result:
        value = str(settings.get(key, result[key])).strip().casefold()
        if value in {"on", "off"}:
            result[key] = value
    return result


def should_notify(settings: dict[str, Any], kind: str) -> bool:
    normalized = normalize_notification_settings(settings)
    return normalized.get(kind, "off") == "on"
