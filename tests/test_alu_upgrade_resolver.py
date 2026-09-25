from alu_data import ALUDataStore, Car, InMemoryALUDataRepository, UpgradeCatalog, VerificationStatus
from alu_upgrade_resolver import ALUUpgradeResolver


def _store(catalog):
    car = Car(id="car:test", source="test", source_url="https://example.com/data", collected_at="2026-09-24", name="Test Car")
    repo = InMemoryALUDataRepository(cars=[car], upgrade_catalogs=[catalog])
    return ALUDataStore(repository=repo)


def test_unverified_catalog_refuses_upgrade_resolution():
    catalog = UpgradeCatalog(
        id="upgrade-catalog:test",
        source="a9garage",
        source_url="https://example.com/a9",
        collected_at="2026-09-24",
        verification=VerificationStatus.UNKNOWN,
        car_table_refs={"car:test": {"slot_1": 0, "slot_2": 0, "slot_3": 0, "slot_4": 0}},
    )
    result = ALUUpgradeResolver(_store(catalog)).resolve("car:test", 1, 1)
    assert result.ok is False
    assert result.status == "unknown"
    assert result.can_calculate is False


def test_verified_catalog_still_requires_explicit_semantics():
    catalog = UpgradeCatalog(
        id="upgrade-catalog:test",
        source="verified-test",
        source_url="https://example.com/data",
        collected_at="2026-09-24",
        verification=VerificationStatus.VERIFIED_CURRENT,
        car_table_refs={"car:test": {"slot_1": 0, "slot_2": 1, "slot_3": 2, "slot_4": 3}},
    )
    result = ALUUpgradeResolver(_store(catalog)).resolve("car:test", 1, 1)
    assert result.ok is False
    assert result.status == "mapping_not_implemented"
    assert result.can_calculate is False
    assert result.values["table_refs"]["slot_1"] == 0


def test_unverified_blueprints_are_not_current():
    catalog = UpgradeCatalog(
        id="upgrade-catalog:test",
        source="a9garage",
        source_url="https://example.com/a9",
        collected_at="2026-09-24",
        verification=VerificationStatus.UNKNOWN,
        car_blueprint_requirements={"car:test": [30, 45]},
    )
    result = ALUUpgradeResolver(_store(catalog)).resolve_blueprints("car:test")
    assert result.ok is False
    assert result.status == "unknown"
    assert result.values["requirements"] == [30, 45]
