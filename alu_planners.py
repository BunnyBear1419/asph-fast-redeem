"""Planning helpers for Shohan's Companion.

These functions are deliberately data-driven: they calculate from explicit user
inputs or records already present in the centralized ALU data layer. They never
invent ALU game values.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

from alu_data import ALUDataStore, VerificationStatus


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return default


def blueprint_plan(current: float, target: float, owned: float = 0, wildcards: float = 0) -> dict[str, float]:
    missing = max(0.0, target - current)
    usable = max(0.0, owned) + max(0.0, wildcards)
    remaining = max(0.0, missing - usable)
    return {"target": target, "current": current, "missing": missing, "owned": max(0.0, owned),
            "wildcards": max(0.0, wildcards), "remaining": remaining}


def star_up_plan(requirements: Sequence[float], current_star: int, target_star: int,
                 current_cards: float = 0, wildcard_cards: float = 0) -> dict[str, Any]:
    if target_star < current_star:
        raise ValueError("Target star must be at least the current star.")
    req = [float(x) for x in requirements]
    needed = sum(req[current_star:target_star])
    available = max(0.0, current_cards) + max(0.0, wildcard_cards)
    return {"current_star": current_star, "target_star": target_star,
            "requirements": req[current_star:target_star], "required_cards": needed,
            "available_cards": available, "remaining_cards": max(0.0, needed - available)}


def upgrade_stage_plan(store: ALUDataStore, car_id: str, current_star: int, current_stage: int,
                       target_star: int, target_stage: int) -> dict[str, Any]:
    if target_star < current_star or (target_star == current_star and target_stage < current_stage):
        raise ValueError("Target configuration must be at or above the current configuration.")
    rows = []
    for star in range(current_star, target_star + 1):
        first = current_stage + 1 if star == current_star else 1
        last = target_stage if star == target_star else 4
        for stage in range(first, last + 1):
            row = store.upgrade_stage(car_id, star, stage)
            if row is None:
                return {"ok": False, "status": "missing_stage", "stages": rows}
            if row.verification != VerificationStatus.VERIFIED_CURRENT:
                return {"ok": False, "status": "unverified_stage", "stages": rows}
            rows.append(row)
    totals: dict[str, int] = {}
    for row in rows:
        for key, value in row.costs.items():
            totals[key] = totals.get(key, 0) + int(value)
    return {"ok": True, "status": "verified_current", "stages": rows, "totals": totals}


def import_parts_plan(current: Mapping[str, float], target: Mapping[str, float]) -> dict[str, Any]:
    rows = []
    for part in sorted(set(current) | set(target)):
        before = _num(current.get(part))
        goal = _num(target.get(part))
        rows.append({"part": part, "current": before, "target": goal, "needed": max(0.0, goal - before)})
    return {"rows": rows, "total_needed": sum(x["needed"] for x in rows)}


def rank_progress(current: float, target: float) -> dict[str, float]:
    if target <= 0:
        raise ValueError("Target rank must be greater than zero.")
    delta = target - current
    pct = max(0.0, min(100.0, current / target * 100))
    return {"current": current, "target": target, "delta": delta, "completion_percent": pct}


def garage_progress(completed: float, total: float) -> dict[str, float]:
    if total < 0:
        raise ValueError("Total cannot be negative.")
    done = max(0.0, min(completed, total))
    return {"completed": done, "total": total, "remaining": max(0.0, total - done),
            "completion_percent": 100.0 if total == 0 else done / total * 100}


def event_reward_plan(attempts: float, reward_per_attempt: float, target_reward: float,
                      current_reward: float = 0) -> dict[str, float]:
    remaining = max(0.0, target_reward - current_reward)
    per = max(0.0, reward_per_attempt)
    expected_attempts = None if per == 0 else remaining / per
    capacity = max(0.0, attempts)
    return {"attempts_available": capacity, "reward_per_attempt": per, "target_reward": target_reward,
            "current_reward": current_reward, "remaining_reward": remaining,
            "expected_attempts": expected_attempts,
            "target_reachable_with_capacity": expected_attempts is not None and expected_attempts <= capacity}


def compare_cars(store: ALUDataStore, car_a: str, car_b: str) -> dict[str, Any]:
    a = store.search_cars(car_a)[:1]
    b = store.search_cars(car_b)[:1]
    if not a or not b:
        return {"ok": False, "status": "car_not_found"}
    ca, cb = a[0], b[0]
    return {"ok": True, "a": ca, "b": cb, "stats": [
        {"stat": k, "a": ca.stats.get(k), "b": cb.stats.get(k)}
        for k in sorted(set(ca.stats) | set(cb.stats))
    ]}


def evo_compare(store: ALUDataStore, car_a: str, car_b: str) -> dict[str, Any]:
    a = store.search_cars(car_a)[:1]
    b = store.search_cars(car_b)[:1]
    if not a or not b:
        return {"ok": False, "status": "car_not_found"}
    ea, eb = store.evo_profile(a[0].id), store.evo_profile(b[0].id)
    if ea is None or eb is None:
        return {"ok": False, "status": "evo_profile_missing"}
    if ea.verification != VerificationStatus.VERIFIED_CURRENT or eb.verification != VerificationStatus.VERIFIED_CURRENT:
        return {"ok": False, "status": "unverified_evo"}
    return {"ok": True, "a": ea, "b": eb}


def track_lookup(store: ALUDataStore, query: str) -> list[dict[str, Any]]:
    return [{"id": x.id, "name": x.name, "variant": x.variant, "direction": x.direction,
             "location": x.location, "verification": x.verification.value, "source": x.source}
            for x in store.search_tracks(query)[:25]]


def event_lookup(store: ALUDataStore, query: str) -> list[dict[str, Any]]:
    return [{"id": x.id, "name": x.name, "event_type": x.event_type,
             "start_date": x.start_date, "end_date": x.end_date,
             "verification": x.verification.value, "source": x.source}
            for x in store.search_events(query)[:25]]
