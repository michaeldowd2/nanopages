# FX Portfolio Trading System

An 11-step pipeline for analyzing currency movements, generating trading signals, and executing strategies.

## Quick Links

- **📊 Live Dashboard:** https://michaeldowd2.github.io/nanopages/fx-dashboard/
- **📖 Documentation:** [`docs/`](docs/)
- **🚀 Deployment:** ALWAYS use `./scripts/deploy-dashboard.sh` (see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md))
- **🧪 Testing:** See data clearing commands below for testing empty states

**⚠️ IMPORTANT**: Dashboard site name is `fx-dashboard` (NOT `fx-portfolio`). Project folder is `fx-portfolio` but dashboard site is `fx-dashboard`.

## Project Structure

```
fx-portfolio/
├── scripts/          # Pipeline scripts (steps 1-7)
├── data/             # Pipeline data (prices, signals, exports)
├── docs/             # Documentation
├── skills/           # Automation skills
└── config/           # Configuration files
```

## Pipeline Steps

1. **Fetch FX Rates** - Download exchange rates from GitHub Currency API (free, no API key required)
2. **Calculate Indices** - Compute synthetic currency strength indices
3. **Download News** - Fetch currency-related news articles
4. **Analyze Horizons** - Estimate time horizons for each article
5. **Generate Signals** - Create bullish/bearish sentiment signals
6. **Check Realization** - Validate signals against actual movements
7. **Aggregate Signals** - Combine signals by currency and direction
8. **Calculate Trades** - Determine optimal trades from aggregated signals
9. **Execute Trades** - Calculate exact trade amounts with spreads
10. **Account Balances** - Update portfolio balances from executed trades
11. **Portfolio Performance** - Calculate multi-currency valuations and performance metrics

## Quick Start

### Run Full Pipeline
```bash
cd /workspace/group/fx-portfolio
./run-pipeline.sh
```

### Deploy Dashboard
```bash
# Using Python script (recommended - full pipeline with logging)
python3 scripts/deploy-dashboard.py

# Or using bash script (legacy)
./scripts/deploy-dashboard.sh
```

The deployment script automatically:
1. Clears old dashboard data
2. Re-exports all pipeline data from source
3. Copies fresh exports to dashboard folder
4. Deploys to GitHub Pages

### Clear Data (Three Modes)
```bash
# Option 1: Clear only exports and dashboard data (keeps source data)
./scripts/clear-all-data.sh --exports-only

# Option 2: Clear exports + today's source data (keeps historical data)
./scripts/clear-all-data.sh --latest

# Option 3: Complete reset - clear ALL data (fresh start)
./scripts/clear-all-data.sh --all
```

All modes preserve configuration files, scripts, and `system_config.json`.

## Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and pipeline flow |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | How to deploy the dashboard |
| [CONFIGURATION.md](docs/CONFIGURATION.md) | Strategy and system configuration |
| [LOGGING_SYSTEM.md](docs/LOGGING_SYSTEM.md) | Pipeline logging |
| [PROCESS_REFACTORING.md](docs/PROCESS_REFACTORING.md) | Recent pipeline changes (processes 9-11) |

## Skills

Skills are reusable automation commands located in `/workspace/group/skills/`:

- **`publish-github-pages fx-dashboard`** - Deploy dashboard to GitHub Pages
- **`publish-static fx-dashboard`** - Deprecated (Surge)

For skill details, see [`/workspace/group/skills/publish-github-pages.md`](/workspace/group/skills/publish-github-pages.md)

## Configuration

Strategies are defined in `config/strategies.json`:

```json
{
  "strategy-id": {
    "name": "Strategy Name",
    "params": {
      "confidence_threshold": 0.5,
      "trade_size_pct": 0.25,
      "generator_ids": ["keyword-sentiment-v1.1-standard"],
      "estimator_ids": ["llm-horizon-estimator-v1-default"]
    }
  }
}
```

See [CONFIGURATION.md](docs/CONFIGURATION.md) for details.

## Dashboard

The live dashboard visualizes all pipeline steps:

- **URL:** https://michaeldowd2.github.io/nanopages/fx-dashboard/
- **Source:** `/workspace/group/sites/fx-dashboard/`
- **Deploy:** `publish-github-pages fx-dashboard`

## Development

### Adding a New Strategy

1. Edit `config/strategies.json`
2. Add strategy with unique ID
3. Run step 7: `python3 scripts/strategy-simple-momentum.py`

### Adding a New Signal Generator

1. Increment generator ID version (e.g., `v1.1` → `v1.2`)
2. Update `SIGNAL_GENERATOR_ID` in `scripts/generate-sentiment-signals.py`
3. Document params in `DEFAULT_GENERATOR_PARAMS`

### Adding a New Horizon Estimator

1. Create new estimator ID (e.g., `llm-horizon-v2-default`)
2. Update horizon analysis logic
3. Update `estimator_id`, `estimator_type`, `estimator_params` in output

## Support

For questions or issues, refer to the documentation in `docs/` or review conversation logs in `/workspace/group/conversations/`.
