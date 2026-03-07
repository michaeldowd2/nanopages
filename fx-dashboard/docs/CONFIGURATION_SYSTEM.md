# Configuration System Documentation

## Overview

The FX Portfolio system uses a centralized configuration file that defines:
- Active currencies
- Available horizon estimator implementations + parameters
- Available signal generator implementations + parameters
- Available strategy implementations + parameters + **composition** (which estimators/generators to use)

**Key Principle:** Strategies can compose **multiple** estimators and **multiple** generators, then aggregate their outputs.

---

## Configuration File

**Location:** `/workspace/group/fx-portfolio/config/system_config.json`

**Structure:**
```json
{
  "currencies": ["EUR", "USD", ...],
  "horizon_estimators": { "available": {...}, "active": [...] },
  "signal_generators": { "available": {...}, "active": [...] },
  "strategies": { "available": {...}, "active": [...] },
  "pipeline_settings": {...}
}
```

---

## Composable Strategies

### Key Innovation

Strategies specify which estimators and generators to use via `estimator_combos` and `generator_combos` parameters:

```json
{
  "strategy": "simple-momentum",
  "params": {
    "confidence_threshold": 0.6,
    "trade_size_pct": 0.50,
    "aggregation_method": "weighted",
    "estimator_combos": [
      "llm-horizon-v1-default",
      "llm-horizon-v1-conservative"
    ],
    "generator_combos": [
      "keyword-sentiment-v1.1-standard",
      "keyword-sentiment-v1.1-aggressive"
    ]
  }
}
```

This creates an **ensemble** of `2 estimators × 2 generators = 4 combinations`, then aggregates them using the specified method (weighted average).

### Strategy Types

**1. Single Configuration (Baseline)**
```json
{
  "estimator_combos": ["llm-horizon-v1-default"],
  "generator_combos": ["keyword-sentiment-v1.1-standard"]
}
```
- 1 estimator × 1 generator = 1 signal set
- Simplest approach, fastest execution

**2. Ensemble (Multiple Analyzers)**
```json
{
  "estimator_combos": [
    "llm-horizon-v1-default",
    "llm-horizon-v1-conservative"
  ],
  "generator_combos": [
    "keyword-sentiment-v1.1-standard",
    "keyword-sentiment-v1.1-aggressive"
  ],
  "aggregation_method": "weighted"
}
```
- 2 estimators × 2 generators = 4 signal sets
- Averages across all 4 combinations
- More robust to individual analyzer failures
- Higher computational cost

**3. Grid Search (Parameter Sweeps)**
```json
{
  "confidence_threshold": [0.5, 0.6, 0.7],
  "trade_size_pct": [0.25, 0.50, 0.75],
  "estimator_combos": ["llm-horizon-v1-default"],
  "generator_combos": ["keyword-sentiment-v1.1-standard"]
}
```
- Single estimator/generator combo
- 3 × 3 = 9 strategy parameter combinations
- Used for parameter optimization

---

## Aggregation Methods

When strategies use multiple estimator/generator combinations, they aggregate signals using:

### 1. **Average** (Equal Weight)
```python
final_signal = sum(all_signals) / count(all_signals)
```
- Each combination contributes equally
- Simple, transparent
- Default method

### 2. **Weighted** (Confidence-Based)
```python
final_signal = sum(signal.confidence * signal.value) / sum(signal.confidence)
```
- Higher-confidence signals have more influence
- Adaptive to signal quality
- Recommended for ensembles

### 3. **Majority** (Voting)
```python
final_direction = most_common(signal.direction for signal in all_signals)
final_confidence = count(votes_for_winner) / total_votes
```
- Democratic voting across combinations
- Robust to outliers
- Good for directional signals

---

## Configuration Loader API

### Python API

```python
from scripts.config_loader import *

# Get active configurations
currencies = get_currencies()  # ['EUR', 'USD', ...]
estimators = get_active_estimators()  # {name: {estimator, params, description}}
generators = get_active_generators()
strategies = get_active_strategies()

# Get specific configuration
gen_config = get_generator_config('keyword-sentiment-v1.1-standard')
# Returns: {'generator': 'keyword-sentiment-v1.1', 'params': {...}, 'description': '...'}

# Modify active configurations
activate_generator('keyword-sentiment-v1.1-aggressive')
deactivate_generator('keyword-sentiment-v1.1-standard')

# Currency management
add_currency('BRL')
remove_currency('CNY')

# Save changes
save_config(modified_config)
```

### CLI Interface

```bash
# View all configurations
python scripts/config_loader.py list

# Activate/deactivate analyzers
python scripts/config_loader.py activate-generator keyword-sentiment-v1.1-aggressive
python scripts/config_loader.py deactivate-generator keyword-sentiment-v1.1-standard

# Currency management
python scripts/config_loader.py add-currency BRL
python scripts/config_loader.py remove-currency CNY
```

---

## Adding New Configurations

### 1. Add New Generator Configuration

Edit `/workspace/group/fx-portfolio/config/system_config.json`:

```json
{
  "signal_generators": {
    "available": {
      "llm-sentiment-v1-fast": {
        "generator": "llm-sentiment-v1",
        "params": {
          "model": "claude-haiku",
          "temperature": 0.3,
          "max_tokens": 100
        },
        "description": "Fast LLM-based sentiment analysis"
      }
    },
    "active": ["keyword-sentiment-v1.1-standard"]
  }
}
```

Then activate it:
```bash
python scripts/config_loader.py activate-generator llm-sentiment-v1-fast
```

### 2. Add New Strategy Configuration

```json
{
  "strategies": {
    "available": {
      "mean-reversion-ensemble": {
        "strategy": "mean-reversion",
        "params": {
          "lookback_days": 7,
          "z_score_threshold": 2.0,
          "estimator_combos": [
            "llm-horizon-v1-default",
            "llm-horizon-v1-conservative"
          ],
          "generator_combos": [
            "keyword-sentiment-v1.1-standard",
            "llm-sentiment-v1-fast"
          ],
          "aggregation_method": "weighted"
        },
        "description": "Mean-reversion with ensemble of 2×2 analyzers"
      }
    }
  }
}
```

This strategy will:
1. Use 2 horizon estimators × 2 signal generators = 4 analyzer combinations
2. Generate signals from each combination
3. Aggregate using weighted average
4. Apply mean-reversion logic to aggregated signals

---

## Dashboard Integration

The CONFIG tab on the dashboard displays:
- ✅ Active currencies
- ✅ All available estimator configurations (active highlighted)
- ✅ All available generator configurations (active highlighted)
- ✅ All available strategy configurations (active highlighted)
- ✅ Strategy composition (which estimators/generators each strategy uses)
- ✅ CLI commands for configuration management

Access via: https://michaeldowd2.github.io/nanopages/fx-dashboard/ → CONFIG tab

---

## Example Workflows

### Workflow 1: Compare Single vs Ensemble

**Step 1:** Activate single-config strategy
```bash
# Edit config to activate simple-momentum-default
python scripts/config_loader.py list  # verify
```

**Step 2:** Run pipeline
```bash
python scripts/strategy-simple-momentum.py
python scripts/track-performance.py
```

**Step 3:** Switch to ensemble strategy
```bash
# Edit config to activate simple-momentum-ensemble instead
```

**Step 4:** Run pipeline again
```bash
python scripts/strategy-simple-momentum.py
python scripts/track-performance.py
```

**Step 5:** Compare results in dashboard
- Check Step 8 performance metrics
- Compare accuracy, returns, drawdown

### Workflow 2: Add New Currency

```bash
# Add Brazilian Real
python scripts/config_loader.py add-currency BRL

# Update news aggregator to fetch BRL articles
# (would need to add BRL-specific RSS feeds)

# Run pipeline
python scripts/fetch-news.py
python scripts/generate-sentiment-signals.py
```

### Workflow 3: A/B Test Generators

```bash
# Activate both standard and aggressive
python scripts/config_loader.py activate-generator keyword-sentiment-v1.1-aggressive

# Create strategy using both
# Edit config: generator_combos: ["standard", "aggressive"]

# Run and compare which combo performs better
```

---

## Future Enhancements

### 1. Dynamic Configuration Loading

Currently: Config read at startup
Future: Hot-reload configuration without restarting pipeline

### 2. Web UI for Configuration

Currently: Edit JSON manually or use CLI
Future: Dashboard CONFIG tab allows activating/deactivating configurations via buttons

### 3. Configuration Versioning

Currently: Single config file
Future: Track configuration history, roll back to previous configs

### 4. Per-Currency Configurations

Currently: Global generator/estimator configs
Future: Different generators for different currencies (e.g., LLM for USD, keywords for emerging markets)

---

## Migration from Hardcoded to Config-Based

### Before (Hardcoded)

```python
# generate-sentiment-signals.py
CURRENCIES = ["EUR", "USD", "GBP", ...]  # Hardcoded
analyze_sentiment(text, currency)  # Uses DEFAULT_GENERATOR_PARAMS
```

### After (Config-Based)

```python
from scripts.config_loader import get_currencies, get_active_generators

currencies = get_currencies()  # From config
generators = get_active_generators()

for gen_name, gen_config in generators.items():
    params = gen_config['params']
    analyze_sentiment(text, currency, params)
```

---

## Configuration Schema

### Estimator Configuration
```json
{
  "estimator": "llm-horizon-estimator-v1",
  "params": {
    "model": "claude-haiku",
    "temperature": 0.3,
    // estimator-specific parameters
  },
  "description": "Human-readable description"
}
```

### Generator Configuration
```json
{
  "generator": "keyword-sentiment-v1.1",
  "params": {
    "keyword_set": "standard",
    "negation_enabled": true,
    "confidence_boost": 1.5,
    // generator-specific parameters
  },
  "description": "Human-readable description"
}
```

### Strategy Configuration
```json
{
  "strategy": "simple-momentum",
  "params": {
    "confidence_threshold": 0.6,
    "trade_size_pct": 0.50,
    "aggregation_method": "weighted",
    "estimator_combos": ["config-name-1", "config-name-2"],
    "generator_combos": ["config-name-1", "config-name-2"],
    // strategy-specific parameters
  },
  "description": "Human-readable description"
}
```

---

## Best Practices

1. **Naming Convention:** `{type}-{variant}-v{version}-{param-summary}`
   - Example: `keyword-sentiment-v1.1-aggressive`
   - Example: `llm-horizon-v1-conservative`

2. **Descriptions:** Clear, concise explanation of what makes this config unique

3. **Versioning:** Increment version when changing implementation, not just params

4. **Active Configs:** Keep active list small (1-3) for production, expand for testing

5. **Strategy Composition:** Start simple (single estimator/generator), add ensemble when validated

6. **Documentation:** Update `description` field when adding new configurations

---

## Related Files

- `/workspace/group/fx-portfolio/config/system_config.json` - Main configuration
- `/workspace/group/fx-portfolio/scripts/config_loader.py` - Configuration API
- `/workspace/group/sites/fx-dashboard/index.html` - Dashboard CONFIG tab
- `/workspace/group/fx-portfolio/docs/MODULAR_ARCHITECTURE.md` - Architecture overview
