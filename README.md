# Shohan's Companion

**Shohan's Companion** is a Discord bot and Asphalt Legends Unite companion toolkit.

It is a tools-only Asphalt Legends Unite companion. The primary /dashboard command opens the entire UI; /tools is a compatibility alias. No unrelated moderation, administration, or general-purpose Discord command surface is included.
- Car Upgrades Calculator
- Comparator
- Priority
- Season Calendar
- FAQ
- Hunt Game
- Simulation
- Race Maps
- Rating Predictor
- Cost Calculator
- Event Calculator
- Notes & Reminders
- Player Hub (garage snapshot, favorites, settings, and global search)
- Redeem Center with verified-data safeguards
- Native car picker with pagination, search, and automatic prefill for car-based tools

## ALU data layer

ALU game data is centralized in alu_data.py. Tools should query this layer rather than hard-code game values.

Each imported record carries:
- source and source URL
- collection date
- game/version context
- verification status (verified_current, older_reference, or unknown)

The repository now includes a 346-record reference-only vehicle catalog across Classes D/C/B/A/S. Player state is persisted separately in MongoDB so personal garage, favorites, settings, usage history, notes, and redeem-code records do not contaminate the central reference dataset. No numeric car, upgrade, blueprint, track, or event values are presented as current until they are imported and verified.

Reference sources currently registered:
- A9Garage
- Asphalt Legends Unite Database
- Asphalt9.info (older/reference upgrade data)
- Gameloft documentation

This structure keeps the data source replaceable: a future MongoDB or refreshed import can replace the repository without requiring a rewrite of the Discord UI/calculators.

## ALU importer / normalization pipeline

The repository now includes `alu_importer.py`, a source-agnostic import pipeline. Source adapters can pass normalized dictionaries into the importer without coupling the Discord tools to scraping code.

The importer:
- normalizes stable IDs for cars, upgrades, tracks, and events
- preserves source URL, collection time, game version, notes, and verification status
- rejects malformed records instead of guessing missing values
- merges duplicate records using verification status first and collection time second
- records conflicts instead of silently overwriting them
- exports the resulting store back to the replaceable JSON dataset

A structured A9Garage snapshot adapter is now available. It preserves the source-native upgrade tables (cost, XP, upgrade/import-part, blueprint, summary, and combined-cost tables) in an UpgradeCatalog, plus the per-car table references and blueprint requirement strings exposed by api_cars.json.

These third-party snapshot values remain unknown verification. The sync layer does not reinterpret an indexed table into a game meaning unless that mapping is established by source evidence. This prevents a calculator from silently using a guessed cost/part mapping as if it were verified current data.

Run the central sync with:
python alu_sync.py

The resulting store can then be replaced or refreshed from MongoDB or another repository implementation without changing the Discord/UI tools.


### Third-party source reuse policy

A9Garage is currently treated as a **reference-only** source. The public A9Garage backup repository does not declare an explicit software/data license, so this project does not persist or redistribute its raw snapshot datasets by default.

The A9Garage adapter may inspect the public snapshot for research, validation, and provenance-aware development, but `alu_sync.py` intentionally operates in non-persisting reference mode. Persistence is refused unless the source metadata explicitly identifies the source as `redistributable`.

This is a practical engineering safeguard, not a legal determination. Obtain permission or confirm applicable licensing before redistributing third-party datasets.


## Tooling status

The Discord dashboard now includes the complete planning/tool surface:

- Car Upgrades Calculator
- Upgrade Planner
- Cost Calculator
- Blueprint Planner
- Star-Up Planner
- Import Parts Planner
- Rank Calculator
- Garage Progress Tracker
- Car Comparator
- Car Comparison
- EVO / Build Comparison
- Priority Planner
- Season Calendar lookup
- Event Calculator
- Event Reward Planner
- Hunt Game
- Input-only Simulation
- Race Maps / Track lookup
- Rating Difference analysis
- FAQ
- Notes & Reminders
- Global ALU Search across centralized cars, tracks, and events
- Player Hub for garage snapshots, favorites, settings, and tool discovery
- Redeem Center that refuses to present unverified/guessed codes as active

Car selection is centralized in `alu_car_picker.py`: Discord's 25-option select limit is handled with pagination, a car-name search modal, and automatic prefill for Car / Car A / Car B inputs. All numerical calculations are isolated from the Discord UI in `alu_calculators.py` and `alu_planners.py`. Game values are only presented as current when centralized records are marked `verified_current`; otherwise the tools explain the data state instead of inventing values.

### Automated tests

The repository includes unit tests for the centralized data layer, importer, source adapters, upgrade resolver, calculator engine, and planner engine. The GitHub Actions test workflow runs Python compilation followed by `pytest -q` on supported pushes/pull requests/manual dispatches.


## Ultimate ALU Tool Scope

The project is strictly dedicated to Asphalt Legends Unite player tools: garage intelligence, resource and blueprint planning, upgrade analysis, event readiness, season/track search, progress tracking, comparisons, goals, and ALU data health/update analysis. It intentionally excludes unrelated general-purpose Discord bot features.


## Persistent player state

The dashboard now persists:
- personal garage snapshots
- favorite tools
- recently used tool statistics
- player settings
- private notes and reminder state
- a reserved redeem-code collection for future verified-code ingestion

MongoDB indexes are created at startup for these collections. Reference ALU data remains separate from personal player state.

## Redeem safety

The Redeem Center is search-only until verified code records are supplied. The bot does not scrape Reddit, guess codes, or present unverified strings as active redeem codes. A future verified ingestion source can populate the MongoDB redeem-code collection with code, source, verification, first-seen time, and expiry metadata.

## Command surface

The intended Discord command surface is deliberately small:
- /dashboard — primary player tools hub
- /tools — compatibility alias for the same dashboard

All other tools are reached through the dashboard UI.


## Reliability architecture

The companion is organized around a dashboard-first tool engine, centralized ALU reference data, and separate MongoDB player state. Calculators remain pure input/data functions so they can be regression-tested without Discord or production services.

Reliability safeguards include:
- deterministic/offline unit tests for calculator and data-layer behavior
- source adapters that can be tested with mocked responses rather than live network calls
- explicit verification states and provenance
- duplicate/conflict detection during imports
- reference-only handling for sources that are not explicitly redistributable
- persistent player state isolated from centralized ALU reference data
- a deliberately small public Discord command surface (/dashboard and /tools)
- deployment validation that compiles the project and runs the full test suite before attempting production deployment

The project does not treat a successful HTTP fetch as proof that ALU data is current. Current-game values require an appropriate verification state.
