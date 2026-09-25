"""Central ALU data layer for Shohan's Companion.

The Discord/UI layer should depend on this module instead of embedding game data.
Records carry source/version/verification metadata so stale or unknown values can
never silently look like current verified ALU data.
"""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Protocol

class VerificationStatus(str, Enum):
    VERIFIED_CURRENT = "verified_current"
    OLDER_REFERENCE = "older_reference"
    UNKNOWN = "unknown"

@dataclass(frozen=True)
class SourceMetadata:
    source_id: str
    name: str
    url: str
    collected_at: str
    game_version: Optional[str] = None
    verification: VerificationStatus = VerificationStatus.UNKNOWN
    notes: str = ""
    # Practical source-use policy. This is provenance metadata, not a legal license grant.
    # "unknown" means redistribution rights have not been established.
    reuse_status: str = "unknown"

@dataclass
class DataRecord:
    id: str
    source: str
    source_url: str
    collected_at: str
    game_version: Optional[str] = None
    verification: VerificationStatus = VerificationStatus.UNKNOWN
    notes: str = ""
    def validate_provenance(self) -> None:
        if not self.id.strip(): raise ValueError("Data record id is required.")
        if not self.source.strip(): raise ValueError(f"{self.id}: source is required.")
        if not self.source_url.startswith(("http://","https://")):
            raise ValueError(f"{self.id}: source_url must be an HTTP(S) URL.")
        if not self.collected_at.strip(): raise ValueError(f"{self.id}: collected_at is required.")

@dataclass
class Car(DataRecord):
    name: str = ""
    manufacturer: Optional[str] = None
    class_name: Optional[str] = None
    star_levels: int = 0
    max_rank: Optional[int] = None
    stats: dict[str,float] = field(default_factory=dict)
    blueprints: dict[str,int] = field(default_factory=dict)

@dataclass
class UpgradeStage(DataRecord):
    car_id: str = ""
    star_level: int = 0
    stage: int = 0
    rank: Optional[int] = None
    costs: dict[str,int] = field(default_factory=dict)
    import_parts: dict[str,int] = field(default_factory=dict)

@dataclass
class EvoProfile(DataRecord):
    car_id: str = ""
    star_levels: int = 0
    class_name: Optional[str] = None
    blueprint_requirements: list[int] = field(default_factory=list)
    stock_stats: dict[str,Any] = field(default_factory=dict)
    archetypes: list[dict[str,Any]] = field(default_factory=list)
    parts: dict[str,list[dict[str,Any]]] = field(default_factory=dict)

@dataclass
class UpgradeCatalog(DataRecord):
    """Source-native upgrade tables kept intact until their semantics are verified."""
    source_schema: Optional[str] = None
    source_version: Optional[int] = None
    cost_tables: list[Any] = field(default_factory=list)
    exp_tables: list[Any] = field(default_factory=list)
    upg_tables: list[Any] = field(default_factory=list)
    bp_tables: list[Any] = field(default_factory=list)
    sum_tables: list[Any] = field(default_factory=list)
    cd_tables: list[Any] = field(default_factory=list)
    car_table_refs: dict[str,dict[str,int]] = field(default_factory=dict)
    car_blueprint_requirements: dict[str,list[int]] = field(default_factory=dict)

@dataclass
class Track(DataRecord):
    name: str = ""
    variant: Optional[str] = None
    direction: Optional[str] = None
    location: Optional[str] = None
    distance_km: Optional[float] = None

@dataclass
class Event(DataRecord):
    name: str = ""
    event_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    track_ids: list[str] = field(default_factory=list)
    car_ids: list[str] = field(default_factory=list)
    rewards: list[dict[str,Any]] = field(default_factory=list)

class ALUDataRepository(Protocol):
    def get_car(self, car_id: str) -> Optional[Car]: ...
    def find_cars(self, query: str = "") -> list[Car]: ...
    def get_upgrade_stage(self, car_id: str, star_level: int, stage: int) -> Optional[UpgradeStage]: ...
    def find_tracks(self, query: str = "") -> list[Track]: ...
    def find_events(self, query: str = "") -> list[Event]: ...
    def get_upgrade_catalog(self, catalog_id: str = "") -> Optional[UpgradeCatalog]: ...
    def get_evo_profile(self, car_id: str) -> Optional[EvoProfile]: ...

class InMemoryALUDataRepository:
    def __init__(self, *, cars: Iterable[Car]=(), upgrades: Iterable[UpgradeStage]=(),
                 tracks: Iterable[Track]=(), events: Iterable[Event]=(),
                 upgrade_catalogs: Iterable[UpgradeCatalog]=(),
                 evo_profiles: Iterable[EvoProfile]=()):
        self.cars={x.id:x for x in cars}
        self.upgrades={(x.car_id,x.star_level,x.stage):x for x in upgrades}
        self.tracks={x.id:x for x in tracks}
        self.events={x.id:x for x in events}
        self.upgrade_catalogs={x.id:x for x in upgrade_catalogs}
        self.evo_profiles={x.car_id:x for x in evo_profiles}
        self._validate()
    def _validate(self):
        for collection in (self.cars.values(),self.upgrades.values(),self.tracks.values(),self.events.values(),self.upgrade_catalogs.values(),self.evo_profiles.values()):
            for record in collection: record.validate_provenance()
    def get_car(self, car_id): return self.cars.get(car_id)
    def find_cars(self, query=""):
        q=query.strip().casefold()
        items=[x for x in self.cars.values() if not q or q in x.name.casefold() or q in x.id.casefold()]
        return sorted(items,key=lambda x:x.name.casefold())
    def get_upgrade_stage(self, car_id, star_level, stage):
        return self.upgrades.get((car_id,star_level,stage))
    def find_tracks(self, query=""):
        q=query.strip().casefold()
        items=[x for x in self.tracks.values() if not q or q in x.name.casefold() or q in x.id.casefold()]
        return sorted(items,key=lambda x:x.name.casefold())
    def find_events(self, query=""):
        q=query.strip().casefold()
        items=[x for x in self.events.values() if not q or q in x.name.casefold() or q in x.id.casefold()]
        return sorted(items,key=lambda x:x.name.casefold())
    def get_upgrade_catalog(self, catalog_id=""):
        if catalog_id:
            return self.upgrade_catalogs.get(catalog_id)
        return next(iter(self.upgrade_catalogs.values()), None)
    def get_evo_profile(self, car_id):
        return self.evo_profiles.get(car_id)

class ALUDataStore:
    def __init__(self, *, sources: Iterable[SourceMetadata]=(), repository: Optional[ALUDataRepository]=None):
        self.sources={x.source_id:x for x in sources}
        self.repository=repository or InMemoryALUDataRepository()
    def source(self, source_id): return self.sources.get(source_id)
    def source_status(self, source_id):
        source=self.source(source_id)
        return source.verification if source else VerificationStatus.UNKNOWN
    def data_status(self):
        repo=self.repository
        return {"sources":len(self.sources),"cars":len(getattr(repo,"cars",{})),
                "upgrade_stages":len(getattr(repo,"upgrades",{})),
                "upgrade_catalogs":len(getattr(repo,"upgrade_catalogs",{})),
                "evo_profiles":len(getattr(repo,"evo_profiles",{})),
                "tracks":len(getattr(repo,"tracks",{})),"events":len(getattr(repo,"events",{}))}
    def car(self, car_id): return self.repository.get_car(car_id)
    def search_cars(self, query=""): return self.repository.find_cars(query)
    def upgrade_stage(self, car_id, star_level, stage): return self.repository.get_upgrade_stage(car_id,star_level,stage)
    def upgrade_catalog(self, catalog_id=""): return self.repository.get_upgrade_catalog(catalog_id)
    def evo_profile(self, car_id): return self.repository.get_evo_profile(car_id)
    def search_tracks(self, query=""): return self.repository.find_tracks(query)
    def search_events(self, query=""): return self.repository.find_events(query)
    def can_present_as_current(self, record): return record.verification == VerificationStatus.VERIFIED_CURRENT
    def export_json(self):
        repo=self.repository
        return {"schema_version":1,"exported_at":datetime.now(timezone.utc).isoformat(),
                "sources":[asdict(s)|{"verification":s.verification.value} for s in self.sources.values()],
                "cars":[asdict(x)|{"verification":x.verification.value} for x in getattr(repo,"cars",{}).values()],
                "upgrade_stages":[asdict(x)|{"verification":x.verification.value} for x in getattr(repo,"upgrades",{}).values()],
                "upgrade_catalogs":[asdict(x)|{"verification":x.verification.value} for x in getattr(repo,"upgrade_catalogs",{}).values()],
                "evo_profiles":[asdict(x)|{"verification":x.verification.value} for x in getattr(repo,"evo_profiles",{}).values()],
                "tracks":[asdict(x)|{"verification":x.verification.value} for x in getattr(repo,"tracks",{}).values()],
                "events":[asdict(x)|{"verification":x.verification.value} for x in getattr(repo,"events",{}).values()]}
    @classmethod
    def from_json(cls,path):
        payload=json.loads(Path(path).read_text(encoding="utf-8"))
        sources=[SourceMetadata(**{**x,"verification":VerificationStatus(x.get("verification","unknown"))}) for x in payload.get("sources",[])]
        def common(item):
            x=dict(item); x["verification"]=VerificationStatus(x.get("verification","unknown")); return x
        repo=InMemoryALUDataRepository(
            cars=(Car(**common(x)) for x in payload.get("cars",[])),
            upgrades=(UpgradeStage(**common(x)) for x in payload.get("upgrade_stages",[])),
            upgrade_catalogs=(UpgradeCatalog(**common(x)) for x in payload.get("upgrade_catalogs",[])),
            evo_profiles=(EvoProfile(**common(x)) for x in payload.get("evo_profiles",[])),
            tracks=(Track(**common(x)) for x in payload.get("tracks",[])),
            events=(Event(**common(x)) for x in payload.get("events",[])))
        return cls(sources=sources,repository=repo)

DEFAULT_SOURCES=(
    SourceMetadata("a9garage","A9Garage","https://a9garage.pages.dev/","2026-09-24",verification=VerificationStatus.UNKNOWN,notes="ALU-oriented database reference."),
    SourceMetadata("alu_database","Asphalt Legends Unite Database","https://asphaltlegendsunite.info/","2026-09-24",verification=VerificationStatus.UNKNOWN,notes="Car, event, race, track, performance and blueprint reference."),
    SourceMetadata("asphalt9_info","Asphalt9.info upgrade database","https://asphalt9.info/asphalt9/tuning/upgrades/","2026-09-24",verification=VerificationStatus.OLDER_REFERENCE,notes="Reference only until ALU accuracy is verified."),
    SourceMetadata("gameloft_docs","Gameloft documentation","https://support.gameloft.com/","2026-09-24",verification=VerificationStatus.UNKNOWN,notes="Official documentation reference for upgrade-system concepts."),
)
DEFAULT_DATA_PATH=Path(__file__).resolve().parent/"data"/"alu_data.json"
def empty_store(): return ALUDataStore(sources=DEFAULT_SOURCES)
def load_default_store():
    return ALUDataStore.from_json(DEFAULT_DATA_PATH) if DEFAULT_DATA_PATH.exists() else empty_store()
