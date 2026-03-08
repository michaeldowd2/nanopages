# Skill: analyze-article-horizons

Analyze FX news articles to extract time horizons, predicted movements, and determine if predictions have been realized.

## Purpose

This intermediate step between news aggregation and sentiment signal generation performs critical analysis:
1. **Time Horizon Detection**: Determine the timeframe of predictions (hours/days/weeks/months)
2. **Movement Prediction**: Extract predicted direction and magnitude
3. **Realization Check**: Compare predictions against actual currency movements
4. **Filtering**: Exclude stale or already-realized predictions from signal generation

## Architecture

```
fetch-news.py → [articles with timestamps]
    ↓
analyze-article-horizons (THIS SKILL) → [analyzed articles]
    ↓
generate-sentiment-signals.py → [filtered, weighted signals]
```

## Current Implementation (Orchestrator-based)

**⚠️ LIMITATION**: This process currently requires nanoclaw orchestrator intervention.

The orchestrator reads pending articles and uses its LLM capabilities to analyze each one. This is a temporary solution until API integration is built.

### Running the Analysis

1. **Check status:**
```bash
python3 scripts/analyze-time-horizons.py
```

This shows how many articles need analysis.

2. **For each pending article, analyze using LLM prompts:**

Read the article data from the pending list, then for each article, perform this analysis:

**Prompt Template:**
```
Analyze this FX news article and extract ONLY the time horizon:

Title: {article.title}
Snippet: {article.snippet}
Published: {article.published_at}
Currency: {article.currency}

Questions:
1. What is the time horizon of any predictions or analysis in this article?
   - Return as: "2h" (hours), "1d" (days), "1w" (weeks), "1m" (months), or "unclear"
   - If multiple horizons mentioned, pick the most prominent one
   - Examples:
     * "Fed meeting next week" → "1w"
     * "Q1 earnings" → "1m"
     * "today's session" → "1d"
     * "longer term outlook" → "3m"

2. On a scale of 0-1, how confident are you about this time horizon?
   - 1.0 = explicit time reference ("next Tuesday", "in 3 weeks")
   - 0.5 = implied timeframe ("upcoming meeting", "near term")
   - 0.1 = no clear time reference

3. Briefly explain the reasoning (1 sentence)

Return as JSON:
{
  "time_horizon": "1w",
  "horizon_category": "medium",
  "confidence": 0.85,
  "reasoning": "Article discusses Fed policy meeting scheduled for next week"
}
```

**IMPORTANT**: Do NOT analyze direction, magnitude, or sentiment. That's the job of sentiment analyzers (Step 5).

3. **Save each analysis:**

For each analyzed article, call:
```python
from scripts.analyze_time_horizons import save_analysis

save_analysis(article_url, {
    'title': article['title'],
    'published_at': article['published_at'],
    'currency': article['currency'],
    'estimator': 'llm-horizon-estimator-v1',
    'time_horizon': '1w',
    'horizon_category': 'medium',
    'confidence': 0.85,
    'reasoning': 'Article discusses Fed meeting next week'
})
```

## Analysis Schema

### Horizon Categories
- **short**: < 3 days (intraday, tomorrow, next session)
- **medium**: 3-14 days (this week, next week, coming days)
- **long**: > 14 days (this month, coming weeks/months, longer term)

### Time Horizon Format
- `2h`, `6h`, `12h` - hours
- `1d`, `2d`, `3d` - days
- `1w`, `2w` - weeks
- `1m`, `3m`, `6m` - months
- `unclear` - no specific timeline mentioned

### Predicted Direction
- `bullish` - currency expected to strengthen
- `bearish` - currency expected to weaken
- `neutral` - mixed or balanced view
- `unclear` - no clear directional view

### Output Storage

Analysis results are saved to `/workspace/group/fx-portfolio/data/article-analysis/{url_hash}.json`:

```json
{
  "url": "https://example.com/article",
  "analyzed_at": "2026-02-21T11:00:00Z",
  "title": "Fed signals dovish shift",
  "published_at": "2026-02-21T09:00:00Z",
  "currency": "USD",
  "estimator": "llm-horizon-estimator-v1",
  "time_horizon": "1w",
  "horizon_category": "medium",
  "confidence": 0.85,
  "reasoning": "References Fed FOMC meeting scheduled for next week"
}
```

## Realization Checking (Phase 2)

**Not yet implemented** - future enhancement.

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

## Time-Decay Weighting (Phase 3)

**Not yet implemented** - future enhancement.

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

## Future Improvements

### 1. Anthropic API Integration (High Priority)
Replace orchestrator-based analysis with standalone Python script:

```python
import anthropic

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

def analyze_article_with_api(article):
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"Analyze this FX article: {article}"
        }]
    )
    return parse_llm_response(response.content)
```

**Benefits:**
- Standalone script, no orchestrator needed
- Schedulable via cron
- Repeatable and testable
- Cost: ~$0.25 per 1M tokens = ~$0.0001 per article

**Estimated cost:** 60 articles/day × $0.0001 = $0.006/day = $2.20/year

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

## Troubleshooting

**No articles to analyze:**
- Run `fetch-news.py` first to collect articles
- Check URL index exists: `/workspace/group/fx-portfolio/data/news/url_index.json`

**Articles stuck in pending:**
- Orchestrator must manually process via nanoclaw
- Future: API integration will auto-process

**Analysis quality issues:**
- LLM prompt may need tuning for FX-specific language
- Add more context about currency market terminology
- Consider using Claude Opus for critical articles (higher cost but better accuracy)

## Integration with Sentiment Signals

The sentiment signal generator will be updated to:
1. Read analyzed articles instead of raw articles
2. Filter based on realization status
3. Apply time-decay weights
4. Include metadata: `articles_used`, `articles_filtered`, `avg_article_age`, `avg_prediction_confidence`

This ensures signals are based on relevant, timely, unrealized predictions rather than stale or already-realized views.
