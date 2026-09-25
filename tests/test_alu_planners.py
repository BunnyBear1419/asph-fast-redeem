from alu_data import ALUDataStore, Car, EvoProfile, InMemoryALUDataRepository, UpgradeStage, VerificationStatus
from alu_planners import (
    blueprint_plan, star_up_plan, upgrade_stage_plan, import_parts_plan,
    rank_progress, garage_progress, event_reward_plan, compare_cars, evo_compare,
)


def meta(status=VerificationStatus.VERIFIED_CURRENT):
    return {"source": "test", "source_url": "https://example.com/source",
            "collected_at": "2026-09-24", "verification": status}


def test_blueprint_plan():
    r = blueprint_plan(10, 50, 20, 5)
    assert r["missing"] == 40
    assert r["remaining"] == 15


def test_star_up_plan():
    r = star_up_plan([0, 20, 30, 40], 1, 3, current_cards=10)
    assert r["required_cards"] == 50
    assert r["remaining_cards"] == 40


def test_upgrade_stage_plan_requires_verified_rows():
    row = UpgradeStage(id="x", car_id="car:test", star_level=1, stage=1, costs={"credits": 1000}, **meta())
    store = ALUDataStore(repository=InMemoryALUDataRepository(upgrades=[row]))
    r = upgrade_stage_plan(store, "car:test", 1, 0, 1, 1)
    assert r["ok"] is True and r["totals"]["credits"] == 1000


def test_upgrade_stage_plan_blocks_unverified_rows():
    row = UpgradeStage(id="x", car_id="car:test", star_level=1, stage=1, costs={"credits": 1000},
                       **meta(VerificationStatus.UNKNOWN))
    store = ALUDataStore(repository=InMemoryALUDataRepository(upgrades=[row]))
    assert upgrade_stage_plan(store, "car:test", 1, 0, 1, 1)["status"] == "unverified_stage"


def test_import_parts_plan():
    r = import_parts_plan({"engine": 2}, {"engine": 5, "nitro": 1})
    assert r["total_needed"] == 4


def test_rank_and_garage_progress():
    assert rank_progress(1200, 1500)["completion_percent"] == 80
    assert garage_progress(3, 5)["remaining"] == 2


def test_event_reward_plan():
    r = event_reward_plan(10, 5, 40, 10)
    assert r["expected_attempts"] == 6
    assert r["target_reachable_with_capacity"]


def test_car_and_evo_lookup():
    a = Car(id="car:a", name="A", stats={"speed": 100}, **meta())
    b = Car(id="car:b", name="B", stats={"speed": 90}, **meta())
    ea = EvoProfile(id="e:a", car_id="car:a", **meta())
    eb = EvoProfile(id="e:b", car_id="car:b", **meta())
    store = ALUDataStore(repository=InMemoryALUDataRepository(cars=[a, b], evo_profiles=[ea, eb]))
    assert compare_cars(store, "A", "B")["ok"]
    assert evo_compare(store, "A", "B")["ok"]
