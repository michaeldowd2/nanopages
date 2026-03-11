# Skill: fetch-news

Aggregate FX news from RSS feeds and NewsAPI.

---

## Purpose

Fetch and filter news articles relevant to each currency from multiple sources. Extracts publication timestamps and deduplicates globally.

**Implementation Date**: NewsAPI integration added 2026-02-24

---

## Quick Start

```bash
cd /workspace/group/fx-portfolio
python3 scripts/pipeline/fetch-news.py
```

**Output**:
- `/data/news/{date}.csv` - All articles for the date across all currencies (CSV format)
- Cross-date deduplication: Each article URL is downloaded only once across all dates

---

## Expected Output

### Output Files

**Primary Output**: `/data/news/{date}.csv` (one file per date with all currencies)
- Format: CSV
- Updated: Created during each run
- Size: ~20-60 KB per day (all currencies combined)

### Output Schema

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| date | string | Fetch date (YYYY-MM-DD) | 2026-03-11 |
| source | string | News source name | FXStreet |
| url | string | Article URL (unique identifier) | https://... |
| currency | string | Related currency | USD |
| title | string | Article headline | Fed signals hawkish shift |
| snippet | string | Clean text excerpt | Fed signals... |

### Sample Output

```csv
date,source,url,currency,title,snippet
2026-03-11,FXStreet,https://www.fxstreet.com/news/...,USD,Fed signals hawkish shift,The Federal Reserve indicated a more hawkish stance...
2026-03-11,ForexLive,https://www.forexlive.com/...,EUR,ECB holds rates steady,The European Central Bank maintained its key interest rates...
```

### Interpretation

- **url**: Unique identifier for each article - used for deduplication across dates
- **source**: Identifies where article came from (FXStreet, ForexLive, NewsAPI, etc.)
- **Typical article count**: 30-60 articles per day across all currencies
- **Use this data to**: Analyze time horizons and generate sentiment signals

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
0 * * * * cd /workspace/group/fx-portfolio && python3 scripts/pipeline/fetch-news.py
```
- API usage: 48 requests/day (52% of limit)
- Safety margin: 52 requests spare

**4 times daily** (conservative):
```bash
0 6,12,18,0 * * * cd /workspace/group/fx-portfolio && python3 scripts/pipeline/fetch-news.py
```
- API usage: 8 requests/day (8% of limit)
- Safety margin: 92 requests spare

---

## Output Format

### Daily CSV File

**Location**: `/data/news/{date}.csv`

Example: `/data/news/2026-03-11.csv`

```csv
date,source,url,currency,title,snippet
2026-03-11,FXStreet,https://www.fxstreet.com/news/...,USD,Fed signals hawkish shift,The Federal Reserve indicated...
2026-03-11,ForexLive,https://www.forexlive.com/...,EUR,ECB holds rates,The European Central Bank...
2026-03-11,NewsAPI (Reuters),https://reuters.com/...,GBP,Sterling rises on data,The British pound gained...
```

### Source Attribution

Each article includes a `source` field identifying its origin:
- `"FXStreet"` - From FXStreet RSS feed
- `"ForexLive"` - From ForexLive RSS feed
- `"Yahoo Finance"` - From Yahoo Finance RSS feed
- `"NewsAPI (Reuters)"` - From NewsAPI (source name in parentheses)
- `"Investing.com"` - From Investing.com RSS feed
- `"MarketWatch"` - From MarketWatch RSS feed
- `"DailyFX"` - From DailyFX RSS feed

---

## Features

### Cross-Date URL Deduplication
**Critical Feature**: Each article URL is downloaded and processed only once across all dates.

**How it works**:
1. On startup, loads all existing URLs from past 30 days into memory
2. Before saving any article, checks if URL already exists
3. Only NEW URLs are downloaded and saved
4. Prevents re-downloading and re-analyzing the same content

**Benefits**:
- Reduces API costs for downstream LLM processing
- Prevents duplicate sentiment signals
- Ensures each article is analyzed exactly once
- Maintains clean historical dataset

### 30-Day Article Age Filter
Articles older than 30 days (by publication date) are automatically filtered during fetch.

### Relevance Filtering
Articles filtered by currency keywords - each article can appear multiple times (once per relevant currency).

### Publication Timestamps
Extracted from RSS `<pubDate>` tags (used for 30-day age filtering).

---

## How Cross-Date Deduplication Works

When the script runs on a specific date (e.g., 2026-03-11):

1. **Loads existing URLs**: Scans past 30 days of CSV files and loads all URLs into memory
   - Example: Loaded 648 URLs from 16 files
2. **Fetches** fresh articles from RSS feeds and NewsAPI
3. **Filters by currency**: Checks each article for currency keyword relevance
4. **For EACH relevant article**:
   - **If URL is NEW** (not in existing URLs):
     - Saves to file: `/data/news/2026-03-11.csv`
     - Article is tagged with date `2026-03-11`
   - **If URL ALREADY EXISTS** (in any previous date's CSV):
     - **Skips completely** - not downloaded or saved again
     - Prevents duplicate processing

**Example output from a typical run**:
```
✓ Loaded 648 existing URLs from 16 files (past 30 days)
✓ Fetched 85 articles from RSS feeds
✓ Fetched 20 articles from NewsAPI
Deduplication Summary:
  New URLs: 30
  Duplicates skipped: 32
  Total to save: 30
```

**Key guarantees**:
- Each URL appears in exactly ONE date's CSV file
- The date represents when we FIRST discovered the article
- Downstream processes never analyze the same article twice
- Dataset remains clean over time

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
# analyze-time-horizons: Analyze time horizons
python3 scripts/pipeline/analyze-time-horizons.py

# Or run full pipeline
```

---

## Debugging

Check today's news:
```bash
cat data/news/$(date +%Y-%m-%d).csv
```

Count articles per date:
```bash
for f in data/news/*.csv; do echo "$f: $(tail -n +2 "$f" | wc -l) articles"; done
```

Verify no duplicate URLs across all dates:
```python
python3 -c "
import glob, sys
from pathlib import Path
sys.path.append('scripts')
from utilities.csv_helper import read_csv

news_files = sorted(glob.glob('data/news/*.csv'))
all_urls = []
for filepath in news_files:
    date = Path(filepath).stem
    rows = read_csv('3', date=date, validate=False)
    all_urls.extend([row['url'] for row in rows])

print(f'Total articles: {len(all_urls)}')
print(f'Unique URLs: {len(set(all_urls))}')
print(f'Duplicates: {len(all_urls) - len(set(all_urls))}')
"
```

Export to dashboard:
```bash
python3 scripts/deployment/export-pipeline-data.py
head -20 site_data/step3_news.csv
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
2. Verify `newsapi_enabled: true` in `config/news_sources.json`
3. Check script output for API errors

### Issue: Low article count

**Symptom**: Fewer articles than expected

**Causes**:
- RSS feeds have limited history (24-48 hours typically)
- Many articles filtered out due to currency relevance threshold
- **Cross-date deduplication** (articles already downloaded in previous runs)

**Solution**:
- Run more frequently to catch fresh articles before they age out
- Consider adding more RSS feeds or NewsAPI queries
- Review relevance filtering keywords
- **Note**: Low counts are EXPECTED after first run - most articles will be duplicates

**Example**: After initial run, subsequent runs might show:
```
✓ Loaded 648 existing URLs from 16 files
Fetched 105 articles
Duplicates skipped: 75
New articles saved: 30
```

This is normal behavior - the deduplication is working correctly!

### Issue: Duplicate URLs in dataset

**Symptom**: Same URL appears in multiple date files

**Solution**:
Run the cross-date deduplication utility to clean up:
```bash
python3 scripts/utilities/deduplicate-news-cross-dates.py
```

This will:
- Keep first occurrence of each URL
- Remove later occurrences from subsequent dates
- Report how many duplicates were found and removed

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
