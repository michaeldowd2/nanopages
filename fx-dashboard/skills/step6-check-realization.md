# Skill: step6-check-realization

Check if signal predictions have been realized by comparing against actual currency movements.

## Purpose

Tag each signal with `realized: true/false` by comparing predicted movements against actual index changes since article publication.

## Running This Step

```bash
cd /workspace/group/fx-portfolio
python3 scripts/check-signal-realization.py
```

## Output

Updates signal files in-place, adding realization fields:

```json
{
  "signal_id": "news-sentiment-abc12345",
  "currency": "USD",
  "predicted_direction": "bullish",
  "predicted_magnitude": "0.5%",
  "time_horizon": "1w",
  ...
  "realized": false,
  "realization_status": "unrealized",
  "actual_movement": {
    "direction": "bullish",
    "magnitude": "+0.3%",
    "pct_change": 0.3,
    "days_elapsed": 2,
    "horizon_days": 7,
    "start_index": 100.0,
    "end_index": 100.3
  },
  "realization_check_timestamp": "2026-02-23T10:00:00Z"
}
```

## Realization Logic (Moderate Complexity)

For each signal:
1. Calculate days elapsed since publication
2. Load currency index movements for that period
3. Compare predicted vs actual direction
4. Compare predicted vs actual magnitude (if specified)

**Status determination:**
- `realized`: Direction matches AND actual magnitude ≥ 50% of predicted
- `unrealized`: Prediction hasn't materialized yet
- `too_early`: Less than 25% of time horizon elapsed
- `partially_realized`: Direction matches but magnitude insufficient
- `contradicted`: Opposite direction occurred
- `no_price_data`: Need more index history
- `insufficient_data`: Missing prediction or horizon data

## Dependencies

- **Step 2**: Requires currency indices with sufficient history (7-14 days minimum)
- **Step 5**: Requires signals with predictions

## Next Steps

After running this step:
- Signals are ready for Step 7 (strategies)
- Strategies filter `realized: false` signals only

## Debugging

Check CSV export:
```bash
python3 scripts/export-pipeline-data.py
cat data/exports/step6_realization.csv
```

Check status summary:
```bash
python3 scripts/check-signal-realization.py | grep "Realization Status:" -A 10
```

## Current Limitation

**Need more price history**: Most signals show `no_price_data` because we only have 1 day of index history. After running Steps 1-2 daily for 7-14 days, realization checking will work properly.

## Notes

- Runs daily after Step 5
- Updates signals in-place (modifies Step 5 output files)
- Safe to rerun (recalculates based on latest index data)
- Future: Add volatility adjustment, statistical significance testing
