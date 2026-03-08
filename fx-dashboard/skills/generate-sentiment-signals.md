# Skill: generate-sentiment-signals

Generate sentiment signals using multiple analyzers (keyword-based and LLM-based).

---

## Purpose

Analyze news articles to create signals with directional predictions. Supports multiple signal generators running in parallel for comparison and A/B testing.

**Implementation Date**: LLM generator added 2026-02-25

---

## Quick Start

### Run All Configured Generators

```bash
cd /workspace/group/fx-portfolio
python3 scripts/generate-sentiment-signals-v2.py
```

### Run Legacy Single Generator (Keyword Only)

```bash
python3 scripts/generate-sentiment-signals.py
```

**Output**: `/data/signals/{CURRENCY}/{date}.json`

---

## Modular Generator System

### Architecture

1. **Generator Configuration in system_config.json**
   - All generators defined in config file
   - Easy to add/remove generators
   - Parameters configurable per generator

2. **Modular Generator Functions**
   - Each generator type has its own analysis function
   - Consistent input/output interface
   - Easy to add new generator types

3. **Single Script, Multiple Generators**
   - One script loops through all configured generators
   - Signals saved per-currency with generator metadata
   - All generators run on same article set

4. **Generator Metadata Tracking**
   - Each signal tagged with `generator_id`, `generator_type`, `generator_params`
   - Enables comparison between generators
   - Supports strategy selection by generator

---

## Generator Types

### 1. Keyword-Based Generator

**ID**: `keyword-sentiment-v1.1-standard`
**Type**: `keyword-sentiment-v1.1`

**How it works**:
- Counts bullish/bearish keywords in article text
- 47 bullish keywords (gains, rises, strengthens, etc.)
- 51 bearish keywords (falls, declines, weakens, etc.)
- Negation pattern detection (e.g., "sheds gains" → bearish)
- Confidence based on keyword count and boost factor

**Strengths**:
- Fast (no API calls, < 1ms per article)
- Deterministic (same input = same output)
- No cost
- Good for obvious sentiment
- Transparent (easy to debug)

**Weaknesses**:
- Misses nuanced sentiment
- Can't understand context
- Many neutral classifications
- Lower confidence scores (~0.62 average)

**Parameters**:
```json
{
  "keyword_set": "standard",
  "negation_enabled": true,
  "confidence_boost": 1.5,
  "min_keyword_count": 1,
  "magnitude_estimation": true
}
```

**Detailed Methodology**:

The script counts occurrences of sentiment keywords in the combined news text:

- **Bullish keywords:** gains, rises, climbs, strengthens, hawkish, rate hike, positive, firm, strong
- **Bearish keywords:** falls, declines, tumbles, weakens, dovish, rate cut, negative, soft, weak
- **Neutral keywords:** stable, steady, unchanged, flat, consolidates, mixed, choppy

**Scoring:**
- Bullish score = bullish_count / total_keywords
- Bearish score = bearish_count / total_keywords
- Neutral score = neutral_count / total_keywords

**Direction:** Highest score wins (bullish, bearish, or neutral)

**Confidence:**
- Derived from the winning score
- Boosted by 1.5x (capped at 1.0)
- Higher confidence = clearer sentiment direction

**Strength Levels:**
- Strong: confidence ≥ 0.70
- Moderate: 0.40 ≤ confidence < 0.70
- Weak: confidence < 0.40

**Reasoning Extraction:**
The script attempts to identify key themes driving sentiment:
- Monetary policy signals (hawkish/dovish)
- Currency strength trends (gains/falls)
- Economic data (positive/weak indicators)

These are included in the `reasoning` field for transparency.

**Keyword Lists**:

Bullish (47 keywords):
```
gains, rises, climbs, strengthens, support, higher, advances, rallies,
upbeat, optimistic, hawkish, rate hike, boost, positive, firm, strong,
extends gains, surges, soars, jumps, spikes, outperforms, builds on gains,
extends rally, supported by, underpinned by, bolstered by, lifted by,
boosted by, resilient, robust, buoyant, gains ground, picks up, bounces,
rebounds
```

Bearish (51 keywords):
```
falls, declines, tumbles, weakens, pressure, lower, drops, slides, downbeat,
pessimistic, dovish, rate cut, drag, negative, soft, weak, loses ground,
under pressure, shudders, plunges, plummets, crashes, collapses, slumps,
sinks, dives, tumbled, erodes, deteriorates, shedding, dropping, slipping,
sliding, easing, retreats, pulls back, pullback, gives up, weighed on,
weighs on, caps, pressures, pressured, dented, hurt, dragged down,
struck down, blocks, trimmed, pared, reversed, uncertainty, concerns,
worries, risks, headwinds, falters, stumbles, struggles, subdued, muted
```

Negation Patterns (8 patterns):
```regex
shed(?:s|ding)?\s+(?:early[- ]session\s+)?gains?
trim(?:s|med|ming)?\s+gains?
pare(?:s|d|ing)?\s+gains?
give(?:s|ing)?\s+up\s+gains?
revers(?:e|es|ed|ing)\s+gains?
erase(?:s|d|ing)?\s+gains?
lose(?:s|ing)?\s+gains?
surrender(?:s|ed|ing)?\s+gains?
```

### 2. LLM-Based Generator

**ID**: `llm-sentiment-v1-haiku`
**Type**: `llm-sentiment-v1`

**How it works**:
- Uses Claude Haiku to analyze article sentiment
- Comprehensive prompt with FX-specific guidance
- Considers FX pair direction (base vs quote currency)
- Understands context, nuance, and sarcasm
- Returns direction, confidence, magnitude, reasoning

**Strengths**:
- Nuanced understanding - gets subtle sentiment
- Context-aware - understands FX pair mechanics
- Higher confidence - more decisive classifications (~0.71 average)
- Better reasoning - explains the sentiment
- Fewer neutrals - better at detecting direction

**Weaknesses**:
- API cost ($0.01 per 45 articles)
- Slower (~55 seconds for 45 articles)
- Requires API key
- Non-deterministic (slight variation possible)

**Parameters**:
```json
{
  "model": "claude-3-haiku-20240307",
  "temperature": 0.3,
  "max_tokens": 300
}
```

**Prompt Design**:
The LLM prompt includes:
1. FX pair direction rules (base vs quote)
2. Central bank policy indicators (hawkish/dovish)
3. Economic strength/weakness indicators
4. Output format (JSON with direction, confidence, magnitude, reasoning)

**Cost Analysis**:
- Model: Claude Haiku
- Input: ~200 tokens per article
- Output: ~100 tokens per article
- Cost per article: ~$0.0002
- Cost for 45 articles: **$0.009**
- Daily cost (45 articles): **$0.009/day**
- Monthly cost: **$0.27/month**

**Very cost-effective!**

---

## Performance Comparison

### Results from Test Run

**Total Signals Generated**: 90 signals (45 from each generator)

| Generator | Type | Signals | Bullish | Bearish | Neutral | Avg Conf |
|-----------|------|---------|---------|---------|---------|----------|
| **keyword-sentiment-v1.1-standard** | keyword-sentiment-v1.1 | 45 | 15 | 11 | 19 | 0.62 |
| **llm-sentiment-v1-haiku** | llm-sentiment-v1 | 45 | 17 | 14 | 14 | 0.71 |

**Key Observations**:
- LLM generator has **higher confidence** (0.71 vs 0.62)
- LLM generator has **fewer neutral signals** (14 vs 19) - more decisive
- LLM generator has **more bullish/bearish signals** - better at detecting sentiment
- Processing time: ~55 seconds for 45 articles

### Processing Time

| Generator | Articles | Time | Time/Article |
|-----------|----------|------|--------------|
| keyword-sentiment-v1.1-standard | 45 | ~5s | 0.11s |
| llm-sentiment-v1-haiku | 45 | ~55s | 1.22s |
| **Combined (both)** | 90 | **~60s** | **0.67s** |

### Cost Comparison

| Generator | Cost/Article | Cost/45 Articles | Cost/Month (30 days) |
|-----------|--------------|------------------|----------------------|
| keyword-sentiment-v1.1-standard | $0.00 | $0.00 | $0.00 |
| llm-sentiment-v1-haiku | $0.0002 | $0.009 | $0.27 |
| **Combined (both)** | **$0.0002** | **$0.009** | **$0.27** |

**Verdict**: LLM cost is negligible - only $0.27/month for much better analysis!

---

## Output Format

### Signal File Structure

**Location**: `/data/signals/{CURRENCY}/{date}.json`

Signals from BOTH generators in same file:

```json
{
  "currency": "USD",
  "date": "2026-02-24",
  "signals": [
    {
      "date": "2026-02-24",
      "generator_id": "keyword-sentiment-v1.1-standard",
      "generator_type": "keyword-sentiment-v1.1",
      "generator_params": {...},
      "signal_type": "news-sentiment",
      "currency": "USD",
      "predicted_direction": "neutral",
      "predicted_magnitude": null,
      "confidence": 0.5,
      "article_url": "...",
      "article_title": "...",
      "reasoning": "USD mixed signals; markets consolidating"
    },
    {
      "date": "2026-02-24",
      "generator_id": "llm-sentiment-v1-haiku",
      "generator_type": "llm-sentiment-v1",
      "generator_params": {...},
      "signal_type": "news-sentiment",
      "currency": "USD",
      "predicted_direction": "bullish",
      "predicted_magnitude": "medium",
      "confidence": 0.7,
      "article_url": "...",
      "article_title": "...",
      "reasoning": "The article contains several positive economic indicators..."
    }
  ]
}
```

**Key point**: Same file contains signals from BOTH generators for easy comparison!

---

## Configuration

### system_config.json

```json
{
  "signal_generators": {
    "keyword-sentiment-v1.1-standard": {
      "id": "keyword-sentiment-v1.1-standard",
      "type": "keyword-sentiment-v1.1",
      "params": {
        "keyword_set": "standard",
        "negation_enabled": true,
        "confidence_boost": 1.5,
        "min_keyword_count": 1,
        "magnitude_estimation": true
      },
      "description": "Keyword-based with 47 bullish, 51 bearish keywords"
    },
    "llm-sentiment-v1-haiku": {
      "id": "llm-sentiment-v1-haiku",
      "type": "llm-sentiment-v1",
      "params": {
        "model": "claude-3-haiku-20240307",
        "temperature": 0.3,
        "max_tokens": 300
      },
      "description": "LLM-based sentiment analysis using Claude Haiku"
    }
  }
}
```

---

## Integration with Strategies

Strategies can select which generators to use via `generator_ids` parameter:

```json
{
  "strategies": {
    "keyword-only-strategy": {
      "params": {
        "generator_ids": ["keyword-sentiment-v1.1-standard"]
      }
    },
    "llm-only-strategy": {
      "params": {
        "generator_ids": ["llm-sentiment-v1-haiku"]
      }
    },
    "combined-strategy": {
      "params": {
        "generator_ids": [
          "keyword-sentiment-v1.1-standard",
          "llm-sentiment-v1-haiku"
        ]
      }
    }
  }
}
```

This enables A/B testing of generator types!

---

## Environment Setup

### For LLM Generator

**Location**: `/workspace/project/.env`
```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Loading**: Uses centralized `env_loader.py`
```python
from env_loader import get_anthropic_key
api_key = get_anthropic_key()
```

---

## Dependencies

- **Step 3**: Requires news articles
- **Step 4**: Optional (uses horizon if available)
- **Environment**: ANTHROPIC_API_KEY in .env (for LLM generator)

---

## Next Steps

After running this step:
```bash
# Step 6: Check signal realization
python3 scripts/check-signal-realization.py

# Or run full pipeline
```

---

## Debugging

Check CSV export:
```bash
python3 scripts/export-pipeline-data.py
cat data/exports/step5_signals.csv
```

Count signals per currency and generator:
```bash
python3 -c "
import json, glob
for f in glob.glob('data/signals/*/*.json'):
    data = json.load(open(f))
    print(f\"{data['currency']}: {len(data['signals'])} signals\")
    for signal in data['signals']:
        print(f\"  - {signal['generator_id']}: {signal['predicted_direction']}\")
"
```

Compare generator performance:
```bash
python3 -c "
import json, glob
from collections import defaultdict

stats = defaultdict(lambda: {'bullish': 0, 'bearish': 0, 'neutral': 0, 'total': 0, 'conf_sum': 0})

for f in glob.glob('data/signals/*/*.json'):
    data = json.load(open(f))
    for signal in data['signals']:
        gen_id = signal['generator_id']
        direction = signal['predicted_direction']
        confidence = signal['confidence']

        stats[gen_id][direction] += 1
        stats[gen_id]['total'] += 1
        stats[gen_id]['conf_sum'] += confidence

for gen_id, data in stats.items():
    avg_conf = data['conf_sum'] / data['total'] if data['total'] > 0 else 0
    print(f\"{gen_id}:\")
    print(f\"  Total: {data['total']}\")
    print(f\"  Bullish: {data['bullish']}, Bearish: {data['bearish']}, Neutral: {data['neutral']}\")
    print(f\"  Avg Confidence: {avg_conf:.2f}\")
    print()
"
```

---

## Adding New Generators

### Step 1: Create Generator Function

Add to `generate-sentiment-signals-v2.py`:

```python
def analyze_sentiment_my_new_method(combined_text, currency, params):
    """
    My new sentiment analysis method

    Returns:
        tuple: (direction, confidence, reasoning, magnitude)
    """
    # Your analysis logic here
    direction = "bullish"
    confidence = 0.75
    reasoning = "My analysis says..."
    magnitude = "medium"

    return direction, confidence, reasoning, magnitude
```

### Step 2: Register in Dispatch Logic

Update the generator selection:

```python
if generator_type == 'keyword-sentiment-v1.1':
    analyze_func = analyze_sentiment_keywords
elif generator_type == 'llm-sentiment-v1':
    analyze_func = analyze_sentiment_llm
elif generator_type == 'my-new-method-v1':  # NEW
    analyze_func = analyze_sentiment_my_new_method
```

### Step 3: Add to Config

Update `system_config.json`:

```json
{
  "signal_generators": {
    "my-new-method-v1-default": {
      "id": "my-new-method-v1-default",
      "type": "my-new-method-v1",
      "params": {
        "param1": "value1"
      },
      "description": "My new sentiment analysis method"
    }
  }
}
```

### Step 4: Run

```bash
python3 scripts/generate-sentiment-signals-v2.py
```

All generators will run automatically!

---

## Troubleshooting

### Issue: LLM generator failing

**Symptom**: Only keyword signals generated, no LLM signals

**Solution**:
1. Check API key is set:
   ```bash
   grep ANTHROPIC_API_KEY /workspace/project/.env
   ```
2. Verify generator is enabled in `system_config.json`
3. Check script output for API errors

### Issue: Low confidence scores

**Symptom**: Many signals with confidence < 0.5

**Causes**:
- Keyword generator: Few matching keywords in text
- LLM generator: Ambiguous or unclear article content

**Solution**:
- For keyword: Add more keywords to lists
- For LLM: Review prompt to encourage more decisive classifications
- Consider filtering out low-confidence signals in strategies

---

## Notes

- Runs daily after Step 3 (and optionally Step 4)
- Creates one signal per article per currency per generator
- Rerunning overwrites previous day's signals
- Safe to rerun for debugging
- LLM generator provides significantly better quality at minimal cost
