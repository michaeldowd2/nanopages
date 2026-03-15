# Extract Executed Trades (Step 8.1)

Run Step 8.1 of the FX portfolio pipeline to extract actual executed trades with real currency amounts.

## What This Does

Step 8.1 extracts the actual trades executed for each portfolio configuration, showing:
- Real currency amounts bought and sold
- Balance changes before/after each trade
- Exchange rates applied
- Spread costs in EUR
- Portfolio value changes per trade
- Full trade execution details

This process mirrors the trade execution logic from Step 9 but outputs individual trade records instead of final portfolio states.

## When to Run

- After Step 8 (Trade Calculation) has been run
- Uses previous day's Step 9 (Portfolio Execution) for starting balances
- Can be run independently or as part of the full pipeline
- Does NOT feed into Step 9 - it's a parallel output for visibility

## Dependencies

**Required upstream steps:**
- Step 1: Exchange Rates (for current date)
- Step 8: Trade Calculation (for proposed trades)
- Step 9: Portfolio Execution (for previous date's portfolio state)

## Command

```bash
#!/bin/bash

cd /workspace/group/fx-portfolio

# Run for today
python3 scripts/pipeline/extract-executed-trades.py

# Run for specific date
DATE="2026-03-15"
python3 scripts/pipeline/extract-executed-trades.py --date $DATE
```

## Output

Creates `data/executed-trades/{date}.csv` with columns:
- date
- strategy_id
- trader_id
- sell_currency / buy_currency
- sell_amount / buy_amount
- sell_balance_before / sell_balance_after
- buy_balance_before / buy_balance_after
- exchange_rate
- spread_pct
- trade_size_eur
- cost_eur
- portfolio_value_before / portfolio_value_after
- buy_signal / sell_signal / trade_signal

## Viewing Results

After running:
1. Run `python3 scripts/deployment/export-pipeline-data.py` to export to dashboard
2. Open the dashboard at `index.html`
3. Navigate to "STEP 8.1" tab
4. Filter by portfolio, date, or currency to view executed trades

## Example Output

```
date,strategy_id,trader_id,sell_currency,buy_currency,sell_amount,buy_amount,...
2026-03-15,momentum-T1-size5,combinator-standard,EUR,USD,50.0,57.34,...
2026-03-15,momentum-T2-size5,combinator-standard,USD,JPY,100.0,15965.07,...
```

## Notes

- Trade amounts in Step 8.1 should exactly match what was applied in Step 9
- Useful for debugging portfolio behavior and understanding actual trade sizes
- Shows spread costs explicitly (0.74% by default)
- One row per executed trade (portfolios with multiple trades get multiple rows)
