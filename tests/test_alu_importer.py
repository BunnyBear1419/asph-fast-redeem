from alu_data import ALUDataStore, SourceMetadata, VerificationStatus
from alu_importer import ALUImporter, ImportValidationError, normalize_car


def source(source_id="test", verification=VerificationStatus.VERIFIED_CURRENT):
    return SourceMetadata(
        source_id=source_id,
        name=source_id,
        url="https://example.com/source",
        collected_at="2026-09-24T00:00:00+00:00",
        verification=verification,
    )


def test_normalize_car_has_stable_id_and_provenance():
    car = normalize_car({"name": "Test Car", "stats": {"speed": 100}}, source())
    assert car.id == "car:test-car"
    assert car.stats["speed"] == 100
    assert car.source == "test"


def test_importer_keeps_higher_quality_record():
    importer = ALUImporter([source(), source("older", VerificationStatus.OLDER_REFERENCE)])
    base = importer.import_records(source_id="older", cars=[{"name": "Test Car", "stats": {"speed": 90}}])
    merged = importer.import_records(
        source_id="test",
        cars=[{"name": "Test Car", "stats": {"speed": 100}}],
        base=base,
    )
    assert merged.car("car:test-car").stats["speed"] == 100
    assert merged.car("car:test-car").verification == VerificationStatus.VERIFIED_CURRENT


def test_unknown_data_never_becomes_current():
    importer = ALUImporter([source("unknown", VerificationStatus.UNKNOWN)])
    store = importer.import_records(source_id="unknown", cars=[{"name": "Unverified Car"}])
    assert not store.can_present_as_current(store.car("car:unverified-car"))


def test_invalid_upgrade_rejected():
    importer = ALUImporter([source()])
    try:
        importer.import_records(
            source_id="test",
            upgrades=[{"car_id": "Test Car", "star_level": 0, "stage": 1}],
        )
    except ImportValidationError:
        return
    raise AssertionError("Invalid upgrade should be rejected")
