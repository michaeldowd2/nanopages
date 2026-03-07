# Skill: step4-analyze-horizons

Analyze news articles to extract time horizons.

## Purpose

Determine the timeframe each article discusses (hours/days/weeks/months). Does NOT analyze direction or sentiment - that's Step 5's job.

## Running This Step

**Current Implementation**: Orchestrator-based (requires manual LLM analysis)

1. **Check pending articles:**
```bash
cd /workspace/group/fx-portfolio
python3 scripts/analyze-time-horizons.py
```

2. **Analyze articles using LLM** (see `/skills/analyze-article-horizons.md` for full instructions)

3. **Save analysis** for each article

## Output

**Files**: `/data/article-analysis/{url_hash}.json`

```json
{
  "url": "https://...",
  "analyzed_at": "2026-02-21T11:00:00Z",
  "title": "Fed signals dovish shift",
  "published_at": "2026-02-21T09:00:00Z",
  "currency": "USD",
  "estimator": "llm-horizon-estimator-v1",
  "time_horizon": "1w",
  "horizon_category": "medium",
  "confidence": 0.85,
  "reasoning": "References Fed meeting next week"
}
```

## Horizon Categories

- **short**: < 3 days (intraday, tomorrow, next session)
- **medium**: 3-14 days (this week, next week)
- **long**: > 14 days (this month, coming months)

## Dependencies

- **Step 3**: Requires news articles

## Next Steps

After analyzing articles, run Step 5 to generate sentiment signals.

## Debugging

Check CSV export:
```bash
python3 scripts/export-pipeline-data.py
cat data/exports/step4_horizons.csv
```

Check status:
```bash
python3 scripts/analyze-time-horizons.py
```

## Future Improvement

Replace orchestrator with Anthropic API integration for standalone execution:
- Add `ANTHROPIC_API_KEY` to environment
- Script calls Claude Haiku API directly
- Fully automated, no manual intervention needed
- Cost: ~$0.0001 per article = ~$2/year

## Notes

- Currently requires manual orchestrator intervention
- Progress tracked in `analyzed_urls.json`
- Only needs to run once per new article
- Rerunning is safe (won't duplicate analyses)
