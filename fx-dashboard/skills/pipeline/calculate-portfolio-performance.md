# Calculate Portfolio Performance (Process 11)

Run Process 11 of the FX portfolio pipeline to calculate multi-currency portfolio valuations and performance metrics.

## What This Does

Process 11 calculates portfolio performance by:
- Reading account balances from Process 10
- Valuing portfolios in all 11 currencies
- Calculating percentage changes in each currency
- Computing currency-neutral performance metric (average % change)
- Tracking cumulative performance index

## When to Run

- After Process 10 (Account Balances) has been run
- Uses Process 10's portfolio balances for current date
- Uses Process 11's own output from previous date for % change calculations
- Final step in the pipeline

## Dependencies

**Required upstream steps:**
- Process 1: Exchange Rates (for currency conversions)
- Process 10: Account Balances (for portfolio balances)
- Process 11: Portfolio Performance (for previous date's valuations)

## Command

```bash
#!/bin/bash

cd /workspace/group/fx-portfolio

# Run for today
python3 scripts/pipeline/calculate-portfolio-performance.py

# Run for specific date
DATE="2026-03-21"
python3 scripts/pipeline/calculate-portfolio-performance.py --date $DATE
```

## Output

Creates `data/valuations/{date}.csv` with columns:
- date, strategy_id
- eur_value, usd_value, gbp_value, jpy_value, chf_value, aud_value, cad_value, nok_value, sek_value, cny_value, mxn_value
- eur_pct_change, usd_pct_change, gbp_pct_change, jpy_pct_change, chf_pct_change, aud_pct_change, cad_pct_change, nok_pct_change, sek_pct_change, cny_pct_change, mxn_pct_change
- avg_pct_change (currency-neutral performance)
- value (cumulative performance index)

## Currency-Neutral Performance

The key insight: **avg_pct_change** provides currency-neutral performance by:
1. Valuing the portfolio in all 11 currencies
2. Calculating % change in each currency
3. Averaging the % changes

This reduces EUR-centric bias. If EUR weakens globally, the portfolio might show:
- EUR value: -0.5%
- USD value: +0.3%
- GBP value: +0.1%
- etc.

Average: ~0% → true portfolio performance regardless of base currency

## Cumulative Performance Index

The **value** column tracks cumulative performance:
- Starts at 1.0 (100%)
- Multiplies by (1 + avg_pct_change/100) each day
- Example: 1.0 → 1.002 → 1.005 → 1.008
- Shows total performance since inception

## Example Output

```
date,strategy_id,eur_value,usd_value,...,avg_pct_change,value
2026-03-21,momentum-T1-size5,1103.78,1279.44,...,+0.00%,1.000375
2026-03-21,momentum-T2-size5,1103.78,1279.44,...,-0.01%,1.000341
```

## Sample Output Display

```
Sample: momentum-T1-size5

Values:
  EUR: 1,103.78
  USD: 1,279.44
  GBP: 958.81
  JPY: 203,740.94
  ...

Percentage Changes:
  EUR: -0.56%
  USD: -0.34%
  GBP: +0.18%
  ...

Average % Change (Currency-Neutral): +0.00%
Cumulative Value (Performance Index): 1.000375
```

## Notes

- This is the final output used for performance analysis
- avg_pct_change is the primary performance metric
- Valuation in multiple currencies provides robustness
- First day shows 0% change (no previous valuation)
- One row per strategy (16 strategies typical)
