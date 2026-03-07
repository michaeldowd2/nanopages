# Pipeline Issues & Architectural Recommendations

**Date**: 2026-02-24
**Pipeline Run**: Complete (Steps 1-7)
**Dashboard**: https://michaeldowd2.github.io/nanopages/fx-dashboard/

---

## Executive Summary

Successfully ran full pipeline from clean slate. **113 records** exported across all steps. Identified **1 critical architectural issue** (Step 4 manual intervention) and **5 additional improvement opportunities**.

---

## Pipeline Run Results

### ✅ Step 1: Fetch Exchange Rates
- **Status**: SUCCESS
- **Duration**: 0.16s
- **Output**: 121 currency pairs
- **Data Source**: GitHub Currency API (real data, not mock)
- **Issues**: None

### ✅ Step 2: Calculate Currency Indices
- **Status**: SUCCESS
- **Duration**: 0.01s
- **Output**: 11 index points (1 day of data)
- **Issues**: None
- **Note**: All indices at 100.00 (0.00% change) because only 1 day of data exists

### ⚠️ Step 3: Fetch News
- **Status**: PARTIAL SUCCESS
- **Duration**: ~10s
- **Output**: 34 articles from 2/6 sources
- **Working Sources**:
  - ForexLive: 25 articles ✓
  - FXStreet: 30 articles ✓
- **Blocked Sources** (HTTP 403):
  - DailyFX ✗
  - Reddit /r/forex ✗
  - Reddit /r/Economics ✗
  - Reddit /r/economy ✗
- **Issues**: See Issue #2 below

### 🔴 Step 4: Analyze Time Horizons
- **Status**: REQUIRES MANUAL INTERVENTION
- **Output**: 0 analyses (34 articles pending)
- **Issues**: See **CRITICAL ISSUE #1** below

### ✅ Step 5: Generate Sentiment Signals
- **Status**: SUCCESS
- **Duration**: 0.01s
- **Output**: 34 signals (7 bullish, 10 bearish, 17 neutral)
- **Coverage**: 7/11 currencies with signals
- **Issues**: None

### ✅ Step 6: Check Signal Realization
- **Status**: SUCCESS
- **Duration**: 0.01s
- **Output**: 34 signals checked (all unrealized - too early)
- **Linked with horizon data**: 0 (because Step 4 incomplete)
- **Issues**: None (expected behavior)

### ✅ Step 7: Execute Trading Strategies
- **Status**: SUCCESS
- **Duration**: 0.03s
- **Output**: 9 strategy runs, 0 trades executed
- **Issues**: None (no trades expected with all unrealized signals)

---

## CRITICAL ISSUE #1: Step 4 Requires Manual Orchestration

### Problem

**Step 4 (Time Horizon Analysis) cannot run autonomously** - it requires nanoclaw orchestration for LLM-based article analysis.

```bash
$ python3 scripts/analyze-time-horizons.py

⚠️  34 articles need analysis

This script requires orchestrator intervention.
Run the 'analyze-article-horizons' skill via nanoclaw.
```

### Why This Is Critical

1. **Breaks Pipeline Automation**: Cannot run full pipeline end-to-end without human intervention
2. **Blocks Step 6 Enhancement**: Signal realization checks can't link with horizon data
3. **Limits Production Deployment**: Can't schedule automated daily runs
4. **Creates Bottleneck**: Every pipeline run requires manual LLM orchestration

### Current Architecture

```
┌─────────────────────────────────────────────────────┐
│ Step 4: Horizon Analysis (COORDINATOR)              │
│                                                      │
│ 1. Finds unanalyzed articles                        │
│ 2. Prints "requires orchestrator intervention"      │
│ 3. STOPS - waits for nanoclaw to:                   │
│    • Read each article                              │
│    • Prompt LLM with article content                │
│    • Parse LLM response                             │
│    • Save analysis results                          │
│ 4. Resume pipeline manually                         │
└─────────────────────────────────────────────────────┘
```

### Root Cause

- **No Anthropic API integration** in the script
- Relies on external orchestrator (nanoclaw) to make LLM calls
- Script is just a "coordinator" - doesn't actually perform analysis

### Impact on This Run

- **34 articles pending analysis**
- **0 horizon estimates available** for signal linking
- Pipeline technically completes but with degraded functionality

---

## RECOMMENDED SOLUTIONS

### Solution 1A: Direct Anthropic API Integration (Recommended)

**Add API-based LLM calls directly to the script.**

#### Implementation

```python
# Add to analyze-time-horizons.py

import anthropic
import os

def analyze_article_with_api(article):
    """Use Anthropic API to analyze article horizon"""

    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )

    prompt = f"""Analyze this forex news article and estimate the time horizon for its impact:

Title: {article['title']}
Snippet: {article['snippet']}
Currency: {article['currency']}

Respond in JSON format:
{{
  "horizon_days": <number>,
  "horizon_category": "immediate|short-term|medium-term|long-term",
  "confidence": <0.0-1.0>,
  "reasoning": "<brief explanation>"
}}
"""

    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    # Parse JSON response
    import json
    result = json.loads(message.content[0].text)

    return {
        'horizon_days': result['horizon_days'],
        'horizon_category': result['horizon_category'],
        'confidence': result['confidence'],
        'reasoning': result['reasoning'],
        'method': 'llm-horizon-v1-default'
    }
```

#### Pros
- ✅ Fully autonomous pipeline
- ✅ Production-ready
- ✅ Can run on schedule
- ✅ Uses same LLM as nanoclaw
- ✅ Simple implementation

#### Cons
- ⚠️ Requires ANTHROPIC_API_KEY environment variable
- ⚠️ API costs (though minimal - ~34 articles/day × $0.003 = ~$0.10/day)
- ⚠️ Requires anthropic Python package

#### Estimated Effort
- **2-3 hours** to implement and test

---

### Solution 1B: Batch Processing Mode

**Allow Step 4 to run in "batch mode" with pending queue, then process later.**

#### Implementation

```python
# Modified workflow

def main():
    articles = get_articles_needing_analysis()

    if len(articles) == 0:
        print("✓ All articles analyzed")
        return

    # Check for API key
    if os.environ.get("ANTHROPIC_API_KEY"):
        # Process autonomously
        for article in articles:
            analysis = analyze_article_with_api(article)
            save_analysis(article['url'], analysis)
    else:
        # Queue for manual processing
        save_pending_batch(articles)
        print(f"⚠️  {len(articles)} articles queued for manual analysis")
        print("   Set ANTHROPIC_API_KEY to enable autonomous processing")
```

#### Pros
- ✅ Graceful degradation
- ✅ Works with or without API key
- ✅ Clear error messaging

#### Cons
- ⚠️ Still requires manual intervention if no API key
- ⚠️ Two code paths to maintain

---

### Solution 1C: Alternative - Rule-Based Heuristic

**Replace LLM analysis with keyword-based heuristics.**

#### Implementation

```python
def estimate_horizon_heuristic(article):
    """Estimate horizon using keyword matching"""

    text = (article['title'] + ' ' + article['snippet']).lower()

    # Immediate (0-1 days)
    if any(word in text for word in ['today', 'now', 'breaking', 'flash', 'alert']):
        return {'horizon_days': 1, 'category': 'immediate', 'confidence': 0.7}

    # Short-term (1-7 days)
    if any(word in text for word in ['this week', 'tomorrow', 'upcoming']):
        return {'horizon_days': 3, 'category': 'short-term', 'confidence': 0.6}

    # Medium-term (7-30 days)
    if any(word in text for word in ['this month', 'quarter', 'forecast']):
        return {'horizon_days': 14, 'category': 'medium-term', 'confidence': 0.5}

    # Default: short-term
    return {'horizon_days': 3, 'category': 'short-term', 'confidence': 0.4}
```

#### Pros
- ✅ No API required
- ✅ Fast execution
- ✅ No external dependencies
- ✅ Zero cost

#### Cons
- ❌ Lower accuracy than LLM
- ❌ Brittle (requires keyword maintenance)
- ❌ Misses nuanced context
- ❌ Not suitable for production trading

---

## Issue #2: RSS Feed Blocking (HTTP 403)

### Problem

**4 out of 6 news sources return HTTP 403 errors**, reducing news coverage by 67%.

### Affected Sources

1. DailyFX (`https://www.dailyfx.com/feeds/market-news`)
2. Reddit /r/forex (`https://www.reddit.com/r/forex/.rss`)
3. Reddit /r/Economics (`https://www.reddit.com/r/Economics/.rss`)
4. Reddit /r/economy (`https://www.reddit.com/r/economy/.rss`)

### Root Cause

- **Missing User-Agent header**: Sites block requests without proper User-Agent
- **Rate limiting**: Reddit blocks programmatic RSS access
- **Bot detection**: Some sites detect and block automated requests

### Impact

- Only **2 working sources** (ForexLive, FXStreet)
- **34 articles** fetched (could be 100+ with all sources)
- Limited currency coverage (NOK, SEK, MXN have 0 articles)

### Recommended Solution

#### Option A: Add User-Agent Headers

```python
# In fetch-news.py

import urllib.request

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

req = urllib.request.Request(feed_url, headers=headers)
response = urllib.request.urlopen(req)
```

#### Option B: Replace Blocked Sources

Alternative free RSS feeds:
- **Investing.com** - Good FX coverage
- **MarketWatch** - Major currencies
- **Bloomberg** - If RSS available
- **Central Bank feeds** - ECB, Fed, BoE announcements

#### Option C: Use NewsAPI

Programmatic news API (free tier: 100 requests/day):
- **NewsAPI.org** - `api.newsapi.org/v2/everything?q=forex`

---

## Issue #3: Single Day of Price Data (Low Priority)

### Problem

**Indices show 0.00% change** because only 1 day of exchange rate data exists.

### Current State

```
Currency        Index   Daily Δ%
------------------------------------
EUR          100.0000      0.00%
USD          100.0000      0.00%
GBP          100.0000      0.00%
```

### Root Cause

- Used `--all` clear mode before running pipeline
- Only today's prices fetched (2026-02-24)
- Need ≥2 days for meaningful change calculations

### Impact

- **Low** - This is expected behavior after full reset
- Indices will show meaningful data after 2-3 days of accumulation

### Solution

**No action needed** - this resolves naturally as historical data accumulates.

For testing purposes, could:
1. Run Step 1 multiple times with different dates (manual backfill)
2. Add a "backfill" mode to fetch historical rates
3. Wait 2-3 days for natural accumulation

---

## Issue #4: No Trades Executed (Expected Behavior)

### Current State

All 9 strategies executed **0 trades** (€10,000 portfolios unchanged).

### Root Cause - Cascading Dependencies

```
No trades because:
  ↓
All signals unrealized (too early to judge)
  ↓
Only 1 day of price data (can't check multi-day movements)
  ↓
No horizon estimates (Step 4 incomplete)
  ↓
Can't determine when signals should be realized
```

### Impact

**Low** - This is expected for a first-day run. Will resolve as:
1. Historical data accumulates (2-3 days)
2. Horizon estimates are added (fix Issue #1)
3. Signals mature and get realized/contradicted

### Solution

**No action needed** - expected behavior for initial run.

---

## Issue #5: Script Naming Inconsistency (Minor)

### Problem

Step 7 script is named `strategy-simple-momentum.py` instead of `execute-strategies.py`.

### Impact

- **Very Low** - Just a naming convention issue
- Slightly confusing when looking for execution script

### Solution

Rename for consistency:
```bash
mv scripts/strategy-simple-momentum.py scripts/execute-strategies.py
```

Or update documentation to use the current name.

---

## ARCHITECTURAL RECOMMENDATIONS

### 1. **Add Anthropic API Integration** (PRIORITY 1)

**Implement Solution 1A** to make Step 4 fully autonomous.

**Estimated ROI**:
- Effort: 2-3 hours
- Cost: ~$0.10/day (34 articles × $0.003)
- Benefit: Fully autonomous pipeline, production-ready

**Implementation Plan**:
1. Install `anthropic` package
2. Add API-based analysis function
3. Set ANTHROPIC_API_KEY environment variable
4. Add graceful fallback (warn if key missing)
5. Test with 5-10 articles
6. Deploy to production

---

### 2. **Fix RSS Feed Blocking** (PRIORITY 2)

**Implement Solution: Add User-Agent Headers**

**Estimated ROI**:
- Effort: 30 minutes
- Cost: $0
- Benefit: 3-4x more articles, better currency coverage

**Implementation**:
```python
# Simple one-line fix in fetch-news.py
headers = {'User-Agent': 'Mozilla/5.0 (compatible; FXPortfolioBot/1.0)'}
req = urllib.request.Request(feed_url, headers=headers)
```

---

### 3. **Add Pipeline Orchestration Script** (PRIORITY 3)

**Create a master runner that executes all steps sequentially.**

**Current Problem**:
- Must manually run each script: `python3 scripts/step1.py && python3 scripts/step2.py...`
- Error handling is manual
- No unified logging

**Proposed Solution**:

```python
#!/usr/bin/env python3
# scripts/run-full-pipeline.py

import subprocess
import sys

STEPS = [
    ("Step 1: Fetch Exchange Rates", "scripts/fetch-exchange-rates.py"),
    ("Step 2: Calculate Indices", "scripts/calculate-currency-indices.py"),
    ("Step 3: Fetch News", "scripts/fetch-news.py"),
    ("Step 4: Analyze Horizons", "scripts/analyze-time-horizons.py"),
    ("Step 5: Generate Signals", "scripts/generate-sentiment-signals.py"),
    ("Step 6: Check Realization", "scripts/check-signal-realization.py"),
    ("Step 7: Execute Strategies", "scripts/strategy-simple-momentum.py"),
]

def run_pipeline():
    for name, script in STEPS:
        print(f"\n{'='*60}")
        print(f"Running: {name}")
        print('='*60)

        result = subprocess.run(["python3", script], capture_output=False)

        if result.returncode != 0:
            print(f"❌ {name} failed with code {result.returncode}")
            sys.exit(1)

    print("\n✅ Pipeline complete - running exports...")
    subprocess.run(["python3", "scripts/export-pipeline-data.py"])
    subprocess.run(["python3", "scripts/export-logs.py"])
    subprocess.run(["python3", "scripts/export-exchange-rates.py"])

    print("\n✅ All done! Deploy with: publish-github-pages fx-dashboard")

if __name__ == "__main__":
    run_pipeline()
```

**Benefits**:
- Single command: `python3 scripts/run-full-pipeline.py`
- Automatic error detection
- Unified output
- Easier to schedule (cron, systemd)

---

### 4. **Add Backfill Capability** (PRIORITY 4)

**Allow fetching historical exchange rates for past dates.**

**Use Case**: After clearing data, quickly rebuild 30 days of history.

**Implementation**:

```python
# scripts/backfill-exchange-rates.py

import sys
from datetime import datetime, timedelta

def backfill(days=30):
    """Fetch exchange rates for past N days"""

    # Note: GitHub Currency API supports historical queries:
    # https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@2026-02-20/v1/currencies/eur.json

    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')

        # Fetch historical rate for this date
        url = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date_str}/v1/currencies/eur.json"

        # Save to data/prices/fx-rates-{date_str}.json
        # (implementation details omitted)

# Usage: python3 scripts/backfill-exchange-rates.py --days 30
```

**Benefits**:
- Faster testing (don't wait 30 days for data)
- Better index calculations from day 1
- More realistic signal realization checks

---

### 5. **Add Health Check Dashboard** (PRIORITY 5)

**Create a simple status page showing pipeline health.**

**Proposed Features**:
- Last successful run timestamp
- Which steps succeeded/failed
- Data freshness (hours since last update)
- Source availability (RSS feeds up/down)
- Alert if Step 4 has pending analyses

**Implementation**: Simple JSON file updated by pipeline, displayed on dashboard.

---

## Summary of Recommendations

| Priority | Issue | Solution | Effort | Impact |
|----------|-------|----------|--------|--------|
| **P1** | Step 4 manual intervention | Add Anthropic API | 2-3 hours | High - enables automation |
| **P2** | RSS feed blocking | Add User-Agent headers | 30 mins | Medium - 3x more articles |
| **P3** | No orchestration script | Create run-full-pipeline.py | 1 hour | Medium - easier operation |
| **P4** | Single day of data | Add backfill script | 2 hours | Low - nice to have |
| **P5** | No health monitoring | Add status dashboard | 3 hours | Low - operational visibility |

---

## Pipeline Success Metrics

**Current Run (2026-02-24)**:

| Metric | Value | Status |
|--------|-------|--------|
| Exchange rates fetched | 121 pairs | ✅ Excellent |
| News articles | 34 | ⚠️ Could be 100+ |
| Horizon analyses | 0 | ❌ Blocked |
| Sentiment signals | 34 | ✅ Good |
| Strategies executed | 9 | ✅ Complete |
| Trades executed | 0 | ✅ Expected |
| Total records | 113 | ✅ Good |
| Pipeline duration | ~12s | ✅ Fast |

---

## Deployment Status

✅ **Dashboard deployed**: https://michaeldowd2.github.io/nanopages/fx-dashboard/

**Files deployed**:
- step1_exchange_rates.csv (121 pairs)
- step2_indices.csv (11 indices)
- step3_news.csv (34 articles)
- step4_horizons.csv (0 analyses - empty but present)
- step5_signals.csv (34 signals)
- step6_realization.csv (34 checks)
- step7_strategies.csv (9 strategies)
- tracking_2026-02-24.json (run log)
- system_config.json (preserved)

---

## Next Steps

### Immediate (This Session)
1. ✅ Pipeline executed successfully
2. ✅ Dashboard deployed
3. ✅ Issues documented

### Short-term (Next 1-2 days)
1. Implement Anthropic API integration (Priority 1)
2. Fix RSS feed blocking (Priority 2)
3. Test with 2-3 days of accumulated data

### Medium-term (Next week)
1. Create orchestration script
2. Add backfill capability
3. Monitor signal realization as data matures

### Long-term (Next month)
1. Add health monitoring
2. Optimize strategy parameters
3. Evaluate trading performance

---

**Document Version**: 1.0
**Last Updated**: 2026-02-24
**Author**: nano (AI assistant)
