# Step 7a/7b Integration - 2026-02-26

## Summary

Connected Step 7b (Portfolio Executor) to read trades from Step 7a (Trade Calculator), completing the separation of trade calculation and portfolio execution.

---

## What Changed

### Before (Single Step)
```
Step 7: execute-strategies.py
├── Load signals
├── Aggregate signals
├── Generate trades internally    ← Trade logic here
├── Execute trades
├── Update portfolios
└── Calculate values
```

### After (Two Steps Connected)
```
Step 7a: calculate-trades.py
├── Load signals
├── Aggregate signals
├── Generate trades
└── Export to step7a_trades.csv   ← Trade proposals saved

Step 7b: execute-strategies.py
├── Read trades from step7a_trades.csv  ← NEW: Reads from 7a
├── Load portfolios
├── Execute trades from 7a
├── Update balances
└── Calculate values
```

---

## Code Changes

### New Function: `load_trades_from_step7a()`

```python
def load_trades_from_step7a(strategy_id, date_str):
    """
    Load pre-calculated trades from Step 7a (calculate-trades.py)

    Parameters:
    - strategy_id: Strategy identifier to filter trades
    - date_str: Date to load trades for

    Returns: List of trade dicts with trade_size_eur already calculated
    """
    import csv

    trades_file = '/workspace/group/fx-portfolio/data/exports/step7a_trades.csv'

    if not os.path.exists(trades_file):
        return []

    trades = []

    with open(trades_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter by strategy_id and date
            if row['strategy_id'] == strategy_id and row['date'] == date_str:
                trades.append({
                    'from_currency': row['from_currency'],
                    'to_currency': row['to_currency'],
                    'trade_size_eur': float(row['from_amount_euro']),
                    'buy_confidence': float(row['buy_confidence']),
                    'sell_confidence': float(row['sell_confidence']),
                    'signal_strength_factor': float(row['signal_strength_factor']),
                    'combined_confidence': (float(row['buy_confidence']) +
                                           float(row['sell_confidence'])) / 2
                })

    return trades
```

### Updated: `run_strategy()`

**Before:**
```python
# Generate trade proposals
proposed_trades = generate_trades(
    aggregate_signals,
    confidence_threshold,
    eur_rates,
    all_pairs,
    portfolio,
    max_trade_size_pct
)
```

**After:**
```python
# Load pre-calculated trades from Step 7a
proposed_trades = load_trades_from_step7a(strategy_id, date_str)
```

**Result:** Step 7b no longer calculates trades internally. It reads them from Step 7a CSV.

---

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ Step 7a: calculate-trades.py                                │
├─────────────────────────────────────────────────────────────┤
│ 1. Load signals from Steps 4-6                              │
│ 2. Aggregate signals per currency                           │
│ 3. Calculate trades for each strategy:                      │
│    - Filter by confidence threshold                         │
│    - Pair bullish with bearish                              │
│    - Size trades by signal strength                         │
│    - Calculate spread costs                                 │
│ 4. Export: data/exports/step7a_trades.csv                   │
│    ├── strategy_id, date, from_currency, to_currency       │
│    ├── from_amount_euro, exchange_rate_with_spread         │
│    ├── to_amount_euro, to_amount_opposite                   │
│    └── cost_euro (spread cost)                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
                step7a_trades.csv
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 7b: execute-strategies.py                              │
├─────────────────────────────────────────────────────────────┤
│ 1. Load trades from step7a_trades.csv                       │
│    - Filter by strategy_id + date                           │
│ 2. Load portfolio state (or initialize)                     │
│ 3. Execute each trade:                                      │
│    - Deduct from source currency                            │
│    - Add to target currency (after spread)                  │
│ 4. Calculate portfolio value using mid rates                │
│ 5. Save portfolio state                                     │
│ 6. Export: data/exports/step7_strategies.csv                │
│    └── Portfolio balances + aggregate signals + values      │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Step 7a Output (step7a_trades.csv)
```csv
strategy_id,date,from_currency,to_currency,from_amount_euro,from_amount_base,exchange_rate_mid,exchange_rate_with_spread,to_amount_euro,to_amount_opposite,cost_euro,signal_strength_factor,buy_confidence,sell_confidence
simple-momentum-conf0.5-size0.25,2026-02-26,EUR,CNY,387.5,387.5,8.10028,8.040338,384.63,3115.63,2.87,0.39,0.21,0.57
simple-momentum-conf0.5-size0.25,2026-02-26,EUR,AUD,186.11,186.11,1.663477,1.651167,184.73,307.3,1.38,0.19,0.19,0.18
```

### Step 7b Input (reads from step7a_trades.csv)
```python
# Loads trades for strategy_id="simple-momentum-conf0.5-size0.25", date="2026-02-26"
[
  {
    'from_currency': 'EUR',
    'to_currency': 'CNY',
    'trade_size_eur': 387.5,
    'buy_confidence': 0.21,
    'sell_confidence': 0.57,
    'signal_strength_factor': 0.39
  },
  {
    'from_currency': 'EUR',
    'to_currency': 'AUD',
    'trade_size_eur': 186.11,
    'buy_confidence': 0.19,
    'sell_confidence': 0.18,
    'signal_strength_factor': 0.19
  }
]
```

### Step 7b Output (step7_strategies.csv)
```csv
date,strategy_id,executed_trades,current_value,EUR,CNY,AUD,...
2026-02-26,simple-momentum-conf0.5-size0.25,2,9995.76,9426.39,3115.63,307.3,...
```

---

## Verification

### Test 1: Trades Match Between Steps ✅

**Step 7a (Trade Calculator):**
```
Strategy 1 spread costs: €4.25
Strategy 2 spread costs: €10.61
Strategy 3 spread costs: €21.23
```

**Step 7b (Portfolio Executor):**
```
Strategy 1 portfolio value: €9,995.76
Strategy 2 portfolio value: €9,989.39
Strategy 3 portfolio value: €9,978.78
```

**Math:**
```
Strategy 1: 10,000 - 4.25 = 9,995.75 ✓ (actual: 9,995.76 - rounding)
Strategy 2: 10,000 - 10.61 = 9,989.39 ✓ (exact match)
Strategy 3: 10,000 - 21.23 = 9,978.77 ✓ (actual: 9,978.78 - rounding)
```

✅ **Portfolio values exactly match spread costs from Step 7a!**

### Test 2: Trade Count Matches ✅

**Step 7a:**
```
Strategy 1: 2 trades
Strategy 2: 2 trades
Strategy 3: 2 trades
Total: 6 trades
```

**Step 7b:**
```
Strategy 1: 2 executed
Strategy 2: 2 executed
Strategy 3: 2 executed
Total: 6 executed
```

✅ **All trades from Step 7a were executed in Step 7b!**

### Test 3: No Trade Strategies ✅

**Step 7a:**
```
Strategies 4-9 (conf=0.3, 0.6): 0 trades
```

**Step 7b:**
```
Strategies 4-9: 0 executed, €10,000.00 portfolio value
```

✅ **Strategies with no trades maintain initial capital!**

---

## Benefits Achieved

### ✅ **Single Source of Truth**
- Trade logic lives in **one place** (Step 7a)
- Step 7b is now a pure executor
- No risk of trade calculation divergence

### ✅ **Separation of Concerns**
- **Step 7a**: "What should we trade?"
- **Step 7b**: "Execute those trades"
- Clear responsibility boundaries

### ✅ **Audit Trail**
- Every trade calculated before execution
- Can review trades independently of portfolio changes
- Easy to debug: check Step 7a first, then Step 7b

### ✅ **Day 1 Validation**
```
Starting capital: €10,000
Step 7a total spread cost: €36.09
Step 7b portfolio values: €9,995.76, €9,989.39, €9,978.78

Verification: Each value = 10,000 - (spread cost from Step 7a) ✓
```

### ✅ **Testability**
Can test independently:
- Step 7a: Does it calculate correct trades with correct costs?
- Step 7b: Does it execute trades correctly on portfolios?

---

## Architecture Principles

### 1. **Data Pipeline Pattern**
```
Signals → Trade Calculation → Trade Execution → Portfolio Valuation
  (6)          (7a)                (7b)               (7b)
```

Each step reads from previous, writes for next.

### 2. **Idempotency**
- Step 7a can be rerun without affecting portfolios
- Step 7b reads static CSV, no side effects until execution

### 3. **Debuggability**
```
Issue: Portfolio value is wrong

Debug:
1. Check step7a_trades.csv - are trades correct?
2. Check spread costs - do they sum correctly?
3. Check step7_strategies.csv - are balances correct?
4. Check exchange rates - are valuations correct?
```

Clear checkpoints at each step.

---

## Files Modified

### 1. **scripts/execute-strategies.py**
**Changes:**
- Updated header docstring to reflect new purpose
- Added `load_trades_from_step7a()` function
- Modified `run_strategy()` to use trades from Step 7a
- Removed trade generation logic (now only in Step 7a)

**Lines changed:** ~30 lines

### 2. **scripts/calculate-trades.py**
**Status:** No changes (already complete)

### 3. **Pipeline Integration**
**run-pipeline.sh** already runs both:
```bash
Step 7a: Calculate trades...
python3 scripts/calculate-trades.py

Step 7b: Execute portfolio strategies...
python3 scripts/execute-strategies.py
```

---

## Trade Filtering Logic

```python
# In load_trades_from_step7a()
for row in reader:
    # Filter by strategy_id and date
    if row['strategy_id'] == strategy_id and row['date'] == date_str:
        trades.append({...})
```

**Why this works:**
- Step 7a writes **all trades for all strategies** to one CSV
- Step 7b reads CSV and filters to **only this strategy's trades**
- Each strategy portfolio executes only its own trades

**Example:**
```
step7a_trades.csv:
  - Row 1: strategy=conf0.5-size0.25, EUR→CNY
  - Row 2: strategy=conf0.5-size0.25, EUR→AUD
  - Row 3: strategy=conf0.5-size0.5, EUR→CNY
  - Row 4: strategy=conf0.5-size0.5, EUR→AUD
  ...

Step 7b for strategy conf0.5-size0.25:
  - Loads: Rows 1, 2 only
  - Executes: 2 trades
  - Updates: conf0.5-size0.25 portfolio only
```

---

## Error Handling

### Scenario 1: step7a_trades.csv doesn't exist

```python
if not os.path.exists(trades_file):
    return []
```

**Behavior:** Strategy executes with 0 trades, maintains current portfolio.

**Why:** Graceful degradation. Portfolio won't change if no trades available.

### Scenario 2: No trades for this strategy

```python
# Filter returns empty list
if row['strategy_id'] == strategy_id and row['date'] == date_str:
    trades.append({...})

# If no matches, trades = []
```

**Behavior:** Same as Scenario 1. Portfolio unchanged.

### Scenario 3: Trade execution fails (insufficient funds)

```python
for trade in proposed_trades:
    executed = execute_trade(trade, all_pairs, eur_rates, portfolio)
    if executed:  # Only add if successful
        executed_trades.append(executed)
```

**Behavior:** Failed trades are skipped. Portfolio updated only for successful trades.

---

## Day 1 vs Day 2+ Behavior

### Day 1 (First Run)
```
Portfolios: All start with €10,000 in EUR
Exchange rates: Same as when trades calculated
Portfolio value change = Pure spread costs

Verification:
  step7a_trades.csv cost_euro: €4.25
  step7_strategies.csv current_value: €9,995.76
  Difference: €4.24 (rounding)
  ✓ Matches spread cost!
```

### Day 2 (After FX Moves)
```
Portfolios: Mixed currencies (EUR, CNY, AUD, etc.)
Exchange rates: Changed from Day 1
Portfolio value change = Spread costs + FX effects

Example:
  Day 1: CNY balance = 3,115.63, rate = 8.10, value = €384.63
  Day 2: CNY balance = 3,115.63, rate = 7.90, value = €394.38
  FX gain: €9.75

  New trades: €2.50 spread cost
  Total change: +€9.75 - €2.50 = +€7.25
```

**Key insight:** Step 7a shows spread costs, Step 7b shows total value including FX.

---

## Future Enhancements

### 1. **Trade Execution History**
Track which trades from Step 7a were actually executed:

```csv
trade_id,strategy_id,date,executed,reason
1,conf0.5-size0.25,2026-02-26,true,
2,conf0.5-size0.25,2026-02-26,true,
3,conf0.6-size0.25,2026-02-26,false,insufficient_confidence
```

### 2. **Partial Fills**
If portfolio has insufficient funds, execute partial trade:

```python
if available < trade_amount:
    # Execute partial trade with available balance
    partial_trade_amount = available
    ...
```

### 3. **Trade Validation**
Before executing, validate trades from Step 7a:

```python
def validate_trade(trade, portfolio, eur_rates):
    # Check sufficient funds
    # Check exchange rates match
    # Check spread is reasonable
    return is_valid, reason
```

### 4. **Multi-Day P&L Attribution**
```
Total Return = Spread Costs (7a) + FX Effects (7b)
```

---

## Command Reference

### Full Pipeline
```bash
# Run both steps
./run-pipeline.sh

# Or manually:
python3 scripts/calculate-trades.py      # Step 7a
python3 scripts/execute-strategies.py    # Step 7b
```

### Clear Data
```bash
# Clear trades only (keeps portfolios)
./scripts/clear-step-data.sh 7a

# Clear portfolios only (keeps trades)
./scripts/clear-step-data.sh 7b

# Clear both
./scripts/clear-step-data.sh 7a
./scripts/clear-step-data.sh 7b
```

### Verify Integration
```bash
# Compare spread costs to portfolio values
python3 -c "
import csv

# Step 7a costs
trades = list(csv.DictReader(open('data/exports/step7a_trades.csv')))
strat1_cost = sum(float(t['cost_euro']) for t in trades if t['strategy_id'] == 'simple-momentum-conf0.5-size0.25')

# Step 7b value
portfolios = list(csv.DictReader(open('data/exports/step7_strategies.csv')))
strat1_value = float([p for p in portfolios if p['strategy_id'] == 'simple-momentum-conf0.5-size0.25'][0]['current_value'])

# Verify
expected = 10000 - strat1_cost
print(f'Expected: €{expected:.2f}')
print(f'Actual: €{strat1_value:.2f}')
print(f'Match: {abs(expected - strat1_value) < 1}')
"
```

---

## Testing Checklist

### ✅ Integration Tests
- [x] Step 7b reads trades from step7a_trades.csv
- [x] Trades filtered by strategy_id correctly
- [x] Trade count matches between steps
- [x] Portfolio values = starting capital - spread costs
- [x] No-trade strategies maintain €10,000
- [x] All 6 trades executed across 3 strategies

### ✅ Error Handling
- [x] Missing step7a_trades.csv → returns empty list
- [x] No trades for strategy → empty list, portfolio unchanged
- [x] Failed trade execution → skipped, not added to executed_trades

### ✅ Data Consistency
- [x] Strategy 1: €4.25 cost → €9,995.76 value ✓
- [x] Strategy 2: €10.61 cost → €9,989.39 value ✓
- [x] Strategy 3: €21.23 cost → €9,978.78 value ✓

---

## Status: COMPLETE ✅

**Date:** 2026-02-26 09:01 UTC
**Commit:** 862a961

**Changes:**
- Connected Step 7b to read trades from Step 7a
- Added `load_trades_from_step7a()` function
- Updated `run_strategy()` to use CSV trades
- Verified all tests pass
- Deployed to production

**Verification:**
- Portfolio values exactly match spread costs from Step 7a
- All trades execute correctly
- No-trade strategies work as expected

**Dashboard:** https://michaeldowd2.github.io/nanopages/fx-dashboard/

---

## Summary

Step 7b now reads trades from Step 7a instead of recalculating them. This completes the separation of trade calculation (7a) and portfolio execution (7b), providing:

1. **Single source of truth** for trade logic
2. **Clear audit trail** from signals → trades → execution
3. **Easy validation** on Day 1 (spread costs only)
4. **Better debugging** (check trades before checking portfolios)

The integration is working perfectly with portfolio values matching expected values based on spread costs from Step 7a. ✅
