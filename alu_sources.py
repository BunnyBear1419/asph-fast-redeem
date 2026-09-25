"""Source adapters for the public ALU database pages.

The adapters are intentionally conservative: they fetch public HTML/JSON, but
only emit records when the page exposes a machine-readable structure we can
parse confidently. Raw values are never marked verified-current automatically.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Mapping

import aiohttp
from bs4 import BeautifulSoup

from alu_data import DEFAULT_SOURCES, SourceMetadata, VerificationStatus
from alu_importer import ALUImporter


class SourceFetchError(RuntimeError):
    pass


def _source(source_id: str) -> SourceMetadata:
    for source in DEFAULT_SOURCES:
        if source.source_id == source_id:
            return source
    raise SourceFetchError(f"Unknown source: {source_id}")


async def fetch_text(url: str, *, timeout: int = 20) -> str:
    headers = {"User-Agent": "Shohans-Companion-ALU-Data-Importer/1.0"}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    raise SourceFetchError(f"{url} returned HTTP {response.status}")
                return await response.text()
    except Exception as exc:
        raise SourceFetchError(f"Unable to fetch {url}: {exc}") from exc


def _json_scripts(html: str) -> list[Any]:
    soup = BeautifulSoup(html, "html.parser")
    payloads = []
    for script in soup.find_all("script"):
        text = script.string or script.get_text()
        if not text.strip():
            continue
        if script.get("type") == "application/json":
            try:
                payloads.append(json.loads(text))
            except json.JSONDecodeError:
                continue
    return payloads


def _extract_json_ld(html: str) -> list[Mapping[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[Mapping[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            value = json.loads(script.get_text())
        except json.JSONDecodeError:
            continue
        if isinstance(value, Mapping):
            rows.append(value)
        elif isinstance(value, list):
            rows.extend(x for x in value if isinstance(x, Mapping))
    return rows

A9GARAGE_BACKUP_BASE = "https://raw.githubusercontent.com/LostKnight-hz/a9garage-backup-data/main"
A9GARAGE_BACKUP_ENDPOINTS = {
    "cars": f"{A9GARAGE_BACKUP_BASE}/api_cars.json",
    "tracks": f"{A9GARAGE_BACKUP_BASE}/api_tracks.json",
    "calendar": f"{A9GARAGE_BACKUP_BASE}/api_calendar.json",
}


async def fetch_json(url: str, *, timeout: int = 30) -> Any:
    text = await fetch_text(url, timeout=timeout)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SourceFetchError(f"{url} did not return valid JSON") from exc


def _a9_car_record(row: list[Any], *, collected_at: str) -> dict[str, Any]:
    if len(row) < 18:
        raise SourceFetchError("A9Garage car row has an unexpected schema.")
    stock = row[6] if isinstance(row[6], list) else []
    maximum = row[7] if isinstance(row[7], list) else []
    stats = {}
    labels = ("rank", "top_speed", "acceleration", "handling", "nitro")
    for label, value in zip(labels, maximum[:5]):
        if isinstance(value, (int, float)):
            stats[label] = float(value)
    return {
        "id": row[0],
        "name": row[2],
        "manufacturer": row[1],
        "class_name": None,
        "star_levels": int(row[4]) if isinstance(row[4], int) else 0,
        "max_rank": int(maximum[0]) if maximum and isinstance(maximum[0], (int, float)) else None,
        "stats": stats,
        "blueprints": {},
        "source_url": A9GARAGE_BACKUP_ENDPOINTS["cars"],
        "collected_at": collected_at,
        "verification": VerificationStatus.UNKNOWN.value,
        "notes": json.dumps({
            "source_car_id": row[0],
            "raw_stat_vector_length": len(maximum),
            "stock_stat_vector_length": len(stock),
            "source_schema": "api_cars.json",
        }, separators=(",", ":")),
    }


async def collect_a9garage_backup_records() -> dict[str, Any]:
    """Collect structured A9Garage backup data without declaring it current."""
    collected_at = datetime.now(timezone.utc).isoformat()
    cars_payload, tracks_payload, calendar_payload = await asyncio.gather(
        fetch_json(A9GARAGE_BACKUP_ENDPOINTS["cars"]),
        fetch_json(A9GARAGE_BACKUP_ENDPOINTS["tracks"]),
        fetch_json(A9GARAGE_BACKUP_ENDPOINTS["calendar"]),
    )

    cars = [
        _a9_car_record(row, collected_at=collected_at)
        for row in cars_payload.get("cars", [])
        if isinstance(row, list)
    ]
    car_name_to_id = {
        str(row[2]).strip().casefold(): row[0]
        for row in cars_payload.get("cars", [])
        if isinstance(row, list) and len(row) > 2
    }

    tracks = []
    for row in tracks_payload.get("tracks", []):
        if not isinstance(row, Mapping) or not row.get("name"):
            continue
        tracks.append({
            "id": row.get("id"),
            "name": row["name"],
            "variant": row.get("type") or None,
            "direction": row.get("direction"),
            "location": row.get("region"),
            "distance_km": row.get("distance_km"),
            "source_url": A9GARAGE_BACKUP_ENDPOINTS["tracks"],
            "collected_at": collected_at,
            "verification": VerificationStatus.UNKNOWN.value,
            "notes": "Imported from A9Garage structured track snapshot.",
        })

    events = []
    for row in calendar_payload.get("events", []):
        if not isinstance(row, Mapping) or not row.get("name"):
            continue
        events.append({
            "id": f"a9garage-{row.get('name')}-{row.get('start')}",
            "name": row["name"],
            "event_type": row.get("type"),
            "start_date": row.get("start"),
            "end_date": row.get("end"),
            "track_ids": [],
            "car_ids": [
                car_name_to_id[name.strip().casefold()]
                for name in (row.get("cars") or [])
                if isinstance(name, str) and name.strip().casefold() in car_name_to_id
            ],
            "rewards": [],
            "source_url": A9GARAGE_BACKUP_ENDPOINTS["calendar"],
            "collected_at": collected_at,
            "verification": VerificationStatus.UNKNOWN.value,
            "notes": "Imported from A9Garage structured calendar snapshot.",
        })

    return {
        "source_id": "a9garage",
        "collected_at": collected_at,
        "cars": cars,
        "tracks": tracks,
        "events": events,
        "source_endpoints": dict(A9GARAGE_BACKUP_ENDPOINTS),
        "source_schema_version": cars_payload.get("v"),
        "counts": {"cars": len(cars), "tracks": len(tracks), "events": len(events)},
        "verification": VerificationStatus.UNKNOWN.value,
    }



async def collect_a9garage_index() -> dict[str, Any]:
    """Collect only discoverable source metadata from A9Garage.

    The current landing page exposes database/tool navigation but does not
    expose the full car dataset in server-rendered HTML, so this adapter
    returns no game records until a stable data endpoint is identified.
    """
    url = _source("a9garage").url
    html = await fetch_text(url)
    soup = BeautifulSoup(html, "html.parser")
    return {
        "source_id": "a9garage",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "title": soup.title.get_text(strip=True) if soup.title else "",
        "cars": [],
        "tracks": [],
        "events": [],
        "json_scripts": len(_json_scripts(html)),
        "json_ld": len(_extract_json_ld(html)),
        "notes": "Landing page inspected; no stable server-rendered ALU record payload imported.",
    }


async def collect_source_index(source_id: str) -> dict[str, Any]:
    source = _source(source_id)
    html = await fetch_text(source.url)
    soup = BeautifulSoup(html, "html.parser")
    return {
        "source_id": source_id,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "title": soup.title.get_text(strip=True) if soup.title else "",
        "json_scripts": len(_json_scripts(html)),
        "json_ld": len(_extract_json_ld(html)),
    }


def build_importer() -> ALUImporter:
    return ALUImporter(DEFAULT_SOURCES)


def provenance_for(source_id: str, *, notes: str = "") -> dict[str, Any]:
    source = _source(source_id)
    return {
        "source": source.source_id,
        "source_url": source.url,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "game_version": source.game_version,
        "verification": VerificationStatus.UNKNOWN.value,
        "notes": notes,
    }
