# Skill: calculate-trades

Generate trade recommendations from aggregated signals using a combinator strategy.

---

## Purpose

Analyzes aggregated currency signals and generates specific trade pairs (buy currency X, sell currency Y) with confidence scores. Uses a combinator approach to identify the strongest bullish/bearish pairings.

**Implementation Date**: 2026-03-01

---

## Quick Start

```bash
cd /workspace/group/fx-portfolio
python3 scripts/calculate-trades-step8.py --date 2026-03-08
```

**Input**: `/data/aggregated-signals/aggregated_signals.csv` (from aggregate-signals)
**Output**: `/data/trades/trades.csv`

---

## Expected Output

### Output Files

**Primary Output**: `/data/trades/trades.csv`
- Format: CSV
- Updated: Appended daily
- Size: ~2-5 KB per day

### Output Schema

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| date | string | Trading date (YYYY-MM-DD) | 2026-03-08 |
| trader_id | string | Generator/combinator ID | combinator-standard |
| buy_currency | string | Currency to buy | USD |
| sell_currency | string | Currency to sell | JPY |
| buy_signal | float | Strength of buy signal (0-1) | 0.67 |
| sell_signal | float | Strength of sell signal (0-1) | 0.54 |
| trade_signal | float | Combined trade confidence (0-1) | 0.605 |

### Sample Output

```csv
date,trader_id,buy_currency,sell_currency,buy_signal,sell_signal,trade_signal
2026-03-08,combinator-standard,USD,JPY,0.67,0.54,0.605
2026-03-08,combinator-standard,GBP,CHF,0.45,0.38,0.415
```

### Interpretation

- **trade_signal**: Higher values indicate stronger conviction trades (average of buy and sell signals)
- **buy_signal**: Positive aggregated signal for the buy currency
- **sell_signal**: Absolute value of negative aggregated signal for sell currency
- **Typical range**: 0.3-0.8 (filtered below min_signal_threshold)
- **Use this data to**: Execute hypothetical trades in execute-strategies

---

## How It Works

### 1. Load Aggregated Signals

Reads the aggregated signals for all currencies from aggregate-signals.

### 2. Identify Bullish and Bearish Currencies

**Bullish** (positive aggregated_signal):
- Currencies expected to strengthen
- Candidates to BUY

**Bearish** (negative aggregated_signal):
- Currencies expected to weaken
- Candidates to SELL

### 3. Generate Trade Pairs

Creates all combinations of bullish × bearish:
- Buy: Most bullish currency
- Sell: Most bearish currency

For each trade pair:
```
buy_signal = aggregated_signal for buy currency
sell_signal = |aggregated_signal| for sell currency
trade_signal = (buy_signal + sell_signal) / 2
```

### 4. Rank by Trade Signal

Sorts trades by `trade_signal` (descending) to identify strongest opportunities.

### 5. Output Format

CSV file with columns:
- `date`: Trading date
- `trader_id`: Generator/combinator ID
- `buy_currency`: Currency to buy
- `sell_currency`: Currency to sell
- `buy_signal`: Strength of buy signal (0-1)
- `sell_signal`: Strength of sell signal (0-1)
- `trade_signal`: Combined trade confidence (0-1)

---

## Example Output

```csv
date,trader_id,buy_currency,sell_currency,buy_signal,sell_signal,trade_signal
2026-03-08,combinator-standard,USD,JPY,0.67,0.54,0.605
2026-03-08,combinator-standard,GBP,CHF,0.45,0.38,0.415
```

---

## Trade Combinator Configuration

Defined in `config/system_config.json`:

```json
{
  "trade_combinators": [
    {
      "id": "combinator-standard",
      "type": "all-pairs-v1",
      "params": {
        "min_signal_threshold": 0.3,
        "max_trades_per_day": 20
      }
    }
  ]
}
```

**Parameters**:
- `min_signal_threshold`: Minimum aggregated signal to consider (filters weak signals)
- `max_trades_per_day`: Maximum trades to generate (takes top N)

---

## Trade Selection Logic

The combinator uses this logic:

1. **Filter weak signals**: Remove currencies with `|aggregated_signal| < min_threshold`
2. **Separate by direction**: Bullish (positive) vs Bearish (negative)
3. **Generate all pairs**: Every bullish × bearish combination
4. **Calculate trade_signal**: Average of buy and sell signal strengths
5. **Rank and limit**: Sort by trade_signal, take top `max_trades_per_day`

---

## Dependencies

**Upstream Steps**:
- aggregate-signals: `aggregate-signals.py` (provides aggregated signals)

**Data Required**:
- `/data/aggregated-signals/aggregated_signals.csv`

---

## Troubleshooting

**"No trades generated"**:
- Check aggregate-signals output - may not have both bullish and bearish signals
- Lower `min_signal_threshold` in config
- Verify aggregated signals exist for the date

**Too many/few trades**:
- Adjust `max_trades_per_day` in config
- Review `min_signal_threshold` setting

**Trade signals seem wrong**:
- Check aggregated signals in aggregate-signals output
- Verify buy_signal + sell_signal calculation
- Review individual currency signals in dashboard

---

## Next Steps

After running this step:
- **execute-strategies**: Execute trades on portfolio strategies
- Review trade recommendations in dashboard
- Analyze which currency pairs are most frequently recommended
