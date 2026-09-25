from alu_calculators import compare_stats, hunt_estimate, priority_plan, race_model, rating_difference, event_plan, parse_stats

def test_parse_and_compare_stats():
    a=parse_stats("speed=350, acceleration=82")
    b=parse_stats("speed=360, acceleration=80")
    rows=compare_stats(a,b)
    assert rows[1]["delta"] == 10

def test_hunt_estimate():
    r=hunt_estimate(10,20,20)
    assert r["missing"] == 10
    assert r["expected_attempts"] == 50

def test_priority_is_transparent():
    r=priority_plan(2,80,50,60)
    assert 0 <= r["score"] <= 100
    assert r["urgency"] > 90

def test_race_model_uses_shared_inputs_only():
    r=race_model({"speed":100,"handling":50},{"speed":80,"handling":70},10)
    assert r["shared_stats"] == ["handling","speed"]
    assert round(r["a_share"]+r["b_share"],5) == 1

def test_rating_difference():
    assert rating_difference(1200,1150)["difference"] == 50

def test_event_plan():
    r=event_plan(5,30,50)
    assert r["remaining"] == 20
    assert r["completion_percent"] == 60
