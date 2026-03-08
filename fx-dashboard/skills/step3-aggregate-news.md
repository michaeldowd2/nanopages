# Skill: step3-aggregate-news

Aggregate FX news from RSS feeds and NewsAPI.

---

## Purpose

Fetch and filter news articles relevant to each currency from multiple sources. Extracts publication timestamps and deduplicates globally.

**Implementation Date**: NewsAPI integration added 2026-02-24

---

## Quick Start

```bash
cd /workspace/group/fx-portfolio
python3 scripts/fetch-news.py
```

**Output**:
- `/data/news/{CURRENCY}/{date}.json` - Articles per currency per day
- `/data/news/url_index.json` - Global URL deduplication index

---

## Data Sources

### RSS Feeds

**Active Sources**:
- **FXStreet**: 30 articles, 73% pass rate
- **ForexLive**: 25 articles, 52% pass rate
- **Yahoo Finance**: 42 articles, 2% pass rate (low quality)
- **MarketWatch**: 10 articles, 0% pass rate (low quality)

### Comprehensive Source List

**Currently Working:**
- ✅ ForexLive (https://www.forexlive.com/feed/news) - Real-time FX news, majors focus
- ✅ FXStreet (https://www.fxstreet.com/rss/news) - Analysis, forecasts, technical views

**Blocked / Authentication Required:**
- ❌ Reddit r/forex, r/economics - 403 errors (need workaround)
- ❌ DailyFX (https://www.dailyfx.com/feeds/market-news) - 403 Forbidden
- ❌ Bloomberg, Reuters - Paywalled, no free RSS

**To Try / Add:**
- 📰 **Investing.com** - https://www.investing.com/rss/news.rss (general markets)
- 📰 **MarketWatch** - https://www.marketwatch.com/rss/ (US markets focus)
- 📰 **Financial Times** - https://www.ft.com/rss/home/uk (limited free access)
- 📰 **CNBC** - https://www.cnbc.com/id/100727362/device/rss/rss.html (markets feed)
- 📰 **Forex Factory** - Check if RSS available
- 📰 **BabyPips** - https://www.babypips.com/news/feed (FX education/news)
- 📰 **Action Forex** - http://www.actionforex.com/rss/ (if still active)

**Currency-Specific Sources:**
- 🇺🇸 **Federal Reserve** - https://www.federalreserve.gov/feeds/press_all.xml
- 🇬🇧 **Bank of England** - https://www.bankofengland.co.uk/news (check for RSS)
- 🇯🇵 **Bank of Japan** - https://www.boj.or.jp/en/rss/ (English announcements)
- 🇨🇭 **SNB** - https://www.snb.ch/en/publications/communication (manual check)
- 🇪🇺 **ECB** - https://www.ecb.europa.eu/rss/ (press releases)
- 🇦🇺 **RBA** - https://www.rba.gov.au/rss-feeds/ (monetary policy)
- 🇨🇦 **Bank of Canada** - https://www.bankofcanada.ca/rss-feeds/
- 🇨🇳 **PBOC** - http://www.pbc.gov.cn/en/3688006/index.html (check for RSS)

**Alternative Approaches for Reddit/Blogs:**
- Use Reddit API with authentication (requires API key)
- Scrape Reddit via web search (e.g., search "site:reddit.com/r/forex JPY" daily)
- Monitor Twitter/X accounts of FX analysts (requires X API)
- Parse economist blogs manually (add URLs to sources as discovered)

**Recommended Next Sources to Add:**
1. Central bank RSS feeds (Federal Reserve, ECB, BoJ) - high quality, official
2. Investing.com RSS - broad coverage including EM currencies
3. MarketWatch - US market focus, good for USD
4. Consider using web search API to find Reddit threads (Google Custom Search API)

**Finding New Sources:**
When you discover a new valuable source, add it to this list with:
- URL and format (RSS/web/API)
- What it covers (currency focus, quality, frequency)
- Any access restrictions

### NewsAPI Integration

**Status**: Fully integrated and working

**Configuration** (in `data/news/sources.json`):
```json
{
  "newsapi_enabled": true,
  "newsapi_queries": [
    "forex",
    "currency exchange"
  ],
  "newsapi_max_results_per_query": 20
}
```

**Current Usage**: 2 API requests per run (well under 100/day limit)

**Results**:
- Query "forex": 20 articles
- Query "currency exchange": 19 articles
- Total: 39 articles fetched
- After filtering: 7 articles saved (18% pass rate)

**Sources Found**:
- The Times of India (3 articles)
- Financial Post (2 articles)
- CNA (Channel NewsAsia) (1 article)
- GlobeNewswire (1 article)

---

## Complete Source Breakdown

| Source | Articles Fetched | Articles Saved | Pass Rate |
|--------|------------------|----------------|-----------|
| **FXStreet** | 30 | 22 | 73% |
| **ForexLive** | 25 | 13 | 52% |
| **NewsAPI (combined)** | 39 | 7 | 18% |
| **Yahoo Finance** | 42 | 1 | 2% |
| **MarketWatch** | 10 | 0 | 0% |
| **TOTAL** | **146** | **43** | **29.5%** |

**Note**: NewsAPI's lower pass rate is expected - it returns general financial news from global sources, not FX-specific content. However, it adds geographic diversity (Asian, North American, European perspectives).

---

## Environment Configuration

### NewsAPI Setup

**Location**: `/workspace/project/.env`
```
NEWSAPI_APIKEY=<your-newsapi-key-here>
```

**Loading**: Automatic via built-in .env loader
```python
def load_env_file():
    """Load environment variables from .env file"""
    env_paths = [
        '/workspace/project/.env',
        '/workspace/group/.env',
        os.path.join(os.path.dirname(__file__), '../.env')
    ]
    # Loads first .env found
```

**Lookup order**:
1. `NEWSAPI_APIKEY` environment variable
2. `newsapi_apikey` environment variable (fallback)
3. If neither found, script gracefully degrades (RSS only)

---

## API Usage & Rate Limits

### NewsAPI Free Tier
- **Daily limit**: 100 requests
- **Current usage**: 2 requests per run
- **Safe frequency**: Can run up to **50 times per day** (hourly with buffer)

### Recommended Schedule

**Hourly execution** (maximum freshness):
```bash
0 * * * * cd /workspace/group/fx-portfolio && python3 scripts/fetch-news.py
```
- API usage: 48 requests/day (52% of limit)
- Safety margin: 52 requests spare

**4 times daily** (conservative):
```bash
0 6,12,18,0 * * * cd /workspace/group/fx-portfolio && python3 scripts/fetch-news.py
```
- API usage: 8 requests/day (8% of limit)
- Safety margin: 92 requests spare

---

## Output Format

### Per-Currency Article File

**Location**: `/data/news/{CURRENCY}/{date}.json`

```json
{
  "currency": "USD",
  "date": "2026-02-21",
  "articles": [
    {
      "title": "Fed signals hawkish shift",
      "url": "https://...",
      "snippet": "Clean text excerpt...",
      "published_at": "2026-02-21T09:00:00Z",
      "relevance_score": 0.85,
      "currency": "USD",
      "source": "FXStreet"
    }
  ],
  "combined_text": "All snippets concatenated..."
}
```

### Source Attribution

Each article now includes a `source` field:
- `"FXStreet"` - From FXStreet RSS feed
- `"ForexLive"` - From ForexLive RSS feed
- `"Yahoo Finance"` - From Yahoo Finance RSS feed
- `"NewsAPI"` - From NewsAPI (query-based)

---

## Features

### 30-Day Retention
Articles older than 30 days automatically filtered and cleaned.

### Global URL Deduplication
Each URL tracked in `url_index.json` - same article never downloaded twice.

### Date Key Assignment
New articles get assigned the date they were FIRST SEEN (the date the script runs).

### Relevance Scoring
Keywords match per currency (0-1 score).

### Publication Timestamps
Extracted from RSS `<pubDate>` tags (used for 30-day filtering only).

---

## How Article Dating Works

When the script runs on a specific date (e.g., 2026-03-01):

1. **Fetches** fresh articles from RSS feeds and NewsAPI
2. **Checks** each URL against the global `url_index.json`
3. **For NEW articles** (never seen before):
   - Saves to file: `/data/news/{CURRENCY}/2026-03-01.json`
   - Adds to URL index with `first_seen_date: "2026-03-01"`
4. **For EXISTING articles** (URL already in index):
   - **Skips completely** - not downloaded or saved again

This ensures:
- Each article appears exactly ONCE across all dates
- The date key represents when we FIRST discovered the article
- Over time, each run adds only genuinely new articles

---

## Quality Analysis

### NewsAPI Article Quality

**Strengths**:
- Global coverage (India, Canada, Singapore, US)
- Diverse perspectives on FX markets
- Real-time breaking news
- Professionally curated sources

**Weaknesses**:
- Lower FX relevance (18% pass rate vs 73% for FXStreet)
- Many articles filtered out due to general financial focus
- Not FX-specific like ForexLive or FXStreet

**Recommendation**: Keep NewsAPI enabled - The 7 additional articles provide geographic diversity and different angles on FX-relevant events.

---

## Dependencies

- None (independent data source)
- Optional: NEWSAPI_APIKEY in .env for NewsAPI integration

---

## Next Steps

After running this step:
```bash
# Step 4: Analyze time horizons
python3 scripts/analyze-time-horizons-llm.py

# Or run full pipeline
```

---

## Debugging

Check CSV export:
```bash
python3 scripts/export-pipeline-data.py
cat data/exports/step3_news.csv
```

Check URL index:
```bash
python3 -c "import json; print(len(json.load(open('/workspace/group/fx-portfolio/data/news/url_index.json'))))"
```

View articles with source attribution:
```bash
cat data/news/USD/$(date +%Y-%m-%d).json | grep -A 2 '"source"'
```

---

## Troubleshooting

### Issue: NewsAPI not fetching articles

**Symptom**: Only RSS articles in output, no NewsAPI articles

**Solution**:
1. Check API key is set:
   ```bash
   grep NEWSAPI_APIKEY /workspace/project/.env
   ```
2. Verify `newsapi_enabled: true` in `data/news/sources.json`
3. Check script output for API errors

### Issue: Low article count

**Symptom**: Fewer articles than expected

**Causes**:
- RSS feeds have limited history (24-48 hours typically)
- Many articles filtered out due to currency relevance threshold
- URL deduplication (articles already seen before)

**Solution**:
- Run more frequently to catch fresh articles
- Consider adding more RSS feeds or NewsAPI queries
- Review relevance scoring threshold

---

## Optimization Ideas

### Add More FX-Specific Queries
```json
"newsapi_queries": [
  "forex",
  "currency exchange",
  "central bank",
  "EUR/USD",
  "GBP/USD"
]
```

**Caveat**: More queries = more API requests (5 queries = 5 requests per run)

### Replace Low-Performing Feeds
Consider replacing Yahoo Finance (2%) and MarketWatch (0%) with:
- Reuters FX feed
- Bloomberg FX feed
- DailyFX feed

---

## Notes

- Runs daily (or more frequently)
- RSS feeds have limited history (typically last 24-48 hours)
- NewsAPI provides real-time breaking news
- Global deduplication prevents duplicate processing
- Source attribution enables quality analysis per source
