# Skill: check-signal-realization

Check if signal predictions have been realized by comparing against actual currency movements.

## Purpose

Process 6 checks if sentiment signals from the past 30 days have been realized by tracking currency index movements. This process **collects signals from previous dates** and checks them against current market data.

---

## Quick Start

```bash
cd /workspace/group/fx-portfolio
python3 scripts/pipeline/check-signal-realization.py --date 2026-03-20
```

---

## How It Works (Key Concept)

**IMPORTANT**: This process does NOT only check signals from the current date. Instead:

1. **Looks back 30 days**: Loads all signals from the past 30 days
2. **Filters by validity**: Only checks signals where `valid_to_date >= processing_date`
3. **Tracks at ANY point**: Checks if the signal was realized at any point since publication (not just currently)
4. **Outputs unrealized signals**: These feed into Process 7 (aggregate-signals)

### Why This Matters

**Even with 0 new articles on a given date**, Process 6 will still generate output because:
- It checks signals from the past 30 days
- Those signals may still be valid (not expired)
- Market movements since their publication are tracked

**Example**: On March 19, 2026:
- 0 new articles fetched
- Process 4 generates empty CSV (0 horizon analyses)
- Process 5 generates empty CSV (0 new signals)
- **Process 6 generates data** - checks ~400+ signals from Feb 17 - Mar 19 that are still valid

---

## Signal Collection Logic

For a given processing date (e.g., 2026-03-20):

```
1. Load signals from past 30 days (2026-02-18 to 2026-03-20)
2. For each signal:
   - Check if valid_to_date >= 2026-03-20 (is it still active?)
   - If YES: Check if realized at any point since article_download_date
   - If NO: Skip (signal expired)
3. Output all valid signals with realization status
```

### Realization Checking (Enhanced Logic)

For each valid signal:

1. **Load index history** from `article_download_date` to `processing_date`
2. **Track min/max index values** during that period
3. **Calculate travel distances**:
   - `greatest_positive_travel` = max_index - start_index
   - `greatest_negative_travel` = min_index - start_index
4. **Check realization**:
   - **Bullish signal**: Realized if `greatest_positive_travel >= estimated_diff`
   - **Bearish signal**: Realized if `greatest_negative_travel <= estimated_diff`

This means a signal is marked as "realized" if the index traveled the estimated distance **at any point**, even if it has since reversed.

---

## Output Schema

**File**: `data/signal-realization/{date}.csv`

### Columns

| Column | Type | Description |
|--------|------|-------------|
| date | string | Realization check date (YYYY-MM-DD) |
| article_id | string | Article hash ID (12-char hex) |
| currency | string | Currency code (USD, EUR, etc.) |
| article_download_date | string | When article was published |
| estimator_id | string | Time horizon estimator ID |
| generator_id | string | Signal generator ID |
| event_id | string | Currency event identifier |
| valid_to_date | string | When signal expires |
| signal | float | Signal strength (-1.0 to +1.0) |
| start_30d_max_diff | float | 30-day range at signal generation |
| estimated_diff | float | Predicted movement (signal × start_30d_max_diff) |
| start_index | float | Index at signal generation |
| **min_index** | float | **Lowest index since signal generation** |
| **max_index** | float | **Highest index since signal generation** |
| index | float | Current index value |
| actual_diff | float | Current movement (index - start_index) |
| **greatest_positive_travel** | float | **Max upward movement** |
| **greatest_negative_travel** | float | **Max downward movement** |
| realized | boolean | Was signal realized at any point? |

**Bold** columns are new (added 2026-03-20) to track if signal was realized at ANY point during the period.

---

## Expected Output

### Typical Day (with new articles)
- Input: 50 new signals from today + 400 unexpired signals from past 30 days
- Output: ~450 records with realization status
- Realized rate: ~40-60% (depending on market volatility)

### Day with NO new articles
- Input: 0 new signals today + 400 unexpired signals from past 30 days
- Output: ~400 records with realization status
- **Process runs normally** - feeds data to downstream processes

---

## Downstream Process Flow

```
Process 6 (Signal Realization)
  ↓
  Outputs: All valid signals with realized: true/false
  ↓
Process 7 (Aggregate Signals)
  ↓
  Filters: Only unrealized signals (realized == false)
  ↓
  Groups by: generator_id + estimator_id + currency
  ↓
Process 8 (Calculate Trades)
  ↓
  Uses: Aggregated unrealized signals
```

---

## Dependencies

### Required Inputs
- **Process 2** (Currency Indices): Needs index data for movement calculation
- **Process 5** (Sentiment Signals): Needs signals to check (from past 30 days)

### Graceful Handling of Empty Files
- If Process 5 generates 0 signals today: Process 6 still checks past signals
- If no indices available: Skips those currency-date combinations
- **Always produces output** even with 0 new articles

---

## Example Scenarios

### Scenario 1: Normal Day (March 20)
```
- 53 new articles → 195 new signals
- + 380 unexpired signals from past days
- = 575 total signals checked
- Result: 333 realized (57.9%), 242 unrealized
```

### Scenario 2: Day with No Articles (March 19)
```
- 0 new articles → 0 new signals
- + 400 unexpired signals from past days
- = 400 total signals checked
- Result: ~230 realized, ~170 unrealized
- Downstream processes run normally with 170 unrealized signals
```

---

## Debugging

Check signal collection:
```bash
python3 scripts/pipeline/check-signal-realization.py --date 2026-03-20 | grep "Loaded.*signals"
```

Check realization rate:
```bash
python3 scripts/pipeline/check-signal-realization.py --date 2026-03-20 | grep -A 5 "Summary Statistics"
```

View output:
```bash
head -20 data/signal-realization/2026-03-20.csv
```

---

## Notes

- **Runs daily** after sentiment signal generation
- **Looks back 30 days** to check all active signals
- **Works with 0 new articles** - still checks historical signals
- Safe to rerun (recalculates based on latest index data)
- Enhanced logic (March 2026) now detects realization at ANY point during period
