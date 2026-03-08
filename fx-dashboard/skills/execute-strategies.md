# Skill: execute-strategies

Execute trading strategies on hypothetical portfolios using unrealized signals.

## Purpose

Strategies aggregate currency signals, generate pair trades, and track hypothetical account balances over time. Multiple parameter combinations run in parallel to compare performance.

---

## Quick Start

```bash
cd /workspace/group/fx-portfolio
python3 scripts/strategy-simple-momentum.py
```

---

## Expected Output

### Output Files

**Primary Output**: `/data/exports/step7_strategies.csv`
- Format: CSV
- Updated: Appended daily
- Size: ~2-5 KB per day

**Detailed Output**: `/data/exports/step7_strategies_detail.json`
- Format: JSON
- Contains full trade history and aggregate signals
- Size: ~20-50 KB per day

**Portfolio State**: `/data/portfolios/{strategy_name}_{params}.json`
- Format: JSON
- One file per strategy combination
- Persistent state between runs

### Output Schema (CSV)

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| date | string | Execution date (YYYY-MM-DD) | 2026-02-21 |
| strategy_name | string | Strategy identifier | simple-momentum |
| strategy_params | string | Parameter combination | conf=0.5_size=0.25_agg=average |
| executed_trades | integer | Number of trades executed | 2 |
| EUR, USD, GBP, JPY... | float | Balance in each currency | 5000 |
| current_value | float | Total portfolio value in EUR | 9875.50 |

### Sample Output

```csv
date,strategy_name,strategy_params,executed_trades,EUR,USD,GBP,JPY,CHF,AUD,CAD,NOK,SEK,CNY,MXN,current_value
2026-02-21,simple-momentum,conf=0.5_size=0.25_agg=average,2,5000,2500,0,0,0,1200,0,0,0,0,0,9875.50
```

### Interpretation

- **executed_trades**: Number of currency pair trades executed that day
- **current_value**: Total portfolio value in EUR (accounts for all currency holdings)
- **Currency balances**: Current holdings in each currency (0 = no position)
- **Value < 10000**: Portfolio has lost money (spreads, bad trades)
- **Value > 10000**: Portfolio has gained money (successful trades)
- **Use this data to**: Compare performance across different strategy parameters

---

## Current Implementation: Simple Momentum Strategy

**Logic:**
1. Load unrealized signals (realized=false from check-signal-realization)
2. Aggregate multiple signals per currency into composite signal
3. Rank currencies by signal strength
4. Pair strongest bullish with strongest bearish
5. Execute trades on hypothetical portfolio (with Revolut spreads)
6. Track portfolio balances and EUR value

**Parameters:**
- `confidence_threshold`: Minimum aggregate confidence to trade (0.5, 0.6, 0.7)
- `trade_size_pct`: % of available balance to trade (0.25, 0.50, 0.75)
- `aggregation_method`: How to combine signals ('average')

**9 Combinations:** 3 thresholds × 3 sizes × 1 method = 9 strategies

## Output

**CSV**: `/data/exports/step7_strategies.csv`

Columns:
- `date` - Execution date
- `strategy_name` - e.g., "simple-momentum"
- `strategy_params` - Parameter combination
- `executed_trades` - Count of trades executed today
- `EUR`, `USD`, `GBP`, `JPY`, `CHF`, `AUD`, `CAD`, `NOK`, `SEK`, `CNY`, `MXN` - Balance in each currency
- `current_value` - Total portfolio value in EUR

**Example row:**
```
2026-02-21,simple-momentum,conf=0.5_size=0.25_agg=average,2,5000,2500,0,0,0,1200,0,0,0,0,0,9875.50
```

This means:
- 2 trades executed
- €5,000 in EUR, $2,500 in USD, A$1,200 in AUD
- Total portfolio worth €9,875.50 (lost €124.50 to spreads)

**Detailed JSON**: `/data/exports/step7_strategies_detail.json`

Contains full trade history, aggregate signals, proposed vs executed trades.

## Trade Execution Logic

**Pairing:**
```
Bullish currencies (sorted by confidence):
  GBP: 0.85, AUD: 0.72, USD: 0.65

Bearish currencies (sorted by confidence):
  JPY: 0.78, EUR: 0.68, CAD: 0.55

Pairs generated:
  1. Sell JPY (0.78) → Buy GBP (0.85) [combined conf: 0.815]
  2. Sell EUR (0.68) → Buy AUD (0.72) [combined conf: 0.70]
  3. Sell CAD (0.55) → Buy USD (0.65) [combined conf: 0.60]
```

**Trade execution:**
1. Check sell currency balance > 0
2. Calculate EUR equivalent of trade amount
3. Apply Revolut spread on sell side (~0.37%)
4. Convert to buy currency at current rate
5. Apply spread on buy side (~0.37%)
6. Update portfolio balances

**Spreads:**
- Default: 0.74% total (0.37% each direction)
- Based on observed Revolut rates
- Future: Per-currency spreads from manual observation

## Portfolio State Management

Each strategy combination maintains its own portfolio file:
- `/data/portfolios/simple-momentum_conf=0.5_size=0.25_agg=average.json`

**Initial state:**
```json
{
  "portfolio": {
    "EUR": 10000,
    "USD": 0,
    ...
  },
  "last_updated": "2026-02-21T14:44:56Z"
}
```

**After trades:**
```json
{
  "portfolio": {
    "EUR": 5000,
    "USD": 2500,
    "GBP": 1200,
    ...
  },
  "last_updated": "2026-02-22T09:30:00Z"
}
```

Portfolio persists between runs - next day's strategy starts with previous day's balances.

## Dependencies

- **fetch-exchange-rates**: Requires current EUR pair prices
- **generate-sentiment-signals**: Requires signals
- **check-signal-realization**: Requires realization status (realized=true/false)

## Next Steps

After running this step:
- Compare performance across 9 parameter combinations
- Identify best-performing strategies
- Analyze trade patterns and currency preferences

## Debugging

Check aggregate signals:
```bash
python3 -c "
import json
with open('data/exports/step7_strategies_detail.json') as f:
    strat = json.load(f)[0]
    for curr, sig in strat['aggregate_signals'].items():
        if sig['confidence'] > 0.3:
            print(f\"{curr}: {sig['direction']} ({sig['confidence']})\")
"
```

Check portfolio state:
```bash
cat data/portfolios/simple-momentum_conf=0.5_size=0.25_agg=average.json
```

View CSV:
```bash
column -t -s, data/exports/step7_strategies.csv | less -S
```

## Future Strategies

Additional strategies to implement:

**1. Contrarian Strategy**
- Fade extreme signals (sell overbought, buy oversold)
- Inverse of momentum logic

**2. Multi-Timeframe Strategy**
- Combine short/medium/long horizon signals
- Weight recent signals higher

**3. Risk-Weighted Strategy**
- Adjust trade sizes based on confidence
- Smaller trades for lower confidence signals

**4. Mean Reversion Strategy**
- Track historical average signal strength per currency
- Trade when deviation from mean exceeds threshold

**5. Volatility-Adjusted Strategy**
- Reduce trade sizes during high volatility periods
- Use index movements to calculate volatility

Each strategy can have its own parameters and generate 9+ combinations.

## Notes

- All portfolios start with €10,000 EUR
- Trades only execute if confidence threshold met
- Spreads applied on both sides of trade (total ~0.74%)
- No trades = portfolio value stays same (minus any previous losses)
- Strategies run independently (don't affect each other)
