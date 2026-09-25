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
from urllib.parse import urljoin

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
