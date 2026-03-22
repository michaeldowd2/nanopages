# Performance Calculation Bug Fix (2026-03-22)

## Issue

Portfolio performance metrics were resetting to zero for March 21st and 22nd, showing:
- All individual currency returns: `0.0%`
- Cumulative performance value: `1.0` (baseline)

This occurred despite:
- Account balances changing correctly
- Trades being executed properly

## Root Cause

**Bug in Process 11** (calculate-portfolio-performance.py), line 114:

```python
# WRONG (after refactoring):
prev_rows = read_csv('process_10_valuations', date=check_date_str, validate=False)
```

After the pipeline refactoring:
- **Process 10** = Account Balances (portfolios)
- **Process 11** = Portfolio Performance (valuations)

The script was trying to read previous valuations from `process_10_valuations` (old naming), but that file no longer exists. It should read from `process_11_valuations`.

## Impact

- Process 11 couldn't find previous day's valuations
- Treated each day as the "first day" of tracking
- Performance metrics reset to baseline (0% change, value=1.0)
- Account balances (Process 10) were unaffected and correct

## Fix

Changed line 114 in `calculate-portfolio-performance.py`:

```python
# CORRECT:
prev_rows = read_csv('process_11_valuations', date=check_date_str, validate=False)
```

## Validation Checks Added

Added automated validation to both Process 10 and Process 11:

### Process 10 (Account Balances)
- **Check**: If trades were executed, balances should differ from previous day
- **Warning**: "N portfolios have identical balances to previous day despite M trades executed"

### Process 11 (Portfolio Performance)
- **Check 1**: Performance metrics shouldn't reset to zero when previous data exists
- **Warning**: "N strategies have performance metrics reset to zero (0% change, value=1.0) despite previous data existing"
- **Check 2**: Portfolio values should change between days
- **Warning**: "N portfolios have nearly identical EUR values to previous day"

## Results

After fix, March 21st performance for momentum-T1-size5:
```
EUR: -0.56%  USD: -0.34%  GBP: +0.18%  JPY: +0.26%
CHF: -0.41%  AUD: +0.58%  CAD: -0.36%  NOK: +0.36%
SEK: +0.18%  CNY: -0.40%  MXN: +0.50%

Average % Change (Currency-Neutral): +0.00%
Cumulative Value: 1.000375
```

March 22nd performance for momentum-T1-size5:
```
EUR: +0.01%  USD: +0.01%  GBP: +0.04%  JPY: +0.01%
CHF: -0.01%  AUD: -0.07%  CAD: -0.02%  NOK: -0.01%
SEK: +0.00%  CNY: -0.01%  MXN: +0.03%

Average % Change (Currency-Neutral): -0.00%
Cumulative Value: 1.000373
```

✅ **Validation passed**: All checks confirm correct calculation

## Files Modified

1. `scripts/pipeline/calculate-portfolio-performance.py`
   - Fixed line 114: Changed `process_10_valuations` → `process_11_valuations`
   - Added validation checks after CSV write

2. `scripts/pipeline/calculate-account-balances.py`
   - Added validation checks after CSV write

## Prevention

These validation checks will now catch similar issues automatically:
- If performance metrics reset unexpectedly
- If balances don't change despite trades
- If values are identical to previous day when they shouldn't be

The warnings are displayed in the process output and logged for monitoring.
