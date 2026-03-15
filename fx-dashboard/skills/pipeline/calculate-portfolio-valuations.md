# Skill: calculate-portfolio-valuations

Calculate multi-currency portfolio valuations and currency-neutral performance metrics.

## Purpose

Process 10 calculates the value of each portfolio in all 11 currencies and computes a currency-neutral performance index. This eliminates EUR-centric bias by averaging percentage changes across all currencies.

## What It Does

1. **Multi-Currency Valuation**: Values each portfolio in all 11 currencies (EUR, USD, GBP, JPY, CHF, AUD, CAD, NOK, SEK, CNY, MXN)
2. **Percentage Change Tracking**: Calculates day-over-day % change in each currency
3. **Currency-Neutral Performance**: Averages % changes across all currencies for unbiased performance measurement
4. **Cumulative Value Index**: Compounds the average % change daily to create a performance index (starts at 1.0)

## Why Multi-Currency?

Traditional portfolio valuation in a single currency (e.g., EUR) creates bias:
- If EUR weakens globally, EUR-denominated portfolio value appears to rise
- If EUR strengthens globally, EUR-denominated portfolio value appears to fall
- These changes don't reflect actual trading performance

By valuing in all 11 currencies and averaging the % changes, we get a currency-neutral view of actual trading performance.

## Inputs

- **data/prices/{date}.csv**: Exchange rates for the date
- **data/portfolios/{date}.csv**: Portfolio balances from Process 9
- **data/valuations/{prev_date}.csv**: Previous day's valuations (for % change calculation)

## Outputs

**data/valuations/{date}.csv** with columns:
- `date`: Valuation date
- `strategy_id`: Portfolio identifier
- `eur_value`, `usd_value`, `gbp_value`, etc.: Portfolio value in each currency
- `eur_pct_change`, `usd_pct_change`, etc.: % change from previous day in each currency
- `avg_pct_change`: Average % change across all 11 currencies (currency-neutral metric)
- `value`: Cumulative performance index (starts at 1.0, compounds avg_pct_change daily)

## How It Works

For each portfolio:

1. **Load current portfolio balances** (e.g., 50 EUR, 100 USD, 200 GBP)
2. **Load exchange rates** for the date
3. **Calculate portfolio value in each currency**:
   - EUR value: Convert all holdings to EUR
   - USD value: Convert all holdings to USD
   - GBP value: Convert all holdings to GBP
   - ... (repeat for all 11 currencies)

4. **Calculate % changes** from previous day:
   - EUR % change = (today's EUR value - yesterday's EUR value) / yesterday's EUR value × 100
   - USD % change = (today's USD value - yesterday's USD value) / yesterday's USD value × 100
   - ... (repeat for all 11 currencies)

5. **Calculate currency-neutral performance**:
   - `avg_pct_change` = average of all 11 % changes
   - This is the TRUE performance metric - unbiased by any single currency's movement

6. **Update cumulative value index**:
   - `value` = previous_value × (1 + avg_pct_change/100)
   - This compounds daily, creating a performance index starting from 1.0

## Example

Day 1 (first day):
- Portfolio valued in all 11 currencies
- No previous day, so all % changes = 0%
- `value` = 1.0 (starting point)

Day 2:
- EUR value changed +2%, USD value changed +1.8%, GBP changed +2.2%, etc.
- `avg_pct_change` = average of all 11 changes = +2.0%
- `value` = 1.0 × (1 + 2.0/100) = 1.02

Day 3:
- `avg_pct_change` = +1.5%
- `value` = 1.02 × (1 + 1.5/100) = 1.0353

The `value` column is the key performance metric - it shows cumulative portfolio performance independent of any single currency's movement.

## Usage

Run for a specific date:

```bash
python scripts/pipeline/calculate-portfolio-valuations.py --date 2024-03-14
```

## Dependencies

- Process 1: Exchange Rates (prices)
- Process 9: Portfolio Execution (portfolio balances)
- Previous day's valuations (for % change calculation)

## Notes

- First day (or after a gap) has no previous valuations, so all % changes are 0% and value starts at 1.0
- The script looks back up to 7 days to find the most recent previous valuation
- Performance index compounds daily - a portfolio with value=1.05 has gained 5% cumulatively
- The `avg_pct_change` is the key currency-neutral performance metric used in dashboard charts

## Configuration

Process 10 settings in `config/pipeline_steps.json`:
- `number_of_export_dates`: 30 (last 30 days exported to dashboard)

## Output Schema

See `config/pipeline_steps.json` step "10" for full schema definition with all 11 currency value columns and 11 pct_change columns plus avg_pct_change and cumulative value.
