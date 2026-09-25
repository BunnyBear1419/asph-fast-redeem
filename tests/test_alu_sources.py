import pytest

from alu_sources import collect_a9garage_index, SourceFetchError


@pytest.mark.asyncio
async def test_a9garage_index_collection():
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
