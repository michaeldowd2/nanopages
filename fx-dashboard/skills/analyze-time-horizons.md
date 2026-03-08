# Skill: analyze-time-horizons

Analyze news articles to estimate time horizons using Claude Haiku.

---

## Purpose

Determine how long each article's market impact will last (immediate, short-term, medium-term, longer-term). Uses LLM analysis to classify articles based on event type, temporal keywords, and market impact patterns.

**Implementation Date**: 2026-02-24

---

## Quick Start

```bash
cd /workspace/group/fx-portfolio
python3 scripts/analyze-time-horizons-llm.py
```

**Output**: `/data/article-analysis/{url_hash}.json`

---

## Time Horizon Categories

The system uses 5 time horizons based on market impact duration:

| Horizon | Days | Description | Use Cases |
|---------|------|-------------|-----------|
| **1day** | 1 | Immediate/Intraday impact | Flash data, intraday moves, breaking news |
| **3day** | 3 | Short-term (2-3 days) | GDP releases, employment data, inflation reports |
| **1week** | 7 | Near-term (1 week) | Central bank meetings, policy decisions |
| **2week** | 14 | Medium-term (2 weeks) | Trade negotiations, geopolitical developments |
| **1month** | 30 | Longer-term (up to 1 month) | Structural changes, regulatory shifts, trends |

**Note**: Articles with horizons longer than 1 month are intentionally ignored as they have less relevance for FX trading strategies.

---

## LLM Configuration

**Estimator**: `claude-haiku-horizon-v1.0`
**Type**: `llm-horizon-analysis`

**Parameters**:
```json
{
  "model": "claude-3-haiku-20240307",
  "max_tokens": 500,
  "temperature": 0.3,
  "horizons": ["1day", "3day", "1week", "2week", "1month"]
}
```

**Why Claude Haiku?**
- Cost-effective for batch processing
- Fast response times (important for daily runs)
- Sufficient accuracy for temporal classification
- Lower cost than Sonnet/Opus for this task

---

## LLM Prompt Design

The prompt guides Claude Haiku using multiple temporal signals:

### Event Type Indicators
- **IMMEDIATE (1day)**: Intraday moves, immediate reactions, "today", "now", breaking news, flash data
- **SHORT-TERM (3day)**: "this week", GDP releases, employment data, inflation reports
- **NEAR-TERM (1week)**: Central bank meetings, policy decisions, "next week"
- **MEDIUM-TERM (2week)**: Trade negotiations, geopolitical developments, "coming weeks"
- **LONGER-TERM (1month)**: Structural changes, regulatory shifts, "next month", trends

### Market Impact Patterns
- Price action mentions → immediate (1day)
- Economic data releases → 3day to 1week
- Central bank policy → 1week to 2week
- Geopolitical events → 2week to 1month
- Structural trends → 1month

### Temporal Keywords
- "Intraday", "today", "session" → 1day
- "This week", "upcoming" → 3day
- "Next week", "near-term" → 1week
- "Coming weeks", "medium-term" → 2week
- "Next month", "longer-term", "trend" → 1month

---

## Output Format

Each analyzed article is saved to `/data/article-analysis/{url_hash}.json`:

```json
{
  "estimator_id": "claude-haiku-horizon-v1.0",
  "estimator_type": "llm-horizon-analysis",
  "estimator_params": {
    "model": "claude-3-haiku-20240307",
    "max_tokens": 500,
    "temperature": 0.3
  },
  "url": "https://...",
  "currency": "EUR",
  "title": "Bank of England: Cuts on the table",
  "published_at": "2026-02-24T10:30:00Z",
  "analyzed_at": "2026-02-24T22:05:00Z",
  "time_horizon": "1week",
  "horizon_category": "Near-term (1 week)",
  "confidence": 0.80,
  "reasoning": "The article mentions the Bank of England's upcoming policy decision, suggesting a near-term impact on the GBP."
}
```

**LLM Response Format**:
```json
{
  "time_horizon": "1week",
  "confidence": 0.80,
  "reasoning": "Brief explanation..."
}
```

**Confidence Scoring**:
- High (0.7-1.0): Clear temporal signals in article
- Medium (0.4-0.6): Some temporal indicators present
- Low (0.0-0.3): Weak or ambiguous signals

**Fallback Behavior**:
- If JSON parsing fails → defaults to `1week` with 0.3 confidence
- If invalid horizon returned → defaults to `1week` with 0.3 confidence

---

## API Usage & Costs

### Environment Setup

**Location**: `/workspace/project/.env`
```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Loading**: Uses centralized `env_loader.py`
```python
from env_loader import get_anthropic_key
api_key = get_anthropic_key()
```

### Cost Analysis (Claude Haiku)

**Pricing** (as of Feb 2024):
- Input: $0.25 per million tokens
- Output: $1.25 per million tokens

**Per Article**:
- Average prompt: ~800 tokens input
- Average response: ~100 tokens output
- Cost per article: ~$0.0003 (0.03 cents)

**Daily Cost**:
- 40 articles/day × $0.0003 = **$0.012/day**
- Monthly: **$0.36/month**

**Very cost-effective!**

---

## Daily Workflow

```bash
cd /workspace/group/fx-portfolio
python3 scripts/analyze-time-horizons-llm.py
```

**Output**:
```
============================================================
Time Horizon Analysis with Claude Haiku
============================================================
✓ API key loaded

Status:
  Total articles: 45
  Already analyzed: 38
  Pending analysis: 7

📊 Analyzing 38 articles...
   Estimator: claude-haiku-horizon-v1.0
   Model: claude-3-haiku-20240307

[1/38] Bank of England: Cuts on the table...
   Currency: GBP, Source: FXStreet
   ✓ Horizon: 1week (confidence: 0.80)
     The article mentions the Bank of England's upcoming policy...

...

============================================================
Analysis Complete
============================================================
✓ Analyzed: 38

Horizon Distribution:
  1day     ( 1 days):   4 articles ( 10.5%)
  3day     ( 3 days):   8 articles ( 21.1%)
  1week    ( 7 days):  18 articles ( 47.4%)
  2week    (14 days):   5 articles ( 13.2%)
  1month   (30 days):   3 articles (  7.9%)
```

---

## Analysis Quality

### Sample Results

**Example 1 - 1week horizon (high confidence)**:
```
Title: "Bank of England: Cuts on the table, conviction still building"
Currency: GBP
Horizon: 1week
Confidence: 0.80
Reasoning: "The article mentions the Bank of England's upcoming policy
decision, suggesting a near-term impact on the GBP."
```

**Example 2 - 3day horizon (high confidence)**:
```
Title: "USD/CAD steadies as stronger US Dollar pressures Loonie"
Currency: USD
Horizon: 3day
Confidence: 0.80
Reasoning: "The article mentions immediate intraday price action, but
also references the US Dollar's broader performance this week."
```

### Distribution Analysis

The 1week horizon dominance (47.4%) makes sense because:
- Central bank meetings are weekly/biweekly events
- Economic data releases typically have 3-7 day impact windows
- FX news aggregators focus on near-term trading opportunities
- Technical analysis often uses weekly timeframes

---

## Data Storage

**Tracking**:
- `analyzed_urls.json`: List of all analyzed URLs (prevents re-analysis)
- Hash-based filenames: MD5 hash of URL (12 chars)

**Stateful Processing**:
- Only analyzes new articles (tracks analyzed URLs)
- Incremental updates to analysis database
- No re-processing of old articles

---

## Dependencies

- **Step 3**: Requires news articles
- **Environment**: ANTHROPIC_API_KEY in .env file

---

## Next Steps

After analyzing articles:
```bash
# Step 5: Generate sentiment signals
python3 scripts/generate-sentiment-signals.py

# Or run full pipeline
```

---

## Debugging

Check CSV export:
```bash
python3 scripts/export-pipeline-data.py
cat data/exports/step4_horizons.csv
```

Check status:
```bash
python3 scripts/analyze-time-horizons-llm.py
```

Count analyzed articles:
```bash
python3 -c "import json; print(len(json.load(open('/workspace/group/fx-portfolio/data/article-analysis/analyzed_urls.json'))))"
```

---

## Troubleshooting

### Issue: "Anthropic API key not found"

**Symptoms**:
```
❌ Anthropic API key not found!
   Set ANTHROPIC_API_KEY in /workspace/project/.env
```

**Solution**:
1. Check if .env file exists:
   ```bash
   ls -la /workspace/project/.env
   ```

2. Check if key is in the file:
   ```bash
   grep ANTHROPIC_API_KEY /workspace/project/.env
   ```

3. If missing, add it:
   ```bash
   echo "ANTHROPIC_API_KEY=sk-ant-api03-..." >> /workspace/project/.env
   ```

### Issue: JSON parsing errors

**Symptoms**:
```
⚠️ Failed to parse LLM response: ...
```

**Cause**: LLM returned malformed JSON or wrapped in markdown

**Solution**:
- Script has built-in regex to extract JSON from markdown
- Fallback to default (1week, confidence 0.3)
- Logged to pipeline logs for review

### Issue: Invalid horizon returned

**Symptoms**:
```
ValueError: Invalid horizon: 2months
```

**Cause**: LLM returned horizon not in allowed list

**Solution**:
- Script validates horizons against TIME_HORIZONS dict
- Fallback to default (1week, confidence 0.3)
- Consider updating prompt to clarify allowed values

---

## Realization Checking (Future Enhancement)

**Not yet implemented** - Phase 2 feature.

After articles are analyzed for time horizon, a second process will:

1. Calculate time elapsed since publication
2. Load currency index data for the elapsed period
3. Calculate actual movement (direction + magnitude)
4. Compare actual vs predicted
5. Mark article as:
   - `too_early` - prediction horizon not reached yet
   - `unrealized` - horizon reached but prediction hasn't materialized
   - `realized` - prediction came true (direction matched)
   - `contradicted` - opposite direction occurred

Only `too_early` and `unrealized` articles should be included in signal generation.

---

## Time-Decay Weighting (Future Enhancement)

**Not yet implemented** - Phase 3 feature.

Once realization status is determined, apply time-decay weights:

### Short-term articles (< 3 days)
- Exponential decay: `weight = 0.5 ^ (days_elapsed / 1.0)`
- 50% weight after 1 day
- Rationale: Short-term views become stale quickly

### Medium-term articles (3-14 days)
- Linear decay: `weight = 1.0 - (days_elapsed / horizon_days)`
- Gradual decline over prediction period
- Rationale: Medium-term views relevant for their stated horizon

### Long-term articles (> 14 days)
- Slow decay: `weight = 0.5 ^ (days_elapsed / 14.0)`
- 50% weight after 2 weeks
- Rationale: Macro views stay relevant longer

---

## Future Improvements

### 1. Anthropic API Integration (Already Implemented)

Current implementation uses Claude Haiku via Anthropic API:
- Standalone script, no orchestrator needed
- Schedulable via cron
- Repeatable and testable
- Cost: ~$0.25 per 1M tokens = ~$0.0001 per article
- Estimated cost: 60 articles/day × $0.0003 = $0.018/day = $6.57/year

### 2. Batch Processing
Process multiple articles in single API call to reduce latency and cost:
- Group 5-10 articles per request
- Parse JSON array response
- Reduce API calls by 5-10x

### 3. Caching & Incremental Updates
- Only analyze new articles (already implemented via `analyzed_urls.json`)
- Re-analyze if article content changes
- Periodic cleanup of old analyses (>30 days)

### 4. Enhanced Prediction Extraction
- Detect multiple timeframes in single article
- Extract target levels ("USD expected to reach 1.20")
- Identify conditional predictions ("if Fed cuts, USD will weaken")

### 5. Source Reliability Scoring
- Track accuracy of predictions by source domain
- Weight high-accuracy sources more heavily
- Downweight sources with poor prediction track record

---

## Notes

- Fully automated LLM-based analysis
- Progress tracked in `analyzed_urls.json`
- Only needs to run once per new article
- Rerunning is safe (won't duplicate analyses)
- Processing time: ~2 minutes for 40 articles
- Average confidence: 0.76 (high confidence)
