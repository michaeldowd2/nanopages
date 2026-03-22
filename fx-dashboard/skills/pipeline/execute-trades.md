# Execute Trades (Process 9)

Run Process 9 of the FX portfolio pipeline to execute trades with exact currency amounts calculated.

## What This Does

Process 9 is the **definitive trade execution step** that:
- Takes proposed trades from Process 8
- Selects top N trades per strategy (sorted by confidence)
- Calculates exact sell/buy amounts based on current portfolio balances
- Applies spreads (0.74% by default)
- Outputs individual trade records with full execution details

This is the ONLY place where trade execution logic exists. Process 10 simply reads these trades and updates account balances.

## When to Run

- After Process 8 (Trade Calculation) has been run
- Uses previous day's Process 10 (Account Balances) for starting balances
- Feeds into Process 10 which updates portfolio balances
- Essential step in the pipeline - must run before Process 10

## Dependencies

**Required upstream steps:**
- Process 1: Exchange Rates (for current date)
- Process 8: Trade Calculation (for proposed trades)
- Process 10: Account Balances (for previous date's portfolio state)

## Command

```bash
#!/bin/bash

cd /workspace/group/fx-portfolio

# Run for today
python3 scripts/pipeline/execute-trades.py

# Run for specific date
DATE="2026-03-21"
python3 scripts/pipeline/execute-trades.py --date $DATE
```

## Output

Creates `data/executed-trades/{date}.csv` with columns:
- date
- strategy_id
- trader_id
- sell_currency / buy_currency
- sell_amount / buy_amount (exact amounts calculated)
- exchange_rate
- spread_pct (0.0074 = 0.74%)
- trade_size_eur
- cost_eur (spread cost)
- trade_signal

## Trade Execution Logic

For each strategy:
1. Filter trades for the strategy's trader
2. Sort by trade_signal (descending)
3. Filter by confidence_threshold
4. Take top N trades (where N = target_trades)
5. For each trade:
   - Calculate trade size = sell_balance * max_trade_size_pct * trade_signal
   - Convert to buy currency with exchange rate
   - Apply 0.74% spread
   - Calculate exact sell_amount and buy_amount

## Example Output

```
date,strategy_id,trader_id,sell_currency,buy_currency,sell_amount,buy_amount,exchange_rate,spread_pct,trade_size_eur,cost_eur,trade_signal
2026-03-21,momentum-T1-size5,combinator-standard,JPY,NOK,263.547,15.7146,0.060072,0.0074,1.43,0.01,0.3058
2026-03-21,momentum-T2-size5,combinator-standard,JPY,NOK,496.874,29.6273,0.060072,0.0074,2.69,0.02,0.3058
```

## Notes

- This is the **single source of truth** for trade execution
- Trade amounts calculated here are used by Process 10 to update balances
- No trade calculation logic exists in Process 10 - it just applies these amounts
- Shows spread costs explicitly (0.74% by default)
- One row per executed trade (52 trades for 16 strategies typical)
