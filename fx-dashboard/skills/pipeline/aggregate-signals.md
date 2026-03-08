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
python3 scripts/pipeline/aggregate-signals.py --date 2026-03-08
```

**Input**: `/data/signals/{CURRENCY}/{date}.json` (from generate-sentiment-signals)
**Output**: `/data/aggregated-signals/aggregated_signals.csv`

---

## Expected Output

### Output Files

**Primary Output**: `/data/aggregated-signals/aggregated_signals.csv`
- Format: CSV
- Updated: Appended daily
- Size: ~1-2 KB per day

### Output Schema

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| date | string | Trading date (YYYY-MM-DD) | 2026-03-08 |
| currency | string | ISO currency code | USD |
| aggregated_signal | float | Net signal strength (-1 to +1) | 0.45 |
| signal_count | integer | Number of signals aggregated | 3 |
| avg_penalty | float | Average penalty factor applied (0-1) | 0.85 |

### Sample Output

```csv
date,currency,aggregated_signal,signal_count,avg_penalty
2026-03-08,USD,0.45,3,0.85
2026-03-08,GBP,-0.23,2,0.90
2026-03-08,JPY,0.67,4,0.75
```

### Interpretation

- **aggregated_signal**: Positive values indicate bullish sentiment, negative values indicate bearish sentiment
- **signal_count**: More signals = more news coverage and potentially more reliable aggregate
- **avg_penalty**: Lower penalty means historically more accurate signals (1.0 = no penalty, 0.5 = heavily penalized)
- **Typical range**: -1.0 to +1.0 (most values fall between -0.8 and +0.8)
- **Use this data to**: Feed into calculate-trades for trade pair generation

---

## How It Works

### 1. Load All Signals for Date

Reads all signals generated in generate-sentiment-signals across all currencies and all generators.

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

No configuration needed - reads from generate-sentiment-signals and check-signal-realization outputs automatically.

---

## Dependencies

**Upstream Steps**:
- generate-sentiment-signals: `generate-sentiment-signals.py` (provides signals)
- check-signal-realization: `check-signal-realization.py` (provides penalty factors)

**Data Required**:
- `/data/signals/{currency}/{date}.json`
- `/data/signal-realization/{date}.json`

---

## Troubleshooting

**"No signals found for date"**:
- Run generate-sentiment-signals first to generate signals
- Check that signal files exist in `/data/signals/`

**"All signals filtered out"**:
- Check check-signal-realization output - signals may all be realized/contradicted
- Verify realization check is working correctly

**Aggregated signal seems wrong**:
- Check penalty factors in check-signal-realization output
- Verify signal filtering logic (only unrealized signals)
- Review individual signals in generate-sentiment-signals output

---

## Next Steps

After running this step:
- **calculate-trades**: Calculate trade recommendations from aggregated signals
- Review aggregated signals in dashboard
