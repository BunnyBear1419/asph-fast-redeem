from alu_data import (
    ALUDataStore,
    Car,
    InMemoryALUDataRepository,
    SourceMetadata,
    VerificationStatus,
)
from alu_health import audit_data, diff_data, verification_summary


def source(status=VerificationStatus.UNKNOWN):
    return SourceMetadata(
        "test",
        "Test",
        "https://example.com",
        "2026-09-24",
        verification=status,
    )


def store(*cars):
    return ALUDataStore(
        sources=[source()],
        repository=InMemoryALUDataRepository(cars=cars),
    )


def car(car_id, name, status=VerificationStatus.UNKNOWN):
    return Car(
        id=car_id,
        source="test",
        source_url="https://example.com",
        collected_at="2026-09-24",
        verification=status,
        name=name,
    )


def test_health_reports_verification_counts():
    report = audit_data(store(
        car("car:a", "A"),
        car("car:b", "B", VerificationStatus.VERIFIED_CURRENT),
    ))
    assert report["status"] == "healthy"
    assert report["collections"]["cars"]["count"] == 2
    assert report["verification_counts"]["unknown"] == 1
    assert report["verification_counts"]["verified_current"] == 1


def test_update_diff_detects_added_removed_and_changed():
    old = store(car("car:a", "Old"))
    new = store(
        car("car:a", "New"),
        car("car:b", "Added"),
    )
    new.repository.cars.pop("car:a")
    new.repository.cars["car:a"] = car("car:a", "New")
    result = diff_data(old, new)
    assert result["collections"]["cars"]["added"] == ["car:b"]
    assert result["collections"]["cars"]["changed"] == ["car:a"]
    assert result["summary"]["added"] == 1
    assert result["summary"]["changed"] == 1


def test_verification_summary():
    report = verification_summary(store(
        car("car:a", "A", VerificationStatus.OLDER_REFERENCE),
        car("car:b", "B", VerificationStatus.VERIFIED_CURRENT),
    ))
    assert report == {"older_reference": 1, "verified_current": 1}
