"""Synchronize structured public ALU source data into the replaceable central store.

Usage:
    python alu_sync.py

The sync intentionally preserves UNKNOWN verification for third-party snapshots.
It does not claim that source freshness equals official game-version verification.
"""
from __future__ import annotations

import asyncio
import argparse

from alu_data import DEFAULT_DATA_PATH, load_default_store
from alu_importer import ALUImporter, save_store
from alu_sources import collect_a9garage_backup_records


async def sync_a9garage(output_path: str | None = None) -> dict:
    payload = await collect_a9garage_backup_records()
    importer = ALUImporter(())
    # The source registry is loaded from the existing store so future sources
    # can be merged without replacing unrelated records.
    store = load_default_store()
    importer = ALUImporter(store.sources.values())
    merged = importer.import_records(
        source_id="a9garage",
        cars=payload["cars"],
        upgrade_catalogs=payload.get("upgrade_catalogs", []),
        evo_profiles=payload.get("evo_profiles", []),
        tracks=payload["tracks"],
        events=payload["events"],
        base=store,
    )
    destination = output_path or str(DEFAULT_DATA_PATH)
    save_store(merged, destination)
    return {
        "destination": destination,
        "counts": merged.data_status(),
        "conflicts": len(importer.conflicts),
        "source_counts": payload["counts"],
        "verification": payload["verification"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync structured ALU source data.")
    parser.add_argument("--output", help="Optional output JSON path.")
    args = parser.parse_args()
    result = asyncio.run(sync_a9garage(args.output))
    print(result)


if __name__ == "__main__":
    main()
