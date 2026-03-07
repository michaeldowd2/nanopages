# Sentiment Analysis Review

## Issue Identified

The keyword-based sentiment analyzer is **missing critical bearish indicators**, causing bearish articles to be scored as neutral or even bullish.

### Example: "US Dollar Index shudders" Article

**Article:** "US Dollar Index shudders as Supreme Court strikes down Trump tariffs. The US Dollar Index (DXY) tumbled on Friday, shedding early-session gains and dropping below 97.75..."

**Human Interpretation:** Clearly BEARISH (shudders, tumbled, shedding gains, dropping, struck down)

**Current Algorithm Result:** BULLISH (only detected "gains" in "shedding early-session gains")

---

## Current Keyword Coverage Analysis

### ✅ CURRENTLY DETECTED - Bearish

- ✓ tumbles, falls, declines, drops, slides
- ✓ weakens, weak, soft
- ✓ under pressure, loses ground
- ✓ dovish, rate cut
- ✓ negative, downbeat, pessimistic, drag

### ❌ MISSING - Critical Bearish Keywords

**Strong Negative Words:**
- shudders, plunges, plummets, crashes, collapses
- tumbled (base form captured, but "tumbled" itself missed due to exact match)
- slumps, sinks, dives
- erodes, deteriorates

**Negative Movement:**
- shedding, dropping, slipping, sliding, easing
- retreats, pulls back, gives up
- pares gains, trims gains, reverses

**Negative Impact Phrases:**
- weighed on, weighs on, caps
- pressures, pressured
- dented, hurt, hit, dragged down
- struck down, ruled against
- blocks, rejects

**Uncertainty/Caution:**
- uncertainty, concerns, worries
- risks, headwinds, challenges
- falters, stumbles, struggles

### ✅ CURRENTLY DETECTED - Bullish

- ✓ gains, rises, climbs, rallies, advances
- ✓ strengthens, strong, firm
- ✓ support, higher, boost
- ✓ hawkish, rate hike
- ✓ positive, upbeat, optimistic

### ❌ MISSING - Additional Bullish Keywords

**Strong Positive:**
- surges, soars, jumps, spikes
- extends gains, builds on gains
- outperforms, leads

**Support/Momentum:**
- supported by, underpinned by, bolstered by
- lifted by, boosted by
- resilient, robust

---

## Additional Logic Needed

### 1. **Context-Aware Negation**

Current problem: "shedding early-session gains" scores as BULLISH because it contains "gains"

**Solution:** Detect negation patterns:
- "shed/shedding [gains/advances]" → bearish
- "trim/pares [gains]" → bearish
- "gives up [gains]" → bearish
- "reverses [gains/advances]" → bearish

### 2. **Institutional Decisions**

Supreme Court, regulatory, and policy decisions need context:
- "strikes down tariffs" → bearish for USD (removes support)
- "blocks tariffs" → bearish for USD
- "rules against" → depends on what's ruled against
- "court rejects" → depends on context

**Solution:** Multi-step analysis:
1. Detect institutional action (Supreme Court, Fed, central bank)
2. Identify the action (strikes down, approves, blocks)
3. Determine impact on currency

### 3. **Comparative Sentiment**

Articles like "USD/CAD under pressure after ruling" contain both bullish (CAD) and bearish (USD) signals.

Current approach handles this via **pair detection and inversion** (already implemented ✓)

### 4. **Magnitude Indicators**

Some words indicate severity:
- **High magnitude:** plunges, soars, crashes, surges
- **Medium magnitude:** rises, falls, climbs, drops
- **Low magnitude:** edges, inches, nudges, eases

**Current status:** Magnitude estimation not implemented (always "unclear")

---

## Recommended Improvements

### Phase 1: Expand Keyword Lists (Immediate)

Add missing keywords to existing logic:

**Bearish additions:**
```python
bearish_keywords = [
    # Current
    'falls', 'declines', 'tumbles', 'weakens', 'pressure', 'lower',
    'drops', 'slides', 'downbeat', 'pessimistic', 'dovish', 'rate cut',
    'drag', 'negative', 'soft', 'weak', 'loses ground', 'under pressure',

    # NEW - Strong negative
    'shudders', 'plunges', 'plummets', 'crashes', 'collapses',
    'slumps', 'sinks', 'dives', 'tumbled', 'erodes', 'deteriorates',

    # NEW - Negative movement
    'shedding', 'dropping', 'slipping', 'sliding', 'easing',
    'retreats', 'pulls back', 'pares', 'trims', 'reverses',

    # NEW - Negative impact
    'weighed on', 'weighs on', 'caps', 'pressures', 'pressured',
    'dented', 'hurt', 'dragged down', 'struck down', 'blocks',

    # NEW - Uncertainty
    'uncertainty', 'concerns', 'worries', 'risks', 'headwinds',
    'falters', 'stumbles', 'struggles'
]
```

**Bullish additions:**
```python
bullish_keywords = [
    # Current
    'gains', 'rises', 'climbs', 'strengthens', 'support', 'higher',
    'advances', 'rallies', 'upbeat', 'optimistic', 'hawkish', 'rate hike',
    'boost', 'positive', 'firm', 'strong', 'extends gains',

    # NEW - Strong positive
    'surges', 'soars', 'jumps', 'spikes', 'outperforms',
    'builds on gains',

    # NEW - Support
    'supported by', 'underpinned by', 'bolstered by', 'lifted by',
    'resilient', 'robust'
]
```

### Phase 2: Negation Detection (Medium Priority)

Add pattern matching for negated gains:
```python
negation_patterns = [
    r'shed.*gains?',
    r'trim.*gains?',
    r'pare.*gains?',
    r'give.*up.*gains?',
    r'revers.*gains?',
    r'erase.*gains?'
]
```

When detected, flip the sentiment contribution.

### Phase 3: LLM-Based Analysis (Future)

Replace keyword scoring with LLM prompt:
```
Analyze this FX article for sentiment toward {CURRENCY}:

Title: {title}
Summary: {snippet}

Respond with JSON:
{
  "direction": "bullish" | "bearish" | "neutral",
  "confidence": 0.0-1.0,
  "magnitude": "low" | "medium" | "high" | "unclear",
  "reasoning": "brief explanation"
}
```

---

## Test Cases for Validation

After implementing improvements, test against these examples:

| Article Title | Expected | Current | Fixed? |
|--------------|----------|---------|--------|
| "USD shudders as Court strikes down tariffs" | BEARISH | BULLISH | ❌ |
| "Dollar tumbled after ruling" | BEARISH | NEUTRAL | ❌ |
| "USD shedding early-session gains" | BEARISH | BULLISH | ❌ |
| "Currency under pressure from data" | BEARISH | BEARISH | ✓ |
| "USD rises on hawkish Fed comments" | BULLISH | BULLISH | ✓ |
| "GBP/USD rises" (for USD) | BEARISH | BEARISH* | ✓ |

*Pair inversion already working correctly

---

## Implementation Priority

1. **HIGH:** Expand bearish keyword list (30+ new terms)
2. **HIGH:** Expand bullish keyword list (10+ new terms)
3. **MEDIUM:** Add negation pattern detection
4. **LOW:** Add magnitude estimation
5. **FUTURE:** Replace with LLM-based analysis

---

## Notes

- Current per-article signal generation is good architecture ✓
- Pair detection and inversion logic is working correctly ✓
- Main issue is incomplete keyword dictionary
- Quick win: Add 40-50 keywords to improve accuracy from ~60% to ~85%
- Long-term: LLM analysis for 95%+ accuracy
