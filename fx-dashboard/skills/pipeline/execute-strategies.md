# Skill: execute-strategies

Execute trading strategies on hypothetical portfolios using unrealized signals.

## Purpose

Strategies aggregate currency signals, generate pair trades, and track hypothetical account balances over time. Multiple parameter combinations run in parallel to compare performance.

---

## Quick Start

```bash
cd /workspace/group/fx-portfolio
python3 scripts/pipeline/execute-strategies.py --date 2026-03-08
```

---

## Expected Output

### Output Files

**Single Output**: `/data/portfolios/strategies.csv`
- Format: CSV
- Updated: Appended daily (one row per strategy per date)
- Size: ~2-5 KB per day
- Contains complete portfolio history and state

**Portfolio State Management:**
- Portfolio state is stored directly in the CSV (currency balance columns)
- Each run reads the previous date's row to get starting balances
- First run (no previous data) initializes with 100 EUR equivalent in each currency
- No separate state files needed - CSV contains all historical data

### Output Schema (CSV)

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| date | string | Execution date (YYYY-MM-DD) | 2026-02-21 |
| strategy_id | string | Strategy identifier | trader_keyword-llm_est_keyword-llm_conf_0.7_size_0.15 |
| trader_id | string | Trader identifier | trader_keyword-llm |
| trades_executed | integer | Number of trades executed | 2 |
| EUR, USD, GBP, JPY... | float | Balance in each currency | 5000 |

### Sample Output

```csv
date,strategy_id,trader_id,trades_executed,EUR,USD,GBP,JPY,CHF,AUD,CAD,NOK,SEK,CNY,MXN
2026-02-21,trader_keyword-llm_est_keyword-llm_conf_0.7_size_0.15,trader_keyword-llm,2,5000,2500,0,0,0,1200,0,0,0,0,0
```

### Interpretation

- **trades_executed**: Number of currency pair trades executed that day
- **Currency balances**: Current holdings in each currency (0 = no position)
- **Use this data to**: Track portfolio composition over time
- **Note**: Portfolio value is calculated separately in Process 10 (Portfolio Valuation) which values the portfolio in all 11 currencies for currency-neutral performance tracking

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

**CSV**: `/data/portfolios/strategies.csv`

Columns:
- `date` - Execution date
- `strategy_id` - Strategy identifier
- `trader_id` - Trader identifier
- `trades_executed` - Count of trades executed today
- `EUR`, `USD`, `GBP`, `JPY`, `CHF`, `AUD`, `CAD`, `NOK`, `SEK`, `CNY`, `MXN` - Balance in each currency

**Example row:**
```
2026-02-21,trader_keyword-llm_est_keyword-llm_conf_0.7_size_0.15,trader_keyword-llm,2,5000,2500,0,0,0,1200,0,0,0,0,0
```

This means:
- 2 trades executed
- €5,000 in EUR, $2,500 in USD, A$1,200 in AUD
- Portfolio value calculated in Process 10 (Portfolio Valuation)


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

**How it works:**
1. Each strategy reads its most recent row from strategies.csv to get starting balances
2. If no previous row exists (first run), initializes with 100 EUR equivalent in each currency
3. Executes trades and updates balances
4. Appends new row to strategies.csv with updated balances
5. Next day repeats from step 1

**Initial portfolio (first run):**
- 100 EUR in EUR
- 100 EUR equivalent in each other currency (calculated using exchange rates)
- Example: If EUR/USD = 1.08, then USD balance = 108.00

**State persistence:**
- All portfolio state is in the CSV - no separate files needed
- Each row contains complete snapshot of portfolio balances
- Historical performance can be analyzed directly from CSV

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

View all strategies:
```bash
column -t -s, data/portfolios/strategies.csv | less -S
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
