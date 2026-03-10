# FX Portfolio Pipeline Architecture

Complete system architecture documentation for the FX Portfolio Trading Pipeline.

---

## System Overview

The FX Portfolio Pipeline is a modular, data-driven system for generating forex trading signals and executing portfolio strategies.

**Pipeline Flow:**
```
Step 1: Fetch Exchange Rates
   ↓
Step 2: Calculate Currency Indices
   ↓
Step 3: Fetch News Articles
   ↓
Step 4: Analyze Time Horizons (LLM)
   ↓
Step 5: Generate Sentiment Signals
   ↓
Step 6: Check Signal Realization
   ↓
Step 7: Aggregate Signals
   ↓
Step 8: Calculate Trades
   ↓
Step 9: Execute Portfolio Strategies
```

---

## Architecture Principles

### 1. Modular Design

Each step is an independent script with:
- **Clear inputs**: Reads from specific `data/` folders
- **Clear outputs**: Writes to specific `data/` folders
- **No side effects**: Steps don't modify other steps' data
- **Testable**: Can run steps independently

### 2. Configuration-Driven

All components defined in `config/system_config.json`:
- Currencies to track
- Signal generators (with parameters)
- Horizon estimators
- Trade combinators
- Portfolio strategies

**Benefits:**
- No code changes needed to add currencies
- Easy to test different configurations
- Clear separation of config vs code

### 3. Data Separation

**System Data** (`data/` subdirectories):
- Raw working data from pipeline
- Logs, portfolios, news articles
- Not version controlled (too large)

**Site Data** (`site_data/`):
- Clean CSV exports for dashboard
- Transformed for visualization
- Version controlled with code

### 4. Fail-Safe Operation

- Scripts validate upstream data exists
- Graceful degradation (e.g., NewsAPI optional)
- Clear error messages
- Logging at each step

---

## Directory Structure

```
fx-portfolio/
├── config/
│   ├── system_config.json      # All component definitions
│   └── pipeline_steps.json     # Step dependencies
├── scripts/
│   ├── fetch-exchange-rates.py # Step 1
│   ├── calculate-currency-indices.py # Step 2
│   ├── fetch-news.py           # Step 3
│   ├── analyze-time-horizons-llm.py # Step 4
│   ├── generate-sentiment-signals-v2.py # Step 5
│   ├── check-signal-realization.py # Step 6
│   ├── aggregate-signals.py    # Step 7
│   ├── calculate-trades-step8.py # Step 8
│   ├── execute-strategies-step9.py # Step 9
│   ├── export-pipeline-data.py # Export to site_data
│   ├── env_loader.py           # Environment variables
│   ├── config_loader.py        # Config helpers
│   └── pipeline_logger.py      # Logging system
├── data/
│   ├── prices/                 # Exchange rates
│   ├── indices/                # Currency indices
│   ├── news/                   # News articles
│   ├── article-analysis/       # Horizon analysis
│   ├── signals/                # Sentiment signals
│   ├── signal-realization/     # Realization checks
│   ├── aggregated-signals/     # Aggregated signals
│   ├── trades/                 # Trade recommendations
│   ├── portfolios/             # Portfolio state
│   └── logs/                   # Pipeline logs
├── site_data/                  # Dashboard exports
├── skills/                     # Automation skills
├── docs/                       # Documentation
└── index.html                  # Dashboard
```

---

## Data Flow

### System Pipeline

```
Exchange Rates → data/prices/{date}.json
    ↓
Currency Indices → data/indices/{currency}_index.json
    ↓
News Articles → data/news/{currency}/{date}_{source}.json
    ↓
Horizon Analysis → data/article-analysis/{date}.json
    ↓
Sentiment Signals → data/signals/{currency}/{date}.json
    ↓
Signal Realization → data/signal-realization/{date}.json
    ↓
Aggregated Signals → data/aggregated-signals/aggregated_signals.csv
    ↓
Trade Recommendations → data/trades/trades.csv
    ↓
Portfolio Execution → data/portfolios/strategies.csv
```

### Export to Dashboard

```
Export Script reads: data/* subdirectories
Export Script writes: site_data/step*.csv
Dashboard reads: site_data/*.csv
```

---

## Key Components

### 1. Signal Generators

Defined in `config/system_config.json`:
- `keyword-sentiment-v1.1-standard`: Rule-based sentiment
- `llm-sentiment-v1-haiku`: LLM-based sentiment (Anthropic Claude)

Each generator produces:
- Direction: bullish/bearish/neutral
- Magnitude: small/medium/large
- Confidence: 0.0-1.0
- Signal: confidence × magnitude_weight

### 2. Horizon Estimators

Analyze time horizon of each news article:
- `llm-horizon-v1-default`: LLM-based horizon analysis

Produces:
- Horizon days: 1, 7, 30, 90
- Reasoning

### 3. Trade Combinators

Generate trade pairs from signals:
- `combinator-standard`: All bullish×bearish combinations
- Weights generators by historical performance

### 4. Portfolio Strategies

Execute trades with different parameters:
- Target trades (T): Number of trades to execute
- Position size: % of portfolio per trade
- Confidence threshold: Minimum signal to trade

---

## Configuration System

See [CONFIGURATION.md](CONFIGURATION.md) for details.

---

## Extension Points

### Adding a Currency

1. Add to `config/system_config.json` currencies array
2. Run pipeline - automatically fetches data

### Adding a Signal Generator

1. Create generator function in `generate-sentiment-signals-v2.py`
2. Add to `config/system_config.json`
3. Run Step 5

### Adding a Strategy

1. Add to `config/system_config.json` strategies
2. Run Step 9

No code changes needed - configuration-driven!

---

## Performance Considerations

- **Caching**: News articles cached by date
- **Incremental**: Steps append to existing data
- **Date filtering**: Most scripts support `--date` flag
- **Parallel potential**: Steps can run in parallel for different dates

---

## Historic Data and Backfilling

### ⚠️ CRITICAL: Data-Fetching Processes

**Processes 1 and 3 fetch LIVE data** from external sources and should NEVER be run with historic dates:

| Process | Name | Data Source | Safe for Historic Dates? |
|---------|------|-------------|-------------------------|
| **1** | Exchange Rates | GitHub Currency API | ❌ **NO** - Fetches current rates |
| **3** | News Aggregation | RSS/NewsAPI | ❌ **NO** - Fetches current news |

**Why?** Running these with `--date 2026-02-24` will:
- Fetch today's data from the API
- Save it with filename `2026-02-24.csv`
- **Corrupt the historic record** ⚠️

**Guardrails:** The `run-system.py` script will block attempts to run P1 or P3 with historic dates.

### ✅ Safe Processes for Historic Reruns

The following processes **read from existing data** and are safe to rerun for historic dates:

| Process | Name | Safe? | Reason |
|---------|------|-------|--------|
| **2** | Currency Indices | ✅ YES | Reads from P1 CSV files |
| **4** | Time Horizon Analysis | ✅ YES | Reads from P3 CSV files |
| **5** | Sentiment Signals | ✅ YES | Reads from P3 CSV files |
| **6** | Signal Realization | ✅ YES | Reads from P2, P4, P5 CSV files |
| **7** | Signal Aggregation | ✅ YES | Reads from P6 CSV files |
| **8** | Trade Calculation | ✅ YES | Reads from P7 CSV files |
| **9** | Portfolio Execution | ✅ YES | Reads from P1, P8 CSV files |

### Backfilling Missing Data

To backfill historic data for processes 2-9:

```bash
# Example: Backfill all processes for a specific date
python3 scripts/utilities/run-system.py --date 2026-02-25 --process-ids 2 4 5 6 7 8 9

# Example: Backfill just Process 2 for multiple dates
for date in 2026-02-25 2026-02-26 2026-02-27; do
    python3 scripts/utilities/run-system.py --date $date --process-ids 2
done
```

**Requirements:**
- P1 (Exchange Rates) CSV must exist for the target date
- P3 (News) CSV must exist for the target date (if running P4+)

### Obtaining Historic Exchange Rates

If you need historic exchange rate data that was never fetched:

1. **Manual Archive Sources:**
   - European Central Bank: https://www.ecb.europa.eu/stats/eurofxref/
   - Bank of England: https://www.bankofengland.co.uk/boeapps/database/
   - FRED (Federal Reserve): https://fred.stlouisfed.org/

2. **Format Requirements:**
   - Create CSV with columns: `date, base_currency, quote_currency, rate`
   - Save as `data/prices/YYYY-MM-DD.csv`
   - Ensure all 121 currency pairs (11×11) are included

3. **Validation:**
   - Run: `python3 scripts/utilities/csv_helper.py --validate data/prices/YYYY-MM-DD.csv`

---

## For More Details

- Configuration: See [CONFIGURATION.md](CONFIGURATION.md)
- Logging: See [LOGGING_SYSTEM.md](LOGGING_SYSTEM.md)
- Deployment: See [DEPLOYMENT.md](DEPLOYMENT.md)
- Environment: See [ENVIRONMENT_VARIABLES_GUIDE.md](ENVIRONMENT_VARIABLES_GUIDE.md)
