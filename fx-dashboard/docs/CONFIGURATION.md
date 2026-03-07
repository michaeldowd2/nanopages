# Configuration System

Complete guide to the FX Portfolio configuration system.

---

## Overview

The FX Portfolio pipeline is **configuration-driven** - all components are defined in JSON config files, not hardcoded.

**Benefits:**
- Add currencies, generators, strategies without code changes
- Easy A/B testing of different configurations
- Clear separation of config vs implementation
- Version-controlled configuration

---

## Configuration Files

### 1. `config/system_config.json`

Defines all pipeline components:
- **currencies**: List of currencies to track
- **horizon_estimators**: Time horizon analyzers
- **signal_generators**: Sentiment signal generators
- **trade_combinators**: Trade recommendation logic
- **strategies**: Portfolio execution strategies

### 2. `config/pipeline_steps.json`

Defines pipeline step metadata:
- Step dependencies
- Scripts to run
- Safe-to-clear flags
- Warnings

---

## System Config Structure

```json
{
  "currencies": ["EUR", "USD", "GBP", "JPY", ...],
  "horizon_estimators": {
    "llm-horizon-v1-default": {
      "id": "llm-horizon-v1-default",
      "type": "llm",
      "description": "...",
      "params": { ... }
    }
  },
  "signal_generators": { ... },
  "trade_combinators": { ... },
  "strategies": { ... }
}
```

---

## Component Definitions

### Currencies

Simple array of currency codes:

```json
{
  "currencies": [
    "EUR", "USD", "GBP", "JPY", "CHF",
    "AUD", "CAD", "NOK", "SEK", "CNY", "MXN"
  ]
}
```

**Used by:**
- Step 1: Fetch exchange rates
- Step 2: Calculate indices
- Step 3: Fetch news
- All downstream steps

---

### Signal Generators

Define sentiment analysis methods:

```json
{
  "signal_generators": {
    "keyword-sentiment-v1.1-standard": {
      "id": "keyword-sentiment-v1.1-standard",
      "type": "keyword-based",
      "description": "Rule-based sentiment with currency events",
      "estimator_ids": ["llm-horizon-v1-default"],
      "params": {
        "magnitude_threshold_small": 3,
        "magnitude_threshold_medium": 6,
        "magnitude_threshold_large": 10,
        "direction_threshold": 2
      }
    },
    "llm-sentiment-v1-haiku": {
      "id": "llm-sentiment-v1-haiku",
      "type": "llm",
      "description": "LLM-based sentiment analysis",
      "estimator_ids": ["llm-horizon-v1-default"],
      "params": {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 300,
        "temperature": 0.3
      }
    }
  }
}
```

**Key fields:**
- `id`: Unique identifier
- `type`: Implementation type
- `estimator_ids`: Which horizon estimators to use
- `params`: Generator-specific parameters

---

### Trade Combinators

Define how to generate trades from signals:

```json
{
  "trade_combinators": {
    "combinator-standard": {
      "id": "combinator-standard",
      "type": "combinator",
      "description": "All bullish x bearish combinations",
      "estimator_ids": ["llm-horizon-v1-default"],
      "generator_ids": [
        "keyword-sentiment-v1.1-standard",
        "llm-sentiment-v1-haiku"
      ],
      "generator_weights": {
        "keyword-sentiment-v1.1-standard": 0.4,
        "llm-sentiment-v1-haiku": 0.6
      }
    }
  }
}
```

**Key fields:**
- `type`: "combinator" (all combinations) or "cascading" (pair strongest)
- `generator_ids`: Which generators to use
- `generator_weights`: How to weight each generator's signals

---

### Strategies

Define portfolio execution parameters:

```json
{
  "strategies": {
    "momentum-T2-size10": {
      "id": "momentum-T2-size10",
      "type": "simple-momentum",
      "description": "Top 2 trades, confidence >10%, conservative size",
      "params": {
        "trader_id": "combinator-standard",
        "confidence_threshold": 0.1,
        "target_trades": 2,
        "trade_size_pct": 0.1
      }
    }
  }
}
```

**Key fields:**
- `trader_id`: Which combinator to use
- `confidence_threshold`: Minimum signal to trade
- `target_trades`: Max number of trades (T parameter)
- `trade_size_pct`: Position size (% of portfolio)

---

## Adding Components

### Add a Currency

1. Edit `config/system_config.json`:
```json
{
  "currencies": ["EUR", "USD", ..., "NEW"]
}
```

2. Run pipeline - automatically processes new currency

### Add a Generator

1. Implement generator function in `generate-sentiment-signals-v2.py`

2. Add to config:
```json
{
  "signal_generators": {
    "my-new-generator": {
      "id": "my-new-generator",
      "type": "custom",
      "estimator_ids": ["llm-horizon-v1-default"],
      "params": { ... }
    }
  }
}
```

3. Update combinator to use new generator:
```json
{
  "generator_ids": [..., "my-new-generator"],
  "generator_weights": {
    "my-new-generator": 0.3,
    ...
  }
}
```

### Add a Strategy

Simply add to config:
```json
{
  "strategies": {
    "my-strategy": {
      "id": "my-strategy",
      "type": "simple-momentum",
      "params": {
        "trader_id": "combinator-standard",
        "confidence_threshold": 0.2,
        "target_trades": 5,
        "trade_size_pct": 0.15
      }
    }
  }
}
```

Run Step 9 - automatically executes new strategy!

---

## Configuration Best Practices

### 1. Use Descriptive IDs

```json
// ❌ Bad
"gen1": { ... }

// ✅ Good
"llm-sentiment-v1-haiku": { ... }
```

### 2. Document Parameters

```json
{
  "description": "LLM sentiment with Haiku model",
  "params": {
    "model": "claude-3-5-haiku-20241022",
    "max_tokens": 300,  // Limit response length
    "temperature": 0.3   // Low temp for consistency
  }
}
```

### 3. Version Your Configurations

```json
"keyword-sentiment-v1.1-standard"  // Version in ID
```

### 4. Test Incrementally

1. Add new component
2. Run single step to test
3. Verify output
4. Add to full pipeline

---

## Dashboard Integration

The dashboard reads `site_data/system_config.json` to:
- Display available generators
- Show strategy parameters
- Explain component relationships

Configuration changes automatically appear on dashboard after export!

---

## For More Details

- Architecture: See [ARCHITECTURE.md](ARCHITECTURE.md)
- Specific components:
  - Generators: See [SENTIMENT_ANALYZERS.md](SENTIMENT_ANALYZERS.md)
  - Horizons: See [LLM_TIME_HORIZON_ANALYSIS.md](LLM_TIME_HORIZON_ANALYSIS.md)
  - Indices: See [GEOMETRIC_MEAN_INDICES.md](GEOMETRIC_MEAN_INDICES.md)
