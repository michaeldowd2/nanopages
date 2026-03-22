# Pipeline Process Refactoring (March 2026)

## Overview

The FX portfolio pipeline was refactored to eliminate redundant trade execution logic and create a clearer separation of concerns between trade execution and account management.

## Problem Identified

**Before refactoring:**
- **Process 8.1** (extract-executed-trades.py): Calculated trade amounts by executing trades on portfolio balances
- **Process 9** (execute-strategies.py): Did THE EXACT SAME THING - calculated trade amounts AND updated balances
- **Process 10** (calculate-portfolio-valuations.py): Calculated performance metrics

The trade execution logic (sorting by confidence, calculating amounts, applying spreads) was duplicated in both Process 8.1 and Process 9.

## Solution

**After refactoring:**
- **Process 9** (execute-trades.py): Single source of truth for trade execution - calculates exact amounts
- **Process 10** (calculate-account-balances.py): Simply applies pre-calculated amounts to balances
- **Process 11** (calculate-portfolio-performance.py): Calculates performance metrics

Trade execution logic now exists in EXACTLY ONE PLACE (Process 9).

## Detailed Changes

### Process 9: Execute Trades (NEW)
**File:** `scripts/pipeline/execute-trades.py`
**Output:** `data/executed-trades/{date}.csv`

**What it does:**
1. Loads proposed trades from Process 8
2. Loads previous day's portfolio balances from Process 10
3. For each strategy:
   - Filters trades for that strategy's trader
   - Sorts by trade_signal (descending)
   - Filters by confidence_threshold
   - Takes top N trades
   - **Calculates exact sell_amount and buy_amount** with spreads
4. Outputs individual trade records with exact amounts

**Key point:** This is the ONLY place where trade amounts are calculated.

### Process 10: Account Balances (NEW)
**File:** `scripts/pipeline/calculate-account-balances.py`
**Output:** `data/portfolios/{date}.csv`

**What it does:**
1. Loads executed trades from Process 9
2. Loads previous day's portfolio balances
3. For each strategy:
   - Finds all executed trades for that strategy
   - **Simply applies the amounts**: `balance[sell_curr] -= sell_amount`, `balance[buy_curr] += buy_amount`
4. Outputs updated portfolio balances

**Key point:** NO trade execution logic - just balance updates.

### Process 11: Portfolio Performance (NEW)
**File:** `scripts/pipeline/calculate-portfolio-performance.py`
**Output:** `data/valuations/{date}.csv`

**What it does:**
1. Loads portfolio balances from Process 10
2. Calculates portfolio value in all 11 currencies
3. Calculates percentage changes in each currency
4. Computes currency-neutral performance metric
5. Outputs multi-currency valuations

**No changes to logic** - just renumbered from Process 10 → 11.

## File Mapping

| Old Name | New Name | Process |
|----------|----------|---------|
| extract-executed-trades.py | execute-trades.py | 9 |
| execute-strategies.py | calculate-account-balances.py | 10 |
| calculate-portfolio-valuations.py | calculate-portfolio-performance.py | 11 |

## Data Flow

```
Process 8: Calculate Trades
    ↓ (proposed trades)
Process 9: Execute Trades
    ↓ (executed trades with exact amounts)
Process 10: Account Balances
    ↓ (portfolio balances)
Process 11: Portfolio Performance
    ↓ (valuations & performance metrics)
```

## Benefits

1. **Single Source of Truth**: Trade execution logic exists in exactly one place
2. **Easier to Maintain**: Changes to trade logic only need to happen in Process 9
3. **Clearer Separation**: Process 9 = execute, Process 10 = account management
4. **No Duplication**: Eliminated ~200 lines of duplicated trade execution code
5. **More Testable**: Each process has a single, clear responsibility

## Backward Compatibility

The refactoring maintains backward compatibility:
- Output file formats unchanged
- Output file locations unchanged
- CSV schemas unchanged
- Legacy process name mappings added to csv_helper.py:
  - `process_9_executed_trades` → Process 9
  - `process_10_portfolio` → Process 10
  - `process_11_valuations` → Process 11

## Testing

Tested on 2026-03-21:
- Process 9: 53 rows (52 executed trades)
- Process 10: 17 rows (16 strategies)
- Process 11: 17 rows (16 strategies)

All processes executed successfully with identical output to pre-refactoring runs.

## Documentation Updated

- ✅ README.md - Updated pipeline step count (7 → 11)
- ✅ execute-trades.md - New skill file for Process 9
- ✅ calculate-account-balances.md - New skill file for Process 10
- ✅ calculate-portfolio-performance.md - Updated skill file for Process 11
- ✅ pipeline_steps.json - Updated with new process structure
- ✅ csv_helper.py - Added legacy name mappings

## Migration Notes

**For future runs:**
- Old scripts (`extract-executed-trades.py`, `execute-strategies.py`, `calculate-portfolio-valuations.py`) still exist but are not used
- New scripts (`execute-trades.py`, `calculate-account-balances.py`, `calculate-portfolio-performance.py`) are the active versions
- Pipeline config (`pipeline_steps.json`) points to new scripts
- No data migration needed - formats are identical

**For developers:**
- Trade execution logic is now ONLY in `execute-trades.py` (Process 9)
- Never modify trade logic in `calculate-account-balances.py` (Process 10) - it just applies amounts
- Process 10 should remain simple - only balance arithmetic

## Date of Refactoring

March 21, 2026
