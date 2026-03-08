# Skill: aggregate-signals

Aggregate sentiment signals by currency, applying penalty factors for unrealized signals.

---

## Purpose

Takes individual sentiment signals from multiple generators and aggregates them by currency. Applies a penalty factor based on signal realization history to weight signals appropriately.

**Implementation Date**: 2026-03-01

---

## Quick Start

```bash
cd /workspace/group/fx-portfolio
python3 scripts/aggregate-signals.py --date 2026-03-08
```

**Input**: `/data/signals/{CURRENCY}/{date}.json` (from Step 5)
**Output**: `/data/aggregated-signals/aggregated_signals.csv`

---

## How It Works

### 1. Load All Signals for Date

Reads all signals generated in Step 5 across all currencies and all generators.

### 2. Filter by Realization Status

Only includes signals that are:
- **unrealized**: Prediction hasn't happened yet
- **too_early**: Horizon not reached

Excludes:
- **realized**: Already happened
- **contradicted**: Opposite occurred

### 3. Apply Penalty Factor

Adjusts signal strength based on generator's historical accuracy:

```
adjusted_signal = original_signal × penalty_factor
```

**Penalty factors** (from signal realization check):
- High accuracy generator: penalty_factor = 1.0 (no penalty)
- Medium accuracy: penalty_factor = 0.7
- Low accuracy: penalty_factor = 0.5

### 4. Aggregate by Currency

For each currency, sums all adjusted signals:

```
aggregated_signal = Σ(signal × penalty_factor)
```

### 5. Output Format

CSV file with columns:
- `date`: Trading date
- `currency`: Currency code
- `aggregated_signal`: Net signal (-ve = bearish, +ve = bullish)
- `signal_count`: Number of signals aggregated
- `avg_penalty`: Average penalty factor applied

---

## Example Output

```csv
date,currency,aggregated_signal,signal_count,avg_penalty
2026-03-08,USD,0.45,3,0.85
2026-03-08,GBP,-0.23,2,0.90
2026-03-08,JPY,0.67,4,0.75
```

---

## Configuration

No configuration needed - reads from Step 5 and Step 6 outputs automatically.

---

## Dependencies

**Upstream Steps**:
- Step 5: `generate-sentiment-signals-v2.py` (provides signals)
- Step 6: `check-signal-realization.py` (provides penalty factors)

**Data Required**:
- `/data/signals/{currency}/{date}.json`
- `/data/signal-realization/{date}.json`

---

## Troubleshooting

**"No signals found for date"**:
- Run Step 5 first to generate signals
- Check that signal files exist in `/data/signals/`

**"All signals filtered out"**:
- Check Step 6 output - signals may all be realized/contradicted
- Verify realization check is working correctly

**Aggregated signal seems wrong**:
- Check penalty factors in Step 6 output
- Verify signal filtering logic (only unrealized signals)
- Review individual signals in Step 5 output

---

## Next Steps

After running this step:
- **Step 8**: Calculate trade recommendations from aggregated signals
- Review aggregated signals in dashboard
