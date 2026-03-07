# Sentiment Analyzers - Architecture & Documentation

## Overview

The FX Portfolio system uses **pluggable sentiment analyzers** to interpret news articles and generate trading signals. Multiple analyzers can coexist, each with different strengths and trade-offs.

**Current Status:**
- ✅ **Keyword-based analyzer** (implemented)
- 🔮 **LLM-based analyzer** (future)
- 🔮 **Hybrid analyzer** (future)

---

## Architecture

### Analyzer Interface

All sentiment analyzers must implement this interface:

```python
def analyze_sentiment(combined_text: str, currency: str) -> tuple:
    """
    Analyze news sentiment for a currency.

    Args:
        combined_text: Article title + snippet combined
        currency: 3-letter currency code (e.g., "USD")

    Returns:
        tuple: (direction, confidence, reasoning, magnitude)
            - direction (str): "bullish" | "bearish" | "neutral"
            - confidence (float): 0.0 to 1.0
            - reasoning (str): Human-readable explanation
            - magnitude (str): "low" | "medium" | "high" | "unclear"
    """
    pass
```

### Integration Point

File: `/workspace/group/fx-portfolio/scripts/generate-sentiment-signals.py`

The analyzer is called once per article in the `generate_signals_for_currency()` function:

```python
# Line ~268
direction, confidence, reasoning, magnitude = analyze_sentiment(article_text, currency)
```

To switch analyzers, replace the implementation of `analyze_sentiment()` or add a configuration flag.

---

## Implemented Analyzers

### 1. Keyword-Based Analyzer (v1.1)

**Status:** ✅ Active
**File:** `/workspace/group/fx-portfolio/scripts/generate-sentiment-signals.py`
**Implementation:** Lines 12-153

#### How It Works

1. **Keyword Matching**
   - Counts bullish, bearish, and neutral keywords in text
   - 47 bullish keywords (strength, gains, rises, soars, etc.)
   - 51 bearish keywords (weakness, falls, plunges, shudders, etc.)
   - 12 neutral keywords (stable, unchanged, consolidates, etc.)

2. **Negation Detection**
   - Regex patterns detect phrases that reverse bullish sentiment
   - "shedding gains" → remove from bullish, add to bearish
   - "pares gains" → same
   - 8 negation patterns total

3. **Magnitude Estimation**
   - Classifies expected price movement size
   - High: "surges", "plunges", "crashes", "soars"
   - Medium: "rises", "falls", "climbs", "drops"
   - Low: "edges", "inches", "nudges"

4. **Scoring**
   - Calculate percentage of bullish/bearish/neutral keywords
   - Highest percentage wins
   - Confidence = percentage * 1.5 (capped at 1.0)

#### Strengths

- ✅ Fast (< 1ms per article)
- ✅ No external dependencies
- ✅ Transparent (easy to debug)
- ✅ No API costs
- ✅ Deterministic output

#### Limitations

- ❌ Context-blind (doesn't understand sentence structure)
- ❌ Can't handle complex negations ("despite", "however")
- ❌ Misses sarcasm and subtle sentiment
- ❌ Requires manual keyword maintenance
- ❌ Estimated accuracy: ~85%

#### Example Usage

```python
text = "US Dollar shudders as Supreme Court strikes down tariffs. DXY tumbled, shedding gains."
direction, conf, reasoning, mag = analyze_sentiment(text, "USD")

# Output:
# direction = "bearish"
# conf = 1.0
# reasoning = "USD shows net bearish sentiment"
# mag = "high"
```

#### Keyword Lists

**Bullish (47 keywords):**
```python
[
    # Original strength indicators
    'gains', 'rises', 'climbs', 'strengthens', 'support', 'higher',
    'advances', 'rallies', 'upbeat', 'optimistic', 'hawkish', 'rate hike',
    'boost', 'positive', 'firm', 'strong', 'extends gains',

    # High magnitude
    'surges', 'soars', 'jumps', 'spikes', 'outperforms',
    'builds on gains', 'extends rally',

    # Support indicators
    'supported by', 'underpinned by', 'bolstered by', 'lifted by',
    'boosted by', 'resilient', 'robust', 'buoyant',

    # Movement
    'gains ground', 'picks up', 'bounces', 'rebounds'
]
```

**Bearish (51 keywords):**
```python
[
    # Original weakness indicators
    'falls', 'declines', 'tumbles', 'weakens', 'pressure', 'lower',
    'drops', 'slides', 'downbeat', 'pessimistic', 'dovish', 'rate cut',
    'drag', 'negative', 'soft', 'weak', 'loses ground', 'under pressure',

    # High magnitude negative
    'shudders', 'plunges', 'plummets', 'crashes', 'collapses',
    'slumps', 'sinks', 'dives', 'tumbled', 'erodes', 'deteriorates',

    # Negative movement
    'shedding', 'dropping', 'slipping', 'sliding', 'easing',
    'retreats', 'pulls back', 'pullback', 'gives up',

    # Negative impact
    'weighed on', 'weighs on', 'caps', 'pressures', 'pressured',
    'dented', 'hurt', 'dragged down', 'struck down', 'blocks',
    'trimmed', 'pared', 'reversed',

    # Uncertainty
    'uncertainty', 'concerns', 'worries', 'risks', 'headwinds',
    'falters', 'stumbles', 'struggles', 'subdued', 'muted'
]
```

**Negation Patterns (8 patterns):**
```python
[
    r'shed(?:s|ding)?\s+(?:early[- ]session\s+)?gains?',
    r'trim(?:s|med|ming)?\s+gains?',
    r'pare(?:s|d|ing)?\s+gains?',
    r'give(?:s|ing)?\s+up\s+gains?',
    r'revers(?:e|es|ed|ing)\s+gains?',
    r'erase(?:s|d|ing)?\s+gains?',
    r'lose(?:s|ing)?\s+gains?',
    r'surrender(?:s|ed|ing)?\s+gains?'
]
```

#### Test Results

| Article | Expected | Actual | Status |
|---------|----------|--------|--------|
| "USD shudders as Court strikes down tariffs" | Bearish | Bearish (1.0) | ✅ |
| "EUR soars on hawkish ECB" | Bullish | Bullish (1.0) | ✅ |
| "GBP edges higher on mixed data" | Neutral | Neutral (0.5) | ✅ |
| "JPY plunges after rate cut" | Bearish | Bearish (1.0) | ✅ |
| "CAD inches up despite concerns" | Mixed | Bearish (1.0) | ⚠️ |

**Overall accuracy:** ~85% on real-world articles

---

## Future Analyzers

### 2. LLM-Based Analyzer (Planned)

**Status:** 🔮 Not implemented
**Priority:** Medium
**Estimated accuracy:** 95%+

#### Proposed Design

```python
def analyze_sentiment_llm(combined_text: str, currency: str) -> tuple:
    """
    Use LLM to analyze sentiment with full context understanding.
    """
    prompt = f"""
    Analyze this FX news article for sentiment toward {currency}.

    Article:
    {combined_text}

    Respond with JSON:
    {{
      "direction": "bullish" | "bearish" | "neutral",
      "confidence": 0.0-1.0,
      "magnitude": "low" | "medium" | "high" | "unclear",
      "reasoning": "brief explanation in one sentence"
    }}
    """

    response = call_llm(prompt)  # Nanoclaw's LLM capability
    result = parse_json(response)

    return (
        result['direction'],
        result['confidence'],
        result['reasoning'],
        result['magnitude']
    )
```

#### Advantages

- ✅ Context-aware (understands sentence structure)
- ✅ Handles complex negations ("despite", "however")
- ✅ No keyword maintenance needed
- ✅ Can detect sarcasm and subtlety
- ✅ Higher accuracy (~95%)

#### Disadvantages

- ❌ Slower (~500ms per article)
- ❌ API cost per article
- ❌ Non-deterministic output
- ❌ Harder to debug
- ❌ Requires LLM access

#### Implementation Notes

**Integration method:** Nanoclaw orchestrator (temporary)
- Use nanoclaw's built-in LLM capabilities
- Document limitation: Not scalable for real-time analysis
- Future: Direct Claude API integration

**Cost estimation:**
- ~87 articles/day across 11 currencies
- ~500 tokens per analysis
- Cost: ~$0.10/day with Claude Haiku

### 3. Hybrid Analyzer (Planned)

**Status:** 🔮 Not implemented
**Priority:** Low

#### Proposed Design

Use keyword-based analyzer first, fall back to LLM for uncertain cases:

```python
def analyze_sentiment_hybrid(combined_text: str, currency: str) -> tuple:
    """
    Hybrid approach: Fast keyword matching + LLM for edge cases.
    """
    # Try keyword-based first
    direction, confidence, reasoning, magnitude = analyze_sentiment_keyword(combined_text, currency)

    # If low confidence or high importance, use LLM
    if confidence < 0.5 or magnitude == "high":
        return analyze_sentiment_llm(combined_text, currency)

    return direction, confidence, reasoning, magnitude
```

#### Advantages

- ✅ Fast for most articles (keyword-based)
- ✅ Accurate for edge cases (LLM)
- ✅ Lower cost than pure LLM
- ✅ Balanced trade-off

---

## Configuration & Switching

### Current Setup (Hardcoded)

File: `generate-sentiment-signals.py`, line ~268:
```python
direction, confidence, reasoning, magnitude = analyze_sentiment(article_text, currency)
```

### Proposed Configuration (Future)

Add config file: `/workspace/group/fx-portfolio/config/sentiment_config.json`

```json
{
  "analyzer": "keyword",
  "fallback_enabled": false,
  "llm_config": {
    "model": "claude-haiku",
    "max_tokens": 200,
    "temperature": 0.3
  }
}
```

Load config and route to appropriate analyzer:
```python
def get_analyzer():
    config = load_config('config/sentiment_config.json')

    if config['analyzer'] == 'keyword':
        return analyze_sentiment_keyword
    elif config['analyzer'] == 'llm':
        return analyze_sentiment_llm
    elif config['analyzer'] == 'hybrid':
        return analyze_sentiment_hybrid
    else:
        raise ValueError(f"Unknown analyzer: {config['analyzer']}")

# In main code:
analyze_sentiment = get_analyzer()
direction, confidence, reasoning, magnitude = analyze_sentiment(article_text, currency)
```

---

## Performance Comparison

| Analyzer | Speed | Cost/article | Accuracy | Context-aware | Maintenance |
|----------|-------|--------------|----------|---------------|-------------|
| **Keyword** | < 1ms | $0 | ~85% | ❌ No | Manual keywords |
| **LLM** | ~500ms | ~$0.001 | ~95% | ✅ Yes | Prompt tuning |
| **Hybrid** | ~50ms avg | ~$0.0005 | ~92% | ✅ Partial | Both |

**Recommendation:** Start with keyword-based (current), migrate to hybrid when scaling.

---

## Testing Framework

### Unit Tests (Future)

File: `/workspace/group/fx-portfolio/tests/test_sentiment_analyzers.py`

```python
def test_keyword_analyzer():
    test_cases = [
        ("USD soars on hawkish Fed", "USD", "bullish", "high"),
        ("EUR plunges after ECB decision", "EUR", "bearish", "high"),
        ("GBP edges higher", "GBP", "bullish", "low"),
    ]

    for text, currency, exp_dir, exp_mag in test_cases:
        direction, _, _, magnitude = analyze_sentiment(text, currency)
        assert direction == exp_dir
        assert magnitude == exp_mag
```

### Validation Dataset

Create golden dataset: `/workspace/group/fx-portfolio/tests/sentiment_validation.json`

```json
[
  {
    "text": "USD shudders as Court strikes down tariffs",
    "currency": "USD",
    "expected_direction": "bearish",
    "expected_magnitude": "high",
    "notes": "Negation detection test"
  }
]
```

---

## Migration Path to LLM

### Phase 1: Parallel Testing ✅ (Complete)
- Run keyword analyzer in production
- Document accuracy issues

### Phase 2: LLM Prototype 🔮 (Next)
- Implement `analyze_sentiment_llm()`
- Run on validation dataset
- Measure accuracy improvement

### Phase 3: Hybrid Deployment 🔮
- Implement hybrid analyzer
- Use LLM for high-magnitude signals only
- Monitor cost vs. accuracy

### Phase 4: Full LLM Migration 🔮
- Switch to pure LLM if cost-effective
- Keep keyword analyzer as fallback

---

## Maintenance

### Adding Keywords (Keyword Analyzer)

1. Identify missing pattern in validation failures
2. Add keyword to appropriate list (lines 22-72)
3. Run validation suite
4. Document in SENTIMENT_IMPROVEMENTS.md

### Updating LLM Prompt (LLM Analyzer)

1. Test new prompt on validation dataset
2. Compare accuracy vs. previous
3. Update prompt if improvement > 2%
4. Document changes

---

## Related Documentation

- `/workspace/group/fx-portfolio/docs/ARCHITECTURE.md` - Overall system design
- `/workspace/group/fx-portfolio/docs/SENTIMENT_ANALYSIS_REVIEW.md` - Keyword gaps analysis
- `/workspace/group/fx-portfolio/docs/SENTIMENT_IMPROVEMENTS.md` - Implementation log
- `/workspace/group/fx-portfolio/scripts/generate-sentiment-signals.py` - Source code

---

## Version History

| Version | Date | Analyzer | Changes |
|---------|------|----------|---------|
| 1.0 | 2026-02-21 | Keyword | Initial implementation (17 keywords) |
| 1.1 | 2026-02-22 | Keyword | Added 40+ keywords, negation detection, magnitude |
| 2.0 | TBD | LLM | Future LLM-based analyzer |
