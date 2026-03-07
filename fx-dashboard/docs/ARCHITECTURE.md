# FX Portfolio System Architecture

## Overview

This system generates trading signals for 11 currencies (EUR, USD, GBP, JPY, CHF, AUD, CAD, NOK, SEK, CNY, MXN) by analyzing news sentiment and technical indicators. The architecture is designed with parallel processing capabilities - multiple implementations of each layer can run simultaneously and be aggregated.

## Core Principles

1. **Separation of Concerns**: Each layer does one job well
2. **Parallelizable**: Multiple implementations can run in parallel
3. **Composable**: Strategies can mix/match different analyzers
4. **Testable**: Each layer can be tested independently
5. **Observable**: All data visible in dashboard for debugging
6. **Parameterizable**: All analyzers/estimators/strategies include name + params in output

## Modular Architecture Pattern

**Key requirement**: All analysis layers (Horizon Estimators, Signal Generators, Strategies) must output:
- **Analyzer/estimator/strategy name**: Which implementation was used
- **Parameters**: What configuration/settings were applied

This enables:
- A/B testing different implementations
- Parameter optimization
- Performance attribution
- Full reproducibility

See `/docs/MODULAR_ARCHITECTURE.md` for detailed specification.

## End-to-End Process (9 Steps)

### Step 1: Download EUR Pairs
**Script**: `fetch-prices.py` (existing)
**Input**: External FX data sources
**Output**: `/data/prices/fx-rates-{date}.json`

Downloads daily EUR-based exchange rates for all currencies.

```json
{
  "timestamp": "2026-02-21T10:00:00Z",
  "base": "EUR",
  "rates": {
    "USD": 1.18,
    "GBP": 0.874,
    "JPY": 182.44,
    ...
  }
}
```

### Step 2: Generate Synthetic Indices
**Script**: `calculate-currency-indices.py`
**Input**: EUR pair prices (from Step 1)
**Output**: `/data/indices/{CURRENCY}_index.json`

Calculates currency strength indices normalized to EUR.
- Formula: `index = (base_rate / current_rate) × 100`
- Higher index = stronger currency
- Used by realization checker to measure actual movements

```json
{
  "currency": "USD",
  "base_currency": "EUR",
  "calculation_method": "synthetic_eur_normalized",
  "data": [
    {
      "date": "2026-02-21",
      "index": 100.0,
      "eur_rate": 1.18,
      "pct_change": 0.0
    }
  ]
}
```

**Current Limitation**: Uses synthetic indices from EUR pairs. Future improvement: Use real currency indices (DXY, EUR TWI, etc.)

### Step 3: News Aggregator
**Script**: `fetch-news.py`
**Input**: RSS feeds, web sources
**Output**: `/data/news/{CURRENCY}/{date}.json` + `/data/news/url_index.json`

Fetches and filters news articles:
- Extracts publication timestamps
- Filters articles >30 days old
- Deduplicates by URL globally
- Calculates relevance scores per currency

```json
{
  "currency": "USD",
  "date": "2026-02-21",
  "articles": [
    {
      "title": "Fed signals hawkish shift",
      "url": "https://...",
      "snippet": "...",
      "published_at": "2026-02-21T09:00:00Z",
      "relevance_score": 0.85
    }
  ]
}
```

### Step 4: Time Horizon Estimators
**Script**: Orchestrator-based (see `skills/analyze-article-horizons.md`)
**Input**: Raw articles (from Step 3)
**Output**: `/data/article-analysis/{url_hash}.json`

**PURPOSE**: Extract ONLY the time horizon from articles (no direction prediction)

Multiple implementations can run in parallel:
- `llm-horizon-estimator` (current): Uses LLM to extract time horizon
- `keyword-horizon-estimator` (future): Uses keywords ("next week", "coming months")
- `source-based-estimator` (future): Infers horizon from source type (news = short, analysis = long)

```json
{
  "url": "https://...",
  "analyzed_at": "2026-02-21T11:00:00Z",
  "estimator": "llm-horizon-estimator-v1",
  "time_horizon": "1w",
  "horizon_category": "medium",
  "confidence": 0.75,
  "reasoning": "Article discusses Fed meeting next week"
}
```

**Current Implementation**: Orchestrator (nanoclaw) performs LLM analysis
**Future Enhancement**: Anthropic API integration for standalone execution

### Step 5: Sentiment Analyzers (Signal Generators)
**Script**: `generate-sentiment-signals.py` (being refactored)
**Input**: Analyzed articles (from Step 4) + raw articles (from Step 3)
**Output**: `/data/signals/{CURRENCY}/{date}.json`

**PURPOSE**: Generate signals with predicted currency movements

Multiple implementations can run in parallel:
- `news-sentiment` (current): Keyword-based sentiment analysis
- `llm-sentiment` (future): LLM-based nuanced analysis
- `central-bank-parser` (future): Parse official statements
- `event-detector` (future): Identify geopolitical events

Each signal includes:
- **Predicted direction**: bullish/bearish/neutral
- **Predicted magnitude**: e.g., "0.5%" or "unclear"
- **Confidence**: 0-1 score
- **Time horizon reference**: Links to horizon estimator output

```json
{
  "currency": "USD",
  "date": "2026-02-21",
  "signals": [
    {
      "signal_id": "news-sentiment-abc123",
      "signal_type": "news-sentiment",
      "currency": "USD",
      "predicted_direction": "bullish",
      "predicted_magnitude": "0.8%",
      "confidence": 0.75,
      "horizon_estimator": "llm-horizon-estimator-v1",
      "time_horizon": "1w",
      "article_url": "https://...",
      "published_at": "2026-02-21T09:00:00Z",
      "reasoning": "Fed hawkish shift supports USD strength",
      "timestamp": "2026-02-21T11:30:00Z"
    }
  ]
}
```

**Note**: Signal does NOT include `realized` flag yet - that's added by Step 6.

### Step 6: Realization Checker
**Script**: `check-signal-realization.py` (to be built)
**Input**: Signals (from Step 5) + Indices (from Step 2)
**Output**: Updates signals with `realized: true/false`

**PURPOSE**: Determine if predicted movements have already occurred

For each signal:
1. Calculate time elapsed since article publication
2. Load currency index movement over that period
3. Compare predicted direction/magnitude vs actual movement
4. Tag signal with realization status

**Realization Logic (Moderate Complexity):**
- **Direction match**: Did currency move in predicted direction?
- **Magnitude threshold**: Did movement exceed 50% of predicted magnitude?
- **Realized**: Direction matches AND magnitude threshold met
- **Unrealized**: Prediction not yet materialized
- **Too Early**: Prediction horizon not reached yet
- **Contradicted**: Opposite direction occurred

```json
{
  "signal_id": "news-sentiment-abc123",
  "realized": false,
  "realization_status": "unrealized",
  "actual_movement": {
    "direction": "bullish",
    "magnitude": "+0.3%",
    "days_elapsed": 2
  },
  "realization_check_timestamp": "2026-02-23T10:00:00Z"
}
```

### Step 7: Strategies (Future)
**Scripts**: Multiple strategy implementations
**Input**: Signals with realization status (from Step 6)
**Output**: Trade recommendations

**PURPOSE**: Generate trading decisions from signals

Each strategy:
- Filters signals (`realized: false` only)
- Applies **strategy-specific time-decay weighting**
- Combines signals across currencies to suggest pair trades
- Accounts for Revolut spreads (~0.74%)

Example strategies:
- `momentum-strategy`: Follows strongest signals
- `contrarian-strategy`: Fades extreme sentiment
- `multi-timeframe`: Combines short/medium/long signals
- `risk-weighted`: Adjusts for volatility and confidence

**Time-Decay Weighting (Strategy-Specific)**:
Each strategy applies its own decay function to older articles:
- Short-term strategy: Exponential decay (50% weight after 1 day)
- Medium-term strategy: Linear decay over horizon period
- Long-term strategy: Slow decay (50% weight after 2 weeks)

### Step 8: Performance Analysis (Future)
**Scripts**: To be built
**Input**: Trade history + actual results
**Output**: Strategy performance metrics

Track:
- Win rate per strategy
- Average return per trade
- Sharpe ratio
- Signal accuracy (predicted vs actual movements)
- Best/worst performing signal generators

### Step 9: Update Dashboard
**Script**: Manual or automated dashboard rebuild
**Input**: All data from Steps 1-8
**Output**: Static website at `https://michaeldowd2.github.io/nanopages/fx-dashboard/`

Displays:
- Architecture diagram
- Latest FX rates and indices
- News articles with time horizons
- Signals with realization status
- Strategy recommendations (future)
- Performance metrics (future)

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Daily 09:00 GMT)                   │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
┌───────────────┐        ┌──────────────────┐       ┌─────────────────┐
│  STEP 1 & 2   │        │   STEP 3 & 4     │       │    STEP 5 & 6   │
│  Price Data   │───────▶│   News + Time    │──────▶│  Signals +      │
│  + Indices    │        │   Horizons       │       │  Realization    │
└───────────────┘        └──────────────────┘       └────────┬────────┘
                                                              │
                                                              ▼
                                                   ┌────────────────────┐
                                                   │     STEP 7         │
                                                   │   Strategies       │
                                                   │  (Filter realized, │
                                                   │   Apply weighting) │
                                                   └────────┬───────────┘
                                                            │
                                                            ▼
                                                   ┌────────────────────┐
                                                   │     STEP 8 & 9     │
                                                   │   Performance +    │
                                                   │    Dashboard       │
                                                   └────────────────────┘
```

## Parallel Processing Capabilities

### Time Horizon Estimators (Step 4)
Multiple estimators can run in parallel:
```
Article → ├─ LLM Estimator → horizon: "1w"
          ├─ Keyword Estimator → horizon: "3d"
          └─ Source-Based → horizon: "1d"
```

Each output is tagged with `estimator` name. Strategies can choose which estimator(s) to trust.

### Sentiment Analyzers (Step 5)
Multiple analyzers create different signals:
```
Article → ├─ News-Sentiment → bullish, 0.75 confidence
          ├─ LLM-Sentiment → bullish, 0.85 confidence
          └─ Event-Detector → neutral, 0.50 confidence
```

Each signal is independent. Strategies can aggregate or cherry-pick.

### Strategies (Step 7)
Multiple strategies consume signals differently:
```
Signals → ├─ Momentum Strategy → Trade: Buy GBP/EUR
          ├─ Contrarian Strategy → Trade: Sell GBP/EUR
          └─ Multi-Timeframe → Trade: Hold
```

Each strategy tracked separately in performance analysis.

## Design Decisions

### Why Separate Horizon Estimation from Sentiment?
- **Reusability**: Same horizon used by multiple sentiment analyzers
- **Testable**: Can validate horizon accuracy independently
- **Composable**: Strategies can mix/match horizon + sentiment sources

### Why Tag Signals (Not Articles) with Realization?
- Different signal generators may predict different movements from same article
- Each signal's prediction needs independent realization check
- Allows comparing accuracy across signal generators

### Why Strategy-Specific Time Weighting?
- Different strategies have different time preferences
- Day-traders weight recent articles heavily
- Position-traders tolerate older macro views
- Flexibility for strategy optimization

### Why Synthetic Indices (Not Real Ones)?
- **Current**: Easy to calculate from EUR pairs (already downloaded)
- **Future**: Real indices (DXY, EUR TWI) more accurate for realization checking
- Documented as known limitation with upgrade path

## File Structure

```
/workspace/group/fx-portfolio/
├── data/
│   ├── prices/                     # Step 1 output
│   │   └── fx-rates-{date}.json
│   ├── indices/                    # Step 2 output
│   │   └── {CURRENCY}_index.json
│   ├── news/                       # Step 3 output
│   │   ├── {CURRENCY}/{date}.json
│   │   └── url_index.json
│   ├── article-analysis/           # Step 4 output
│   │   └── {url_hash}.json
│   ├── signals/                    # Step 5 & 6 output
│   │   └── {CURRENCY}/{date}.json
│   ├── trades/                     # Step 7 output (future)
│   └── performance/                # Step 8 output (future)
│
├── scripts/
│   ├── fetch-prices.py             # Step 1
│   ├── calculate-currency-indices.py  # Step 2
│   ├── fetch-news.py               # Step 3
│   ├── analyze-time-horizons.py    # Step 4 coordinator
│   ├── generate-sentiment-signals.py  # Step 5
│   ├── check-signal-realization.py # Step 6 (to build)
│   └── (future strategy scripts)   # Step 7
│
├── skills/
│   ├── aggregate-news.md
│   ├── analyze-article-horizons.md # Step 4 orchestrator instructions
│   ├── generate-sentiment-signals.md
│   └── (future skill docs)
│
└── docs/
    └── ARCHITECTURE.md (this file)
```

## Current Status

**Completed:**
- ✅ Step 1: Price download
- ✅ Step 2: Synthetic indices
- ✅ Step 3: News aggregation with timestamps
- ✅ Step 4: Time horizon analysis (orchestrator-based)
- 🟡 Step 5: Sentiment signals (needs refactor for new schema)

**In Progress:**
- 🔄 Step 5: Update signal generator for new architecture
- 🔄 Step 6: Build realization checker

**Not Started:**
- ⏳ Step 7: Strategies
- ⏳ Step 8: Performance analysis
- 🔄 Step 9: Dashboard (partially built)

## Future Improvements

1. **API Integration**: Replace orchestrator with Anthropic API calls (~$2/year)
2. **Real Indices**: Use DXY, EUR TWI instead of synthetic indices
3. **More Signal Generators**: LLM-based, event detection, technical analysis
4. **Advanced Realization Logic**: Statistical significance, volatility adjustment
5. **Backtesting**: Test strategies on historical data
6. **Automated Execution**: Revolut API integration (currently manual trades only)
