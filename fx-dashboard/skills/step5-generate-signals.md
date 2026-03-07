# Skill: step5-generate-signals

Generate sentiment signals with predicted currency movements.

## Purpose

Analyze news articles to create signals with directional predictions. Each article generates one signal per currency it's relevant to.

## Running This Step

```bash
cd /workspace/group/fx-portfolio
python3 scripts/generate-sentiment-signals.py
```

## Output

**Files**: `/data/signals/{CURRENCY}/{date}.json`

```json
{
  "currency": "USD",
  "date": "2026-02-21",
  "signals": [
    {
      "signal_id": "news-sentiment-abc12345",
      "signal_type": "news-sentiment",
      "currency": "USD",
      "predicted_direction": "bullish",
      "predicted_magnitude": "unclear",
      "confidence": 0.75,
      "horizon_estimator": "llm-horizon-estimator-v1",
      "time_horizon": "1w",
      "article_url": "https://...",
      "article_title": "Fed signals hawkish shift",
      "published_at": "2026-02-21T09:00:00Z",
      "relevance_score": 0.85,
      "reasoning": "Fed hawkish shift supports USD strength",
      "timestamp": "2026-02-21T13:14:53Z"
    }
  ]
}
```

## Signal Schema

- `signal_id`: Unique identifier per signal
- `predicted_direction`: bullish/bearish/neutral
- `predicted_magnitude`: Estimated move (e.g., "0.5%") or "unclear"
- `confidence`: 0-1 score of prediction strength
- `time_horizon`: Links to horizon analyzer output
- `horizon_estimator`: Which estimator was used (can be null if article not analyzed)

## Current Implementation

**news-sentiment** (keyword-based):
- Counts bullish vs bearish keywords in article text
- Simple but fast
- Always returns `predicted_magnitude: "unclear"`
- Multiple parallel implementations possible (future)

## Dependencies

- **Step 3**: Requires news articles
- **Step 4**: Optional (uses horizon if available, otherwise `time_horizon: "unclear"`)

## Next Steps

After running this step, run Step 6 to check signal realization.

## Debugging

Check CSV export:
```bash
python3 scripts/export-pipeline-data.py
cat data/exports/step5_signals.csv
```

Count signals per currency:
```bash
python3 -c "
import json, glob
for f in glob.glob('data/signals/*/*.json'):
    data = json.load(open(f))
    print(f\"{data['currency']}: {len(data['signals'])} signals\")
"
```

## Future Improvements

See `/skills/generate-sentiment-signals.md` for full enhancement roadmap:
- LLM-based sentiment analysis (higher accuracy)
- Central bank statement parsing
- Geopolitical event detection
- Magnitude estimation improvements

## Notes

- Runs daily after Step 3 (and optionally Step 4)
- Creates one signal per article per currency
- Rerunning overwrites previous day's signals
- Safe to rerun for debugging
