# Skill: aggregate-news

Collect and filter FX-related news articles from multiple sources, storing them in clean JSON format for sentiment analysis.

## Purpose

Fetches news from RSS feeds and other web sources, filters articles by currency relevance, and stores them in daily JSON files. Each currency gets its own file with clean, deduplicated content ready for LLM-based sentiment analysis.

## File Structure

```
/workspace/group/fx-portfolio/data/news/
  sources.json          # List of RSS feeds and sources
  USD/
    2026-02-20.json     # Daily news for USD
    2026-02-21.json
    ...
  GBP/
    2026-02-20.json
    ...
```

## Data Schema

Each daily JSON file contains:

```json
{
  "currency": "USD",
  "date": "2026-02-20",
  "articles": [
    {
      "title": "Fed signals rate cuts...",
      "url": "https://...",
      "snippet": "Clean text, HTML stripped, ~200 words max",
      "published": "Fri, 20 Feb 2026 13:30:13 GMT",
      "relevance_score": 0.85,
      "currency": "USD"
    }
  ],
  "combined_text": "All snippets concatenated for LLM analysis"
}
```

## Sources Configuration

Edit `/workspace/group/fx-portfolio/data/news/sources.json`:

```json
{
  "rss_feeds": [
    "https://www.forexlive.com/feed/news",
    "https://www.fxstreet.com/rss/news"
  ],
  "reddit_rss": [
    "https://www.reddit.com/r/forex/.rss"
  ]
}
```

**Note:** Reddit RSS requires special handling (403 errors common). Focus on RSS feeds that work without authentication.

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

## Relevance Filtering

Articles are scored 0-1 based on keyword matching:

**Currency keywords:**
- USD: "dollar", "usd", "federal reserve", "fed", "powell", etc.
- GBP: "pound", "gbp", "sterling", "bank of england", etc.
- JPY: "yen", "jpy", "bank of japan", "boj", etc.
- (see script for full list)

Minimum score: **0.3** (at least 1 keyword match)

## Running the Aggregator

```bash
cd /workspace/group/fx-portfolio
python3 scripts/fetch-news.py
```

**Output:**
```
USD: 22 new relevant articles (total: 22)
GBP: 6 new relevant articles (total: 6)
JPY: 7 new relevant articles (total: 7)
...
```

## Deduplication

Articles are deduplicated by URL within each daily file. Running the script multiple times on the same day will:
- Add new articles found
- Skip articles already in the file
- Update the `combined_text` field

## Storage Management

**Retention:** Keep last 30 days of news per currency

**Cleanup script** (to be scheduled):
```bash
find /workspace/group/fx-portfolio/data/news -name "*.json" -mtime +30 -delete
```

**Estimated storage:** ~16MB for 11 currencies × 30 days × 50KB/file

## Improvements

Future enhancements:
1. **More sources:** Add FX blogs, Twitter/X feeds, economic calendars
2. **LLM relevance scoring:** Replace keyword matching with LLM-based relevance scoring for better accuracy
3. **Geopolitical events:** Add specialized scrapers for central bank statements, trade announcements
4. **Sentiment pre-processing:** Extract sentiment scores during aggregation to reduce downstream processing

## Integration with Sentiment Signals

Sentiment signal generators should:
1. Read the daily JSON file for their target currency
2. Use the `combined_text` field for LLM analysis
3. Optionally inspect individual articles for source-weighted scoring
4. Generate signals with confidence scores based on article relevance scores

## Scheduling

For daily orchestrator (09:00 GMT):
```bash
# Step 1 in orchestrator: Fetch news
python3 /workspace/group/fx-portfolio/scripts/fetch-news.py

# Step 2: Wait for sentiment generators to process
```

## Troubleshooting

**403 Errors on RSS feeds:**
- Some sites block automated requests
- Add `User-Agent` header (already implemented)
- For persistent issues, remove URL from sources.json

**No articles for a currency:**
- Check keyword list - might need more/better keywords
- Lower minimum relevance score (currently 0.3)
- Add more RSS feeds focused on that currency/region

**Storage growing too large:**
- Run cleanup script more frequently
- Reduce snippet length (currently 500 chars)
- Increase minimum relevance score to filter more aggressively
