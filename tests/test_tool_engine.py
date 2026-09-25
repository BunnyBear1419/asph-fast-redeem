from alu_calculators import hunt_estimate, race_model, search_summary
from alu_data import load_default_store


def test_hunt_estimate_rejects_zero_drop_rate():
    try:
        hunt_estimate(0, 10, 0)
    except ValueError as exc:
        assert "greater than zero" in str(exc)
    else:
        raise AssertionError("zero drop rate must be rejected")


def test_race_model_requires_shared_stats():
    try:
        race_model({"speed": 100}, {"handling": 100}, 3)
    except ValueError as exc:
        assert "shared numeric stat" in str(exc)
    else:
        raise AssertionError("non-overlapping stats must be rejected")


def test_default_data_search_is_safe_when_empty():
    store = load_default_store()
    assert search_summary(store, "cars", "definitely-not-a-real-car") == []
