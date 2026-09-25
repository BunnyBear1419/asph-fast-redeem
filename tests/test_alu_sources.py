import pytest

from alu_sources import collect_a9garage_index, SourceFetchError


@pytest.mark.asyncio
async def test_a9garage_index_collection(monkeypatch):
    async def fake_fetch_text(url):
        return "<html><head><title>A9Garage Test</title></head><body></body></html>"
    monkeypatch.setattr("alu_sources.fetch_text", fake_fetch_text)
    result = await collect_a9garage_index()
    assert result["source_id"] == "a9garage"
    assert "cars" in result
    assert result["cars"] == []


def test_unknown_source_rejected():
    with pytest.raises(SourceFetchError):
        from alu_sources import _source
        _source("missing-source")


def test_a9garage_car_row_normalization_preserves_unknown_verification():
    from alu_sources import _a9_car_record, A9GARAGE_BACKUP_ENDPOINTS

    row = [
        123, "Test", "Test Car", 2, 5, 0,
        [1000, 250, 70, 80, 90, 1, 2, 3],
        [1500, 300, 75, 85, 95, 4, 5, 6],
        [], [], 0, 0, 0, 0, "test.webp", "10 / 20 / 30", 50, None,
    ]
    record = _a9_car_record(row, collected_at="2026-09-24T00:00:00+00:00")

    assert record["name"] == "Test Car"
    assert record["manufacturer"] == "Test"
    assert record["max_rank"] == 1500
    assert record["verification"] == "unknown"
    assert record["source_url"] == A9GARAGE_BACKUP_ENDPOINTS["cars"]


@pytest.mark.asyncio
async def test_sync_does_not_persist_reference_only_source(monkeypatch, tmp_path):
    import alu_sync

    payload = {
        "cars": [{
            "id": 1,
            "name": "Test Car",
            "manufacturer": "Test",
            "star_levels": 5,
            "max_rank": 1500,
            "stats": {"rank": 1500},
            "blueprints": {},
            "source_url": "https://example.test/cars.json",
            "collected_at": "2026-09-24T00:00:00+00:00",
            "verification": "unknown",
            "notes": "",
        }],
        "tracks": [],
        "events": [],
        "counts": {"cars": 1, "tracks": 0, "events": 0},
        "verification": "unknown",
    }
    async def fake_collect():
        return payload

    monkeypatch.setattr(alu_sync, "collect_a9garage_backup_records", fake_collect)
    result = await alu_sync.sync_a9garage(str(tmp_path / "alu_data.json"))
    assert result["persisted"] is False
    assert result["reuse_status"] == "reference_only"
    assert not (tmp_path / "alu_data.json").exists()


def test_a9garage_persistence_requires_explicit_redistribution_status():
    import asyncio
    import alu_sync

    async def fake_collect():
        return {"cars": [], "tracks": [], "events": [], "counts": {"cars": 0, "tracks": 0, "events": 0}, "verification": "unknown"}

    original = alu_sync.collect_a9garage_backup_records
    try:
        alu_sync.collect_a9garage_backup_records = fake_collect
        with pytest.raises(RuntimeError, match="not explicitly redistributable"):
            asyncio.run(alu_sync.sync_a9garage(persist=True))
    finally:
        alu_sync.collect_a9garage_backup_records = original


def test_a9garage_upgrade_catalog_preserves_indexed_tables():
    from alu_sources import _a9_upgrade_catalog

    payload = {
        "v": 1,
        "cars": [[1, "Test", "Car", 0, 3, 0, [], [], [], [], 0, 0, 0, 0, "x.webp", "5 / 8 / 30", 43, None]],
        "cost_tables": [[[1150]]],
        "exp_tables": [[[60]]],
        "upg_tables": [[[5, 0, 0]]],
        "bp_tables": [[8, 30]],
        "sum_tables": [[[20, 5000, 100000]]],
        "cd_tables": [[[1, 5, 68200]]],
    }
    record = _a9_upgrade_catalog(payload, collected_at="2026-09-24T00:00:00+00:00")

    assert record["source_schema"] == "api_cars.json"
    assert record["cost_tables"] == [[[1150]]]
    assert record["car_table_refs"]["car:1"]["slot_1"] == 0
    assert record["car_table_refs"]["car:1"]["slot_4"] == 0
    assert record["car_blueprint_requirements"]["car:1"] == [5, 8, 30]
    assert record["verification"] == "unknown"


def test_a9garage_evo_profile_links_to_numeric_car_id():
    from alu_sources import _a9_evo_profiles

    payload = {
        "evo_data": {
            "test": {
                "info": {"name": "Test Car", "stars": 5, "class": "D", "bp": [10]},
                "stock": {},
                "archetypes": [],
                "parts": {},
            }
        }
    }
    rows = _a9_evo_profiles(
        payload,
        collected_at="2026-09-24T00:00:00+00:00",
        car_name_to_id={"test car": "car:123"},
    )
    assert rows[0]["car_id"] == "car:123"
