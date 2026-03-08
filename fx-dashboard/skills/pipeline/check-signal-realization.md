# Skill: check-signal-realization

Check if signal predictions have been realized by comparing against actual currency movements.

## Purpose

Tag each signal with `realized: true/false` by comparing predicted movements against actual index changes since article publication.

---

## Quick Start

```bash
cd /workspace/group/fx-portfolio
python3 scripts/pipeline/check-signal-realization.py
```

---

## Expected Output

### Output Files

**Primary Output**: Updates existing signal files in-place at `/data/signals/{CURRENCY}/{date}.json`
- Format: JSON (modified)
- Updated: Realization fields added to each signal
- Size: Minimal increase (adds ~200 bytes per signal)

**CSV Export**: `/data/exports/step6_realization.csv`
- Format: CSV for dashboard visualization
- Contains all signals with realization status

### Output Schema

New fields added to each signal:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| realized | boolean | Whether signal was realized | false |
| realization_status | string | Status category | unrealized |
| actual_movement.direction | string | Actual currency direction | bullish |
| actual_movement.magnitude | string | Actual movement size | +0.3% |
| actual_movement.pct_change | float | Percentage change | 0.3 |
| actual_movement.days_elapsed | integer | Days since publication | 2 |
| actual_movement.horizon_days | integer | Prediction horizon in days | 7 |
| actual_movement.start_index | float | Index at publication | 100.0 |
| actual_movement.end_index | float | Current index | 100.3 |
| realization_check_timestamp | string | When check was performed (ISO) | 2026-02-23T10:00:00Z |

### Sample Output

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

### Realization Status Values

- **realized**: Prediction came true (direction matches, magnitude sufficient)
- **unrealized**: Prediction hasn't materialized yet
- **too_early**: Less than 25% of time horizon elapsed
- **partially_realized**: Direction matches but magnitude insufficient
- **contradicted**: Opposite direction occurred
- **no_price_data**: Need more index history
- **insufficient_data**: Missing prediction or horizon data

### Interpretation

- **realized = false**: Signal still active, should be included in aggregate-signals
- **realized = true**: Signal completed, excluded from aggregation
- **days_elapsed/horizon_days**: Progress toward horizon (e.g., 2/7 = day 2 of 7-day prediction)
- **Use this data to**: Apply penalty factors in aggregate-signals based on generator accuracy

---

## How It Works

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

- **calculate-currency-indices**: Requires currency indices with sufficient history (7-14 days minimum)
- **generate-sentiment-signals**: Requires signals with predictions

## Next Steps

After running this step:
- Signals are ready for aggregate-signals (strategies)
- Strategies filter `realized: false` signals only

## Debugging

Check CSV export:
```bash
python3 scripts/utilities/export-pipeline-data.py
cat data/exports/step6_realization.csv
```

Check status summary:
```bash
python3 scripts/pipeline/check-signal-realization.py | grep "Realization Status:" -A 10
```

## Current Limitation

**Need more price history**: Most signals show `no_price_data` because we only have 1 day of index history. After running Steps 1-2 daily for 7-14 days, realization checking will work properly.

## Notes

- Runs daily after generate-sentiment-signals
- Updates signals in-place (modifies generate-sentiment-signals output files)
- Safe to rerun (recalculates based on latest index data)
- Future: Add volatility adjustment, statistical significance testing
