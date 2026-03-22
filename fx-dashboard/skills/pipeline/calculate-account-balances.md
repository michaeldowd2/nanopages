# Calculate Account Balances (Process 10)

Run Process 10 of the FX portfolio pipeline to update account balances from executed trades.

## What This Does

Process 10 updates portfolio account balances by:
- Reading executed trades from Process 9
- Loading previous day's portfolio balances
- Applying the pre-calculated trade amounts to update balances
- Outputting updated portfolio states

This process contains **NO trade execution logic** - it simply applies the amounts calculated in Process 9.

## When to Run

- After Process 9 (Execute Trades) has been run
- Uses Process 9's executed trades for current date
- Uses Process 10's own output from previous date for starting balances
- Feeds into Process 11 (Portfolio Performance)

## Dependencies

**Required upstream steps:**
- Process 1: Exchange Rates (for initialization only)
- Process 9: Execute Trades (for executed trade amounts)
- Process 10: Account Balances (for previous date's balances)

## Command

```bash
#!/bin/bash

cd /workspace/group/fx-portfolio

# Run for today
python3 scripts/pipeline/calculate-account-balances.py

# Run for specific date
DATE="2026-03-21"
python3 scripts/pipeline/calculate-account-balances.py --date $DATE
```

## Output

Creates `data/portfolios/{date}.csv` with columns:
- date
- strategy_id
- trader_id
- trades_executed (count)
- EUR, USD, GBP, JPY, CHF, AUD, CAD, NOK, SEK, CNY, MXN (balances)

## Balance Update Logic

For each strategy:
1. Load previous day's portfolio balances
2. Find all executed trades for this strategy from Process 9
3. For each trade:
   - Subtract sell_amount from sell_currency balance
   - Add buy_amount to buy_currency balance
4. Output updated balances

**Note:** All trade amounts are pre-calculated in Process 9. This process just applies them.

## Example Output

```
date,strategy_id,trader_id,trades_executed,EUR,USD,GBP,JPY,CHF,AUD,CAD,NOK,SEK,CNY,MXN
2026-03-21,momentum-T1-size5,combinator-standard,1,100.0,121.5484,84.3413,16973.0135,84.7783,173.5734,163.8444,1326.4871,965.9357,861.8409,1911.9644
2026-03-21,momentum-T2-size5,combinator-standard,2,100.0,121.5484,84.3413,16209.4402,84.7783,173.5734,163.8444,1352.2144,965.9357,861.8409,1911.9644
```

## Portfolio Initialization

First time running (no previous portfolio):
- Initializes with 100 EUR equivalent in each currency
- EUR: 100.0
- Other currencies: 100.0 * EUR/{CURRENCY} exchange rate

## Notes

- Portfolio state is cumulative - each day builds on the previous
- Clearing this data resets all portfolio history
- Simple balance updates only - no complex trade logic
- Trade execution logic is centralized in Process 9
- One row per strategy (16 strategies typical)
