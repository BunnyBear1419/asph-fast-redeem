# Shohan's Companion

**Shohan's Companion** is a Discord bot and Asphalt Legends Unite companion toolkit.

It includes the Fast Redeem system plus the Asphalt Legends Unite Tools Hub for:
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

## ALU data layer

ALU game data is centralized in alu_data.py. Tools should query this layer rather than hard-code game values.

Each imported record carries:
- source and source URL
- collection date
- game/version context
- verification status (verified_current, older_reference, or unknown)

The repository currently contains source metadata and an intentionally empty data store. No numeric car, upgrade, blueprint, track, or event values are presented as current until they are imported and verified.

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

All numerical calculations are isolated from the Discord UI in `alu_calculators.py` and `alu_planners.py`. Game values are only presented as current when centralized records are marked `verified_current`; otherwise the tools explain the data state instead of inventing values.

### Automated tests

The repository includes unit tests for the centralized data layer, importer, source adapters, upgrade resolver, calculator engine, and planner engine. The GitHub Actions test workflow runs Python compilation followed by `pytest -q` on supported pushes/pull requests/manual dispatches.
