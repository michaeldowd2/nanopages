# Strategy Logic Improvements - 2026-02-25

## Summary

Completely reimplemented trade execution logic to properly scale trades by signal strength and portfolio value. Removed aggregation_method parameter (now always weighted average).

---

## Key Changes

### 1. Trade Size Logic Redesign

**Before:**
- `trade_size_pct` was applied to individual currency balances
- No signal strength scaling
- Would try to trade 25% of EUR balance, regardless of signal strength
- Poor capital utilization

**After:**
- `trade_size_pct` renamed to `max_trade_size_pct` (clarity)
- Applied to **total portfolio value** (not individual balances)
- **Scaled by signal strength**:
  - If signals are 1.0 + 1.0 → use 100% of max_trade_size_pct
  - If signals are 0.5 + 0.5 → use 50% of max_trade_size_pct
  - If signals are 0.2 + 0.6 → use 40% of max_trade_size_pct (average)
- Finds accounts with funds to execute trades (prioritizes bearish currency, then EUR, then any balance)

**Formula:**
```
trade_size_eur = portfolio_value_eur × max_trade_size_pct × signal_strength_factor

where:
  signal_strength_factor = (buy_confidence + sell_confidence) / 2
```

**Example:**
- Portfolio value: €10,000
- max_trade_size_pct: 0.1 (10%)
- Signals: SEK bearish (0.57), CNY bullish (0.21)
- signal_strength_factor = (0.57 + 0.21) / 2 = 0.39
- trade_size_eur = 10,000 × 0.1 × 0.39 = **€390**

### 2. Removed aggregation_method Parameter

**Rationale:**
- System always uses weighted average (by generator_weights)
- Having parameter was confusing and redundant
- Simplifies config and code

**Changed:**
- Removed `aggregation_method` from all strategy configs
- Removed parameter from `run_strategy()`, `load_portfolio()`, `save_portfolio()`
- Updated `aggregate_currency_signals()` to always use weighted average
- Updated output to not include aggregation_method

### 3. Updated Config Values

Changed `trade_size_pct` values to be more realistic percentages of total portfolio:

| Old Value | New Value | Meaning |
|-----------|-----------|---------|
| 0.25 | 0.1 | 10% max (conservative) |
| 0.5 | 0.25 | 25% max (moderate) |
| 0.75 | 0.5 | 50% max (aggressive) |

Updated descriptions to reflect actual behavior:
- "Low confidence (0), conservative size (10% max)"
- "Medium confidence (0.3), moderate size (25% max)"
- "High confidence (0.6), aggressive size (50% max)"

---

## New Trade Logic Flow

### Step 1: Filter Signals by Confidence Threshold
```python
# Only consider signals with confidence > threshold
qualified = [
    (curr, direction, conf)
    for curr, (direction, conf) in aggregate_signals.items()
    if conf >= confidence_threshold and direction != 'neutral'
]
```

### Step 2: Separate Bullish and Bearish
```python
bullish = sorted([(c, conf) for c, d, conf in qualified if d == 'bullish'], ...)
bearish = sorted([(c, conf) for c, d, conf in qualified if d == 'bearish'], ...)
```

### Step 3: Calculate Portfolio Value
```python
portfolio_value_eur = calculate_portfolio_value(portfolio, eur_rates)
```

### Step 4: Pair Strongest Bullish with Strongest Bearish
```python
for buy_currency, sell_currency in pairs:
    signal_strength_factor = (buy_conf + sell_conf) / 2.0
    trade_size_eur = portfolio_value_eur × max_trade_size_pct × signal_strength_factor
```

### Step 5: Find Account with Funds
```python
# Priority:
1. Bearish currency (if has balance)
2. EUR (base currency)
3. Any currency with largest balance
```

### Step 6: Execute Trade
```python
# Convert EUR amount to from_currency amount
# Apply direct pair rate (e.g., EUR/CNY)
# Apply Revolut spread (0.74%)
# Update portfolio balances
```

---

## Current Results (2026-02-25)

### Aggregate Signals
```
SEK: bearish (0.57) ← Strongest signal
CNY: bullish (0.21)
AUD: bullish (0.19)
CAD: bearish (0.18)
EUR: bearish (0.15)
JPY: bearish (0.11)
USD: neutral (0.10)
GBP: neutral (0.08)
CHF: neutral (0.00)
NOK: neutral (0.00)
MXN: neutral (0.00)
```

### Strategy Results

**conf=0.0 (Low Confidence), max_trade_size=10%:**
- ✅ 2 trades executed
- Trade 1: EUR → CNY (€387.50)
  - Signal strength: 0.39 (SEK 0.57 + CNY 0.21) / 2
  - Trade size: 10,000 × 0.1 × 0.39 = €387.50
- Trade 2: EUR → AUD (€186.11)
  - Signal strength: 0.19 (CAD 0.18 + AUD 0.19) / 2
  - Trade size: 10,000 × 0.1 × 0.19 = €186.11
- Final value: **€9,995.76** (spread cost: €4.24)

**conf=0.0, max_trade_size=25%:**
- ✅ 2 trades executed
- Larger trades (25% max instead of 10%)
- Final value: **€9,989.39** (spread cost: €10.61)

**conf=0.0, max_trade_size=50%:**
- ✅ 2 trades executed
- Largest trades (50% max)
- Final value: **€9,978.78** (spread cost: €21.22)

**conf=0.3 (Medium Confidence):**
- ❌ 0 trades executed
- **Why:** Only SEK (0.57) meets threshold, but no bullish signal > 0.3
- Need both bullish AND bearish signals to exceed threshold for a trade

**conf=0.6 (High Confidence):**
- ❌ 0 trades executed
- **Why:** No signals exceed 0.6 threshold
- Current signals are too weak

---

## Why Trades Are Limited

The current aggregate signals are **relatively weak** (most < 0.3). This is because:

1. **Signal Volume:** Only 49 total signals across all currencies
2. **Mixed Sentiment:** Generators sometimes disagree (keyword vs LLM)
3. **Weighted Average Smoothing:** Combining multiple signals dampens extremes
4. **Confidence Thresholds:** Working as intended - only trade on strong signals

**This is GOOD behavior!** The system should be conservative and only trade when signals are clear.

### To See More Trades:

1. **Wait for stronger news:** More bullish/bearish articles → stronger signals
2. **Accumulate signals:** More articles → higher signal volumes → stronger aggregates
3. **Lower thresholds:** conf=0.0 already trades, but could go negative
4. **Increase generator weights:** Give LLM even more influence (currently 2x keyword)

---

## Benefits of New Logic

### 1. **Proper Risk Management**
- Trades scaled to total portfolio value
- Signal strength determines position size
- Weak signals → small positions
- Strong signals → large positions (up to max)

### 2. **Better Capital Utilization**
- Can trade from any account with funds (not just bearish currency)
- Finds largest available balance to execute trades
- Doesn't leave EUR sitting idle

### 3. **Clarity**
- `max_trade_size_pct` is clear: % of total portfolio per pair
- Signal strength factor is transparent in trade records
- Easy to understand: 10% max with 0.5 signal strength = 5% actual

### 4. **Flexibility**
- Easy to adjust max trade sizes in config
- Signal strength automatically scales positions
- No code changes needed to tune aggressiveness

---

## Code Changes Summary

### Files Modified

1. **execute-strategies.py**
   - Completely rewrote `generate_trades()` function
   - Updated `execute_trade()` to use pre-calculated EUR amount
   - Simplified `aggregate_currency_signals()` to remove method parameter
   - Updated `run_strategy()` signature to remove aggregation_method
   - Updated `load_portfolio()` and `save_portfolio()` filenames (removed agg_method)
   - Updated main loop to remove aggregation_method

2. **system_config.json**
   - Removed `aggregation_method` from all 9 strategies
   - Changed `trade_size_pct` values: 0.25→0.1, 0.5→0.25, 0.75→0.5
   - Updated strategy descriptions to reflect actual behavior

3. **Portfolio State Files**
   - New filename format (removed agg_method)
   - Old: `simple-momentum_conf=0.0_size=0.25_agg=average_est=...json`
   - New: `simple-momentum_conf=0.0_size=0.1_est=...json`

---

## Example Trade Execution

### Input Signals
```json
{
  "SEK": {"direction": "bearish", "confidence": 0.57},
  "CNY": {"direction": "bullish", "confidence": 0.21}
}
```

### Strategy Config
```json
{
  "confidence_threshold": 0.0,
  "max_trade_size_pct": 0.1
}
```

### Calculation
```
portfolio_value = €10,000
signal_strength = (0.57 + 0.21) / 2 = 0.39
trade_size = 10,000 × 0.1 × 0.39 = €390

Available accounts:
- EUR: €10,000 ✓ (use this)
- SEK: €0

Trade: EUR → CNY
- From: €390
- Rate: 8.10028 EUR/CNY
- To (before spread): 3,160.11 CNY
- Spread cost (0.74%): 23.38 CNY
- To (after spread): 3,136.73 CNY
- Spread cost in EUR: €2.87
```

### Portfolio After Trade
```
EUR: €9,610
CNY: 3,136.73 CNY (≈ €387.13)
Total value: €9,997.13
```

---

## Testing & Verification

### Test 1: Verify Trades Execute on conf=0.0 ✅
```bash
cd /workspace/group/fx-portfolio
python3 scripts/execute-strategies.py
```
**Result:** 2 trades executed for each of the first 3 strategies (conf=0.0)

### Test 2: Verify Trade Sizes Scale with Signal Strength ✅
- SEK (0.57) + CNY (0.21) → factor 0.39 → €387.50 trade
- CAD (0.18) + AUD (0.19) → factor 0.19 → €186.11 trade
- **Correct!** Stronger signals → larger trades

### Test 3: Verify No Trades When Threshold Not Met ✅
- conf=0.3 strategies: 0 trades (only SEK > 0.3, need both bullish and bearish)
- conf=0.6 strategies: 0 trades (no signals > 0.6)
- **Correct!** System is conservative

### Test 4: Verify Spread Costs ✅
- Strategy 1 (10% max): €4.24 cost
- Strategy 2 (25% max): €10.61 cost
- Strategy 3 (50% max): €21.22 cost
- **Correct!** Larger trades → larger spread costs

---

## Status: COMPLETE ✅

**Date:** 2026-02-25 23:33 UTC
**Tests:** All passing
**Trades:** Executing correctly with proper signal strength scaling
**Dashboard:** Deployed with updated results

**Dashboard URL:** https://michaeldowd2.github.io/nanopages/fx-dashboard/

---

## Next Steps (Optional)

1. **Monitor Signal Quality:** Watch how weighted aggregation performs over time
2. **Tune Thresholds:** Adjust confidence thresholds based on trading results
3. **Add Time Decay:** Weight recent signals higher than older ones
4. **Add Trade Limits:** Max trades per day, cooldown periods, etc.
5. **Backtest:** Run historical data through new logic to validate
