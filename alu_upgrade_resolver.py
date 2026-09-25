"""Safe resolver for centralized ALU upgrade-stage data.

The resolver deliberately refuses to turn A9Garage's indexed source tables into
game-facing numbers until the table-index semantics are independently verified.
This prevents a plausible-looking but incorrect calculator result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from alu_data import ALUDataStore, UpgradeCatalog, VerificationStatus


@dataclass(frozen=True)
class UpgradeResolution:
    ok: bool
    status: str
    reason: str
    car_id: str
    star_level: int
    stage: int
    values: dict[str, Any] = field(default_factory=dict)
    source: str | None = None
    source_url: str | None = None

    @property
    def can_calculate(self) -> bool:
        return self.ok and self.status == VerificationStatus.VERIFIED_CURRENT.value


class ALUUpgradeResolver:
    """Resolve calculator inputs only when their semantics are safe to use."""

    def __init__(self, store: ALUDataStore):
        self.store = store

    def _catalog(self) -> UpgradeCatalog | None:
        return self.store.upgrade_catalog()

    def resolve(self, car_id: str, star_level: int, stage: int) -> UpgradeResolution:
        if star_level < 1 or stage < 1:
            return UpgradeResolution(False, "invalid_input", "Star level and stage must both be positive.", car_id, star_level, stage)

        car = self.store.car(car_id)
        if car is None:
            return UpgradeResolution(False, "missing_car", "Car is not present in the centralized ALU data layer.", car_id, star_level, stage)

        catalog = self._catalog()
        if catalog is None:
            return UpgradeResolution(False, "missing_catalog", "No centralized upgrade catalog is loaded.", car_id, star_level, stage)

        if catalog.verification != VerificationStatus.VERIFIED_CURRENT:
            return UpgradeResolution(
                False,
                catalog.verification.value,
                "Upgrade table semantics are not verified as current, so the calculator will not produce a game-value result.",
                car_id, star_level, stage,
                source=catalog.source, source_url=catalog.source_url,
            )

        refs = catalog.car_table_refs.get(car_id)
        if not refs:
            return UpgradeResolution(False, "missing_mapping", "No verified upgrade-table mapping exists for this car.", car_id, star_level, stage, source=catalog.source, source_url=catalog.source_url)

        # This branch is intentionally conservative. Even a verified catalog
        # must explicitly declare the meaning of each source-native slot before
        # raw indexed arrays can be translated into costs/parts.
        required = {"slot_1", "slot_2", "slot_3", "slot_4"}
        if set(refs) != required:
            return UpgradeResolution(False, "incomplete_mapping", "The catalog does not contain all four source-native slot mappings.", car_id, star_level, stage, source=catalog.source, source_url=catalog.source_url)

        return UpgradeResolution(
            False,
            "mapping_not_implemented",
            "A verified source exists, but source-table index semantics have not been explicitly declared. No guessed cost, XP, rank, or parts value is returned.",
            car_id, star_level, stage,
            values={"table_refs": dict(refs)},
            source=catalog.source, source_url=catalog.source_url,
        )

    def resolve_blueprints(self, car_id: str) -> UpgradeResolution:
        catalog = self._catalog()
        if catalog is None:
            return UpgradeResolution(False, "missing_catalog", "No centralized upgrade catalog is loaded.", car_id, 0, 0)
        requirements = catalog.car_blueprint_requirements.get(car_id)
        if not requirements:
            return UpgradeResolution(False, "missing_blueprints", "No blueprint requirement record is available for this car.", car_id, 0, 0, source=catalog.source, source_url=catalog.source_url)
        if catalog.verification != VerificationStatus.VERIFIED_CURRENT:
            return UpgradeResolution(False, catalog.verification.value, "Blueprint requirements are sourced from unverified data and will not be presented as current.", car_id, 0, 0, values={"requirements": list(requirements)}, source=catalog.source, source_url=catalog.source_url)
        return UpgradeResolution(True, catalog.verification.value, "Blueprint requirements are explicitly verified as current.", car_id, 0, 0, values={"requirements": list(requirements)}, source=catalog.source, source_url=catalog.source_url)
