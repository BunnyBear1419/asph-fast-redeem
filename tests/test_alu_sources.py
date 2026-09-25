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
