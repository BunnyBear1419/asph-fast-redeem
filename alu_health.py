"""ALU data health and update-diff tools for Shohan's Companion.

This module audits the central data layer without inventing game values. It reports
provenance gaps, verification state, duplicate logical records, and differences
between two ALU data snapshots.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any

from alu_data import ALUDataStore, VerificationStatus


def _records(store: ALUDataStore, collection: str) -> list[Any]:
    repo = store.repository
    mapping = {
        "cars": "cars",
        "upgrade_stages": "upgrades",
        "upgrade_catalogs": "upgrade_catalogs",
        "evo_profiles": "evo_profiles",
        "tracks": "tracks",
        "events": "events",
    }
    return list(getattr(repo, mapping[collection], {}).values())


def _logical_key(record: Any) -> str:
    return str(getattr(record, "id", ""))


def audit_data(store: ALUDataStore) -> dict[str, Any]:
    """Return a machine-readable health report for the current ALU store."""
    collections = ("cars", "upgrade_stages", "upgrade_catalogs", "evo_profiles", "tracks", "events")
    by_collection: dict[str, Any] = {}
    duplicate_ids: dict[str, list[str]] = {}
    missing_provenance: list[dict[str, str]] = []
    verification_counts: Counter[str] = Counter()

    for collection in collections:
        records = _records(store, collection)
        seen: dict[str, int] = {}
        for record in records:
            key = _logical_key(record)
            seen[key] = seen.get(key, 0) + 1
            verification_counts[record.verification.value] += 1
            if not getattr(record, "source", "") or not getattr(record, "source_url", "") or not getattr(record, "collected_at", ""):
                missing_provenance.append({"collection": collection, "id": key})
        duplicates = sorted(key for key, count in seen.items() if count > 1)
        if duplicates:
            duplicate_ids[collection] = duplicates
        by_collection[collection] = {
            "count": len(records),
            "verified_current": sum(r.verification == VerificationStatus.VERIFIED_CURRENT for r in records),
            "older_reference": sum(r.verification == VerificationStatus.OLDER_REFERENCE for r in records),
            "unknown": sum(r.verification == VerificationStatus.UNKNOWN for r in records),
        }

    return {
        "status": "healthy" if not missing_provenance and not duplicate_ids else "attention_required",
        "collections": by_collection,
        "verification_counts": dict(verification_counts),
        "missing_provenance": missing_provenance,
        "duplicate_ids": duplicate_ids,
        "source_count": len(store.sources),
        "source_reuse_status": {k: v.reuse_status for k, v in store.sources.items()},
    }


def diff_data(old: ALUDataStore, new: ALUDataStore) -> dict[str, Any]:
    """Compare two stores and report additions, removals, and changed records."""
    collections = ("cars", "upgrade_stages", "upgrade_catalogs", "evo_profiles", "tracks", "events")
    result: dict[str, Any] = {"collections": {}, "summary": {"added": 0, "removed": 0, "changed": 0}}

    for collection in collections:
        old_map = {_logical_key(r): r for r in _records(old, collection)}
        new_map = {_logical_key(r): r for r in _records(new, collection)}
        added = sorted(set(new_map) - set(old_map))
        removed = sorted(set(old_map) - set(new_map))
        changed = sorted(k for k in set(old_map) & set(new_map) if asdict(old_map[k]) != asdict(new_map[k]))
        result["collections"][collection] = {
            "added": added,
            "removed": removed,
            "changed": changed,
        }
        result["summary"]["added"] += len(added)
        result["summary"]["removed"] += len(removed)
        result["summary"]["changed"] += len(changed)

    return result


def verification_summary(store: ALUDataStore) -> dict[str, int]:
    """Count records by verification state across the whole ALU store."""
    counts: Counter[str] = Counter()
    for collection in ("cars", "upgrade_stages", "upgrade_catalogs", "evo_profiles", "tracks", "events"):
        for record in _records(store, collection):
            counts[record.verification.value] += 1
    return dict(counts)
