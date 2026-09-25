from alu_data import Car, InMemoryALUDataRepository, UpgradeStage, VerificationStatus

def meta():
    return {"source":"test","source_url":"https://example.com/source","collected_at":"2026-09-24","verification":VerificationStatus.VERIFIED_CURRENT}

def test_car_search_and_provenance():
    car=Car(id="test-car",name="Test Car",**meta())
    repo=InMemoryALUDataRepository(cars=[car])
    assert repo.find_cars("test")[0].name=="Test Car"
    assert repo.get_car("test-car").verification==VerificationStatus.VERIFIED_CURRENT

def test_upgrade_lookup_is_centralized():
    stage=UpgradeStage(id="test-car-1-1",car_id="test-car",star_level=1,stage=1,costs={"credits":1000},**meta())
    repo=InMemoryALUDataRepository(upgrades=[stage])
    assert repo.get_upgrade_stage("test-car",1,1).costs["credits"]==1000

def test_unverified_data_is_not_current():
    m=meta(); m["verification"]=VerificationStatus.OLDER_REFERENCE
    car=Car(id="old-car",name="Old Car",**m)
    assert car.verification != VerificationStatus.VERIFIED_CURRENT
