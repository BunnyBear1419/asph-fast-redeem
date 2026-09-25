"""Import and normalize ALU source data into the central data layer.

This module deliberately does not scrape or invent game values. Source adapters
hand normalized dictionaries to the importer, which validates provenance,
normalizes identifiers, detects conflicts, and writes a replaceable JSON store.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from alu_data import (
    ALUDataStore,
    Car,
    Event,
    InMemoryALUDataRepository,
    SourceMetadata,
    Track,
    UpgradeStage,
    VerificationStatus,
)


class ImportValidationError(ValueError):
    """Raised when an imported record cannot safely enter the ALU data layer."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_id(value: Any, *, prefix: str = "") -> str:
    text = str(value or "").strip().casefold()
    if prefix and text.startswith(prefix):
        text = text[len(prefix):]
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if not text:
        raise ImportValidationError("A stable record identifier is required.")
    return f"{prefix}{text}" if prefix else text


def _verification(value: Any) -> VerificationStatus:
    if isinstance(value, VerificationStatus):
        return value
    try:
        return VerificationStatus(str(value or "unknown"))
    except ValueError as exc:
        raise ImportValidationError(f"Unknown verification status: {value!r}") from exc


def _provenance(raw: Mapping[str, Any], source: SourceMetadata) -> dict[str, Any]:
    collected_at = str(raw.get("collected_at") or source.collected_at or utc_now())
    return {
        "source": source.source_id,
        "source_url": raw.get("source_url") or source.url,
        "collected_at": collected_at,
        "game_version": raw.get("game_version") or source.game_version,
        "verification": _verification(raw.get("verification", source.verification)),
        "notes": str(raw.get("notes") or ""),
    }


def normalize_car(raw: Mapping[str, Any], source: SourceMetadata) -> Car:
    name = str(raw.get("name") or "").strip()
    if not name:
        raise ImportValidationError("Car name is required.")
    car_id = normalize_id(raw.get("id") or name, prefix="car:")
    stats = {str(k): float(v) for k, v in (raw.get("stats") or {}).items()}
    blueprints = {str(k): int(v) for k, v in (raw.get("blueprints") or {}).items()}
    return Car(
        id=car_id,
        name=name,
        manufacturer=raw.get("manufacturer"),
        class_name=raw.get("class_name"),
        star_levels=int(raw.get("star_levels") or 0),
        max_rank=int(raw["max_rank"]) if raw.get("max_rank") is not None else None,
        stats=stats,
        blueprints=blueprints,
        **_provenance(raw, source),
    )


def normalize_upgrade(raw: Mapping[str, Any], source: SourceMetadata) -> UpgradeStage:
    car_id = normalize_id(raw.get("car_id"), prefix="car:")
    star = int(raw.get("star_level") or 0)
    stage = int(raw.get("stage") or 0)
    if star < 1 or stage < 1:
        raise ImportValidationError("Upgrade star_level and stage must both be positive.")
    costs = {str(k): int(v) for k, v in (raw.get("costs") or {}).items()}
    parts = {str(k): int(v) for k, v in (raw.get("import_parts") or {}).items()}
    return UpgradeStage(
        id=normalize_id(raw.get("id") or f"{car_id}-{star}-{stage}"),
        car_id=car_id,
        star_level=star,
        stage=stage,
        rank=int(raw["rank"]) if raw.get("rank") is not None else None,
        costs=costs,
        import_parts=parts,
        **_provenance(raw, source),
    )


def normalize_track(raw: Mapping[str, Any], source: SourceMetadata) -> Track:
    name = str(raw.get("name") or "").strip()
    if not name:
        raise ImportValidationError("Track name is required.")
    return Track(
        id=normalize_id(raw.get("id") or name, prefix="track:"),
        name=name,
        variant=raw.get("variant"),
        direction=raw.get("direction"),
        location=raw.get("location"),
        distance_km=float(raw["distance_km"]) if raw.get("distance_km") is not None else None,
        **_provenance(raw, source),
    )


def normalize_event(raw: Mapping[str, Any], source: SourceMetadata) -> Event:
    name = str(raw.get("name") or "").strip()
    if not name:
        raise ImportValidationError("Event name is required.")
    return Event(
        id=normalize_id(raw.get("id") or name, prefix="event:"),
        name=name,
        event_type=raw.get("event_type"),
        start_date=raw.get("start_date"),
        end_date=raw.get("end_date"),
        track_ids=[normalize_id(x, prefix="track:") for x in (raw.get("track_ids") or [])],
        car_ids=[normalize_id(x, prefix="car:") for x in (raw.get("car_ids") or [])],
        rewards=list(raw.get("rewards") or []),
        **_provenance(raw, source),
    )


def _quality(record: Any) -> tuple[int, str]:
    rank = {
        VerificationStatus.VERIFIED_CURRENT: 3,
        VerificationStatus.UNKNOWN: 2,
        VerificationStatus.OLDER_REFERENCE: 1,
    }[record.verification]
    return rank, record.collected_at


class ALUImporter:
    """Merge normalized records while keeping conflicts explicit.

    A higher verification status wins. If both records have the same status,
    the newer collection timestamp wins. Conflicts are returned to the caller
    rather than silently discarded.
    """

    def __init__(self, sources: Iterable[SourceMetadata]):
        self.sources = {source.source_id: source for source in sources}
        self.conflicts: list[dict[str, Any]] = []

    def import_records(
        self,
        *,
        source_id: str,
        cars: Iterable[Mapping[str, Any]] = (),
        upgrades: Iterable[Mapping[str, Any]] = (),
        tracks: Iterable[Mapping[str, Any]] = (),
        events: Iterable[Mapping[str, Any]] = (),
        base: ALUDataStore | None = None,
    ) -> ALUDataStore:
        source = self.sources.get(source_id)
        if source is None:
            raise ImportValidationError(f"Unregistered source: {source_id}")

        old = base or ALUDataStore(sources=self.sources.values())
        old_repo = old.repository
        car_map = dict(getattr(old_repo, "cars", {}))
        upgrade_map = dict(getattr(old_repo, "upgrades", {}))
        track_map = dict(getattr(old_repo, "tracks", {}))
        event_map = dict(getattr(old_repo, "events", {}))

        def merge(target: dict, key: Any, incoming: Any, kind: str) -> None:
            current = target.get(key)
            if current is None:
                target[key] = incoming
                return
            if asdict(current) == asdict(incoming):
                return
            winner = incoming if _quality(incoming) > _quality(current) else current
            target[key] = winner
            self.conflicts.append({
                "kind": kind,
                "id": str(key),
                "kept_source": winner.source,
                "discarded_source": current.source if winner is incoming else incoming.source,
                "reason": "verification_then_collection_date",
            })

        for raw in cars:
            record = normalize_car(raw, source)
            merge(car_map, record.id, record, "car")
        for raw in upgrades:
            record = normalize_upgrade(raw, source)
            merge(upgrade_map, (record.car_id, record.star_level, record.stage), record, "upgrade")
        for raw in tracks:
            record = normalize_track(raw, source)
            merge(track_map, record.id, record, "track")
        for raw in events:
            record = normalize_event(raw, source)
            merge(event_map, record.id, record, "event")

        return ALUDataStore(
            sources=self.sources.values(),
            repository=InMemoryALUDataRepository(
                cars=car_map.values(),
                upgrades=upgrade_map.values(),
                tracks=track_map.values(),
                events=event_map.values(),
            ),
        )


def save_store(store: ALUDataStore, path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(store.export_json(), indent=2, sort_keys=True), encoding="utf-8")


def load_records_json(path: str | Path) -> dict[str, list[dict[str, Any]]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        "cars": list(payload.get("cars", [])),
        "upgrade_stages": list(payload.get("upgrade_stages", [])),
        "tracks": list(payload.get("tracks", [])),
        "events": list(payload.get("events", [])),
    }
