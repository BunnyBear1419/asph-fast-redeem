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

No live source data is populated yet. This is intentional: numeric ALU values should only enter the production dataset after the source adapter has collected them and the values have been verified for the current game/version.
