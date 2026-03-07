# Modular Architecture: Parameterized Analyzers

## Core Principle

**All analysis layers must be modular and parameterizable**, with outputs including:
1. **Analyzer/Estimator/Strategy name** (which implementation was used)
2. **Parameters** (what settings were applied)

This enables:
- A/B testing different implementations
- Parameter optimization
- Performance comparison
- Reproducibility
- Debugging and validation

---

## Three Modular Layers

### Layer 1: Horizon Estimators (Step 4)

**Purpose:** Estimate time horizon for article predictions

**Current Status:** ✅ **Properly implemented**

**Output Schema:**
```json
{
  "estimator": "llm-horizon-estimator-v1",  // ✅ Analyzer name
  "estimator_params": {                      // ✅ Parameters (future)
    "model": "claude-haiku",
    "temperature": 0.3
  },
  "time_horizon": "1-3 days",
  "horizon_category": "short",
  "confidence": 0.8,
  "reasoning": "..."
}
```

**Example Implementations:**
- `llm-horizon-estimator-v1` (current) - Uses LLM via nanoclaw
- `keyword-horizon-estimator-v1` (future) - Keyword-based ("today", "this week", etc.)
- `hybrid-horizon-estimator-v1` (future) - Combines both

**Parameterization Examples:**
```python
# LLM estimator with different temperatures
llm_conservative = {"estimator": "llm-v1", "params": {"temperature": 0.1}}
llm_creative = {"estimator": "llm-v1", "params": {"temperature": 0.7}}

# Keyword estimator with different thresholds
keyword_strict = {"estimator": "keyword-v1", "params": {"min_confidence": 0.8}}
keyword_loose = {"estimator": "keyword-v1", "params": {"min_confidence": 0.5}}
```

---

### Layer 2: Signal Generators (Step 5)

**Purpose:** Generate bullish/bearish/neutral signals from articles

**Current Status:** ⚠️ **Needs implementation**

**Required Output Schema:**
```json
{
  "signal_id": "news-sentiment-USD-abc123",
  "signal_generator": "keyword-sentiment-v1.1",     // ❌ MISSING - needs to be added
  "generator_params": {                              // ❌ MISSING - needs to be added
    "keyword_set": "aggressive",
    "negation_enabled": true,
    "confidence_boost": 1.5
  },
  "signal_type": "news-sentiment",
  "currency": "USD",
  "predicted_direction": "bearish",
  "predicted_magnitude": "high",
  "confidence": 1.0,
  "reasoning": "...",
  "timestamp": "2026-02-22T15:00:00Z"
}
```

**Example Implementations:**
- `keyword-sentiment-v1.1` (current) - Keyword-based with negation detection
- `llm-sentiment-v1` (future) - Full LLM analysis
- `hybrid-sentiment-v1` (future) - Keyword + LLM for edge cases

**Parameterization Examples:**
```python
# Keyword-based with different sensitivities
keyword_aggressive = {
    "generator": "keyword-v1.1",
    "params": {
        "keyword_set": "aggressive",      # More keywords, higher sensitivity
        "negation_enabled": True,
        "confidence_boost": 1.5,
        "min_keyword_count": 1
    }
}

keyword_conservative = {
    "generator": "keyword-v1.1",
    "params": {
        "keyword_set": "conservative",    # Fewer, stronger keywords
        "negation_enabled": True,
        "confidence_boost": 1.2,
        "min_keyword_count": 2
    }
}

# LLM-based with different models
llm_fast = {
    "generator": "llm-v1",
    "params": {
        "model": "claude-haiku",
        "temperature": 0.3,
        "max_tokens": 100
    }
}

llm_accurate = {
    "generator": "llm-v1",
    "params": {
        "model": "claude-opus",
        "temperature": 0.1,
        "max_tokens": 200
    }
}
```

---

### Layer 3: Strategies (Step 7)

**Purpose:** Execute trades based on signals

**Current Status:** ✅ **Properly implemented**

**Output Schema:**
```json
{
  "date": "2026-02-22",
  "strategy_name": "simple-momentum",          // ✅ Strategy name
  "strategy_params": "conf=0.5_size=0.25",     // ✅ Parameters
  "executed_trades": 2,
  "EUR": 5000,
  "USD": 2500,
  // ... all currencies
  "current_value": 9875.50
}
```

**Example Implementations:**
- `simple-momentum` (current) - Pairs strongest vs weakest currencies
- `mean-reversion` (future) - Contrarian approach
- `breakout-trader` (future) - Trades on high-magnitude signals only

**Parameterization Examples:**
```python
# Simple momentum with different params
aggressive = {
    "strategy": "simple-momentum",
    "params": {
        "confidence_threshold": 0.5,    # Lower threshold, more trades
        "trade_size_pct": 0.75,         # Larger positions
        "aggregation_method": "weighted"
    }
}

conservative = {
    "strategy": "simple-momentum",
    "params": {
        "confidence_threshold": 0.7,    # Higher threshold, fewer trades
        "trade_size_pct": 0.25,         # Smaller positions
        "aggregation_method": "average"
    }
}
```

---

## Implementation Pattern

### Standard Interface

All analyzers follow this pattern:

```python
def analyze_<type>(input_data, params=None):
    """
    Generic analyzer interface

    Args:
        input_data: The data to analyze
        params: Dict of parameters (optional, uses defaults if None)

    Returns:
        tuple: (result, metadata)
            result: The analysis output
            metadata: {
                "analyzer_name": "keyword-sentiment-v1.1",
                "analyzer_params": {...},
                "analyzed_at": "2026-02-22T15:00:00Z"
            }
    """
    # Set defaults
    if params is None:
        params = get_default_params()

    # Run analysis with params
    result = run_analysis(input_data, params)

    # Build metadata
    metadata = {
        "analyzer_name": get_analyzer_name(),
        "analyzer_params": params,
        "analyzed_at": datetime.utcnow().isoformat() + 'Z'
    }

    return result, metadata
```

### Configuration File

Create `/workspace/group/fx-portfolio/config/analyzers.json`:

```json
{
  "horizon_estimators": {
    "active": "llm-v1-default",
    "configurations": {
      "llm-v1-default": {
        "estimator": "llm-horizon-estimator-v1",
        "params": {
          "model": "claude-haiku",
          "temperature": 0.3
        }
      },
      "llm-v1-conservative": {
        "estimator": "llm-horizon-estimator-v1",
        "params": {
          "model": "claude-haiku",
          "temperature": 0.1
        }
      }
    }
  },
  "signal_generators": {
    "active": "keyword-v1.1-default",
    "configurations": {
      "keyword-v1.1-default": {
        "generator": "keyword-sentiment-v1.1",
        "params": {
          "keyword_set": "standard",
          "negation_enabled": true,
          "confidence_boost": 1.5,
          "min_keyword_count": 1
        }
      },
      "keyword-v1.1-aggressive": {
        "generator": "keyword-sentiment-v1.1",
        "params": {
          "keyword_set": "aggressive",
          "negation_enabled": true,
          "confidence_boost": 1.8,
          "min_keyword_count": 1
        }
      },
      "keyword-v1.1-conservative": {
        "generator": "keyword-sentiment-v1.1",
        "params": {
          "keyword_set": "conservative",
          "negation_enabled": true,
          "confidence_boost": 1.2,
          "min_keyword_count": 2
        }
      }
    }
  },
  "strategies": {
    "active": "simple-momentum-combinations",
    "configurations": {
      "simple-momentum-combinations": {
        "strategy": "simple-momentum",
        "param_grid": {
          "confidence_threshold": [0.5, 0.6, 0.7],
          "trade_size_pct": [0.25, 0.50, 0.75],
          "aggregation_method": ["average"]
        }
      }
    }
  }
}
```

---

## Benefits

### 1. A/B Testing
Run multiple analyzers in parallel and compare:
```bash
# Generate signals with 3 different configurations
python step5_generate_signals.py --config keyword-v1.1-default
python step5_generate_signals.py --config keyword-v1.1-aggressive
python step5_generate_signals.py --config llm-v1-fast

# Compare results
python compare_analyzers.py --step 5 --configs keyword-v1.1-default,keyword-v1.1-aggressive,llm-v1-fast
```

### 2. Parameter Optimization
Find best parameters systematically:
```python
# Grid search for best keyword parameters
for conf_boost in [1.2, 1.5, 1.8]:
    for min_count in [1, 2, 3]:
        params = {"confidence_boost": conf_boost, "min_keyword_count": min_count}
        signals = generate_signals(params)
        performance = backtest(signals)
        # Track best params
```

### 3. Reproducibility
Exact recreation of any past analysis:
```python
# Load historical signal
signal = load_signal("signal-abc123")

# See exactly how it was generated
print(signal['signal_generator'])      # "keyword-sentiment-v1.1"
print(signal['generator_params'])      # {"keyword_set": "aggressive", ...}

# Reproduce with same params
result = run_analyzer(
    signal['signal_generator'],
    signal['generator_params'],
    original_article
)
```

### 4. Performance Attribution
Understand what drives results:
```sql
-- Which signal generator performs best?
SELECT
    signal_generator,
    AVG(realization_rate) as accuracy,
    COUNT(*) as signal_count
FROM signals
GROUP BY signal_generator
ORDER BY accuracy DESC;

-- Do aggressive params trade off accuracy for volume?
SELECT
    generator_params->>'keyword_set' as sensitivity,
    AVG(confidence) as avg_confidence,
    AVG(realization_rate) as accuracy
FROM signals
WHERE signal_generator = 'keyword-sentiment-v1.1'
GROUP BY sensitivity;
```

---

## Migration Plan

### Phase 1: Add Metadata to Signal Generator ✅ (This PR)

1. Update `generate-sentiment-signals.py`:
   - Add `signal_generator` field
   - Add `generator_params` field
   - Define default params

2. Update signal schema in documentation

3. Regenerate all signals with new schema

### Phase 2: Create Configuration System

1. Create `config/analyzers.json`
2. Add config loader utility
3. Update all scripts to load from config

### Phase 3: Add Horizon Estimator Params

1. Add `estimator_params` field to horizon analysis
2. Update LLM estimator to accept params
3. Create keyword-based estimator variant

### Phase 4: Implement Comparison Tools

1. Create `scripts/compare_analyzers.py`
2. Add visualization for multi-analyzer runs
3. Build parameter optimization framework

---

## CSV Export Schema

### Step 4: Horizons CSV
```csv
article_url,estimator,estimator_params,time_horizon,confidence,reasoning
https://...,llm-horizon-estimator-v1,"{""model"":""claude-haiku""}",1-3 days,0.8,Article mentions...
```

### Step 5: Signals CSV
```csv
signal_id,signal_generator,generator_params,currency,direction,magnitude,confidence,reasoning
news-sentiment-USD-abc,keyword-sentiment-v1.1,"{""keyword_set"":""standard""}",USD,bearish,high,1.0,USD shows net bearish...
```

### Step 7: Strategies CSV (already correct)
```csv
date,strategy_name,strategy_params,executed_trades,EUR,USD,...,current_value
2026-02-22,simple-momentum,conf=0.5_size=0.25,2,5000,2500,...,9875.50
```

---

## Documentation Updates Needed

1. ✅ `/workspace/group/fx-portfolio/docs/MODULAR_ARCHITECTURE.md` (this file)
2. Update `/workspace/group/fx-portfolio/docs/ARCHITECTURE.md` - Add parameterization section
3. Update `/workspace/group/fx-portfolio/docs/SENTIMENT_ANALYZERS.md` - Add params interface
4. Create `/workspace/group/fx-portfolio/config/analyzers.json` - Default configurations
5. Update all skill files (step4, step5, step7) - Show how to use different configs

---

## Example: Running Different Configurations

```bash
# Default configuration
python scripts/generate-sentiment-signals.py

# Aggressive keyword matching (more signals, potentially lower precision)
python scripts/generate-sentiment-signals.py --config aggressive

# Conservative keyword matching (fewer signals, higher precision)
python scripts/generate-sentiment-signals.py --config conservative

# Future: LLM-based (slower, more accurate)
python scripts/generate-sentiment-signals.py --config llm-fast
```

Each run stores its configuration in the output, enabling downstream analysis of which configuration performs best.
