# Skill: step3-aggregate-news

Aggregate FX news from RSS feeds and web sources.

## Purpose

Fetch and filter news articles relevant to each currency. Extracts publication timestamps and deduplicates globally.

## Running This Step

```bash
cd /workspace/group/fx-portfolio
python3 scripts/fetch-news.py
```

## Output

**Files**:
- `/data/news/{CURRENCY}/{date}.json` - Articles per currency per day
- `/data/news/url_index.json` - Global URL deduplication index

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
      "currency": "USD"
    }
  ],
  "combined_text": "All snippets concatenated..."
}
```

## Features

- **30-day retention**: Articles older than 30 days automatically filtered and cleaned
- **Global URL deduplication**: Each URL tracked in `url_index.json` - same article never downloaded twice
- **Date key assignment**: New articles get assigned the date they were FIRST SEEN (the date the script runs)
- **Relevance scoring**: Keywords match per currency (0-1 score)
- **Publication timestamps**: Extracted from RSS `<pubDate>` tags (used for 30-day filtering only)

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

## Dependencies

- None (independent data source)

## Next Steps

After running this step, run Step 4 to analyze time horizons.

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

## Sources

See `/skills/aggregate-news.md` for full source list and improvement suggestions.

Current working sources:
- ForexLive RSS
- FXStreet RSS

## Notes

- Runs daily
- RSS feeds may have limited history (typically last 24-48 hours)
- Reddit RSS blocked (403 errors)
- DailyFX RSS blocked (403 errors)
