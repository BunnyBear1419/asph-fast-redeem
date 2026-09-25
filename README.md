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
