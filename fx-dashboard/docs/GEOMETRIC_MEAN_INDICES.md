# Geometric Mean Currency Indices

## Overview

Enhanced currency index calculation using **geometric mean** methodology to properly isolate each currency's movement independent of trading pairs.

**Implementation Date:** 2026-02-22

---

## The Problem with Simple EUR-Based Indices

**Original approach (deprecated):**
```
USD_index = (base_EUR/USD / current_EUR/USD) × 100
```

**Issue:** This captures:
- ✅ USD movement (what we want)
- ❌ EUR movement (contamination)

When EUR/USD rises, it could mean:
1. USD strengthened (desired signal)
2. EUR weakened (noise)
3. Both moved (mixed signal)

**Result:** Cannot distinguish USD movement from EUR movement.

---

## Solution: Geometric Mean Method

### Mathematical Foundation

**For each currency (e.g., USD), calculate:**

1. **Get all pairs with USD in denominator:**
   ```
   EUR/USD, GBP/USD, JPY/USD, CHF/USD, AUD/USD, CAD/USD, NOK/USD, SEK/USD, CNY/USD, MXN/USD
   ```

2. **Calculate geometric mean:**
   ```
   USD_index_raw = (EUR/USD × GBP/USD × JPY/USD × ... × MXN/USD)^(1/10)
   ```

3. **Normalize to base date:**
   ```
   USD_index = (USD_index_raw / USD_base_index) × 100
   ```

4. **Daily change:**
   ```
   USD_daily_change = ((USD_index_today / USD_index_yesterday) - 1) × 100
   ```

### Why This Works

Let's say:
- EUR has intrinsic value change = `e`
- USD has intrinsic value change = `u`
- GBP has intrinsic value change = `g`
- JPY has intrinsic value change = `j`

Then exchange rates reflect:
- EUR/USD ≈ e - u
- GBP/USD ≈ g - u
- JPY/USD ≈ j - u

**Geometric mean:**
```
[(e-u) × (g-u) × (j-u) × ...]^(1/n)
```

When averaged across many currencies:
- The `e`, `g`, `j` terms cancel out (average to zero)
- What remains: `-u` (isolated USD movement) ✅

**Result:** Currency index represents pure USD movement, independent of EUR, GBP, JPY, etc.

---

## Implementation

### Script

**Location:** `/workspace/group/fx-portfolio/scripts/calculate-currency-indices.py`

**Usage:**
```bash
python3 scripts/calculate-currency-indices.py
```

### Key Functions

#### `calculate_geometric_mean(values)`
Calculates geometric mean: `(v1 × v2 × ... × vn)^(1/n)`

#### `calculate_currency_index_geometric(currency, all_pairs, base_all_pairs)`
For a given currency:
1. Extract all pairs where currency is denominator
2. Normalize pairs (invert if needed)
3. Calculate geometric mean
4. Normalize to base date

**Example for USD:**
```python
# Get all pairs: EUR/USD, GBP/USD, JPY/USD, etc.
rates = []
for other in ['EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NOK', 'SEK', 'CNY', 'MXN']:
    # Normalize so USD is denominator
    rate = all_pairs[other]['USD']  # e.g., EUR/USD
    rates.append(rate)

# Geometric mean
usd_index_raw = (rates[0] × rates[1] × ... × rates[9]) ** (1/10)

# Normalize to base
usd_index = (usd_index_raw / base_usd_index) × 100
```

---

## Output Files

### 1. Per-Currency Index Files

**Location:** `/workspace/group/fx-portfolio/data/indices/{CURRENCY}_index.json`

**Example:** `USD_index.json`
```json
{
  "currency": "USD",
  "calculation_method": "geometric_mean",
  "note": "Index isolates currency movement using geometric mean of all pairs",
  "base_date": "2026-02-22",
  "data": [
    {
      "date": "2026-02-22",
      "currency": "USD",
      "index": 100.0,
      "prev_index": null,
      "daily_change_pct": null,
      "base_date": "2026-02-22",
      "pairs_count": 10,
      "calculation_method": "geometric_mean"
    },
    {
      "date": "2026-02-23",
      "currency": "USD",
      "index": 102.3456,
      "prev_index": 100.0,
      "daily_change_pct": 2.3456,
      "base_date": "2026-02-22",
      "pairs_count": 10,
      "calculation_method": "geometric_mean"
    }
  ]
}
```

### 2. CSV Export (For Dashboard)

**Location:** `/workspace/group/fx-portfolio/data/exports/step2_indices.csv`

**Columns:**
- `date` - Date (YYYY-MM-DD)
- `currency` - Currency code (EUR, USD, etc.)
- `index` - Normalized index value (base = 100)
- `prev_index` - Previous day's index
- `daily_change_pct` - Daily percentage change
- `base_date` - Base date for normalization
- `pairs_count` - Number of pairs used in calculation
- `calculation_method` - "geometric_mean"

**Use case:** Loaded in dashboard Step 2 tab for visualization

### 3. Validation File (Calculation Details)

**Location:** `/workspace/group/fx-portfolio/data/exports/step2_indices_validation.json`

**Purpose:** Shows exactly how each index was calculated for the latest date

**Example for USD:**
```json
{
  "currency": "USD",
  "date": "2026-02-22",
  "index": 100.0,
  "pairs_used": [
    {
      "pair": "EUR/USD",
      "original_rate": 1.18,
      "normalized_rate": 1.18,
      "inverted": false
    },
    {
      "pair": "GBP/USD",
      "original_rate": 1.3501,
      "normalized_rate": 1.3501,
      "inverted": false
    },
    {
      "pair": "JPY/USD",
      "original_rate": 154.6102,
      "normalized_rate": 0.006467,
      "inverted": true
    }
  ],
  "pairs_count": 10,
  "geometric_mean_inputs": [1.18, 1.3501, 0.006467, ...]
}
```

**Use case:** Validate calculation, debug discrepancies, audit methodology

---

## Validation in Dashboard

The Step 2 tab shows:
- **Index values** for each currency
- **Daily changes** (%)
- **Pairs used** in calculation
- **Calculation method** (geometric_mean)

Users can validate:
1. ✅ Index value is correct
2. ✅ Daily change makes sense
3. ✅ All 10 pairs were used
4. ✅ Pairs were normalized correctly (inverted when needed)

---

## Advantages of Geometric Mean Method

### 1. **Isolates Currency Movement**
- Removes contamination from trading pairs
- EUR/USD rise = pure USD strength signal
- No need to "remove EUR influence" manually

### 2. **Standard Methodology**
- Same approach as DXY (US Dollar Index)
- Same approach as EXY (Euro Currency Index)
- Used by central banks worldwide

### 3. **Mathematically Sound**
- Geometric mean = multiplicative average
- Appropriate for ratios (exchange rates)
- Maintains proportional relationships

### 4. **Equal Treatment**
- All currencies weighted equally (for now)
- No bias toward major currencies
- Can add trade weights later if desired

### 5. **Transparent & Auditable**
- Validation file shows exact calculation
- Can verify each pair's contribution
- Easy to spot errors or anomalies

---

## Comparison: Old vs New Method

### Old Method (EUR-Based)
```python
# Simple ratio to EUR
usd_index = (base_eur_usd / current_eur_usd) × 100
```

**Issues:**
- ❌ Captures EUR movement
- ❌ Single pair dependency
- ❌ EUR weakness looks like USD strength

### New Method (Geometric Mean)
```python
# Geometric mean of all pairs
rates = [eur_usd, gbp_usd, jpy_usd, chf_usd, aud_usd, cad_usd, nok_usd, sek_usd, cny_usd, mxn_usd]
usd_index_raw = (∏ rates) ^ (1/10)
usd_index = (usd_index_raw / base_index) × 100
```

**Benefits:**
- ✅ Isolates USD movement
- ✅ Uses all 10 pairs
- ✅ EUR effect cancels out

---

## Daily Workflow

### Run Index Calculation

```bash
cd /workspace/group/fx-portfolio
python3 scripts/calculate-currency-indices.py
```

**Output:**
```
Loading 30 days of historical prices...
✓ Loaded 10 days of data
Base date: 2026-02-13
Latest date: 2026-02-22

Calculating geometric mean indices for 11 currencies...
  ✓ EUR: 10 days
  ✓ USD: 10 days
  ...

Latest Indices (2026-02-22):
Currency        Index   Daily Δ%    Pairs
------------------------------------------------------------
EUR          98.7654     -0.36%       10
USD         102.3456      1.10%       10
GBP         101.2345      0.52%       10
JPY          99.8765     -0.21%       10
...
```

---

## Future Enhancements

### 1. **Trade-Weighted Indices**
Instead of equal weights, use actual trade volumes:
```python
usd_index = (eur_usd^w1 × gbp_usd^w2 × jpy_usd^w3 × ...)^(1/Σw)
```

Where `w1, w2, w3` = trade weights from BIS/IMF data

### 2. **Real-Time Updates**
Calculate indices intraday as new rates arrive

### 3. **Historical Rebase**
Allow changing base date to analyze different time periods

### 4. **Index Comparison**
Compare synthetic indices against official indices (DXY, EXY) to validate methodology

---

## References

**Official Currency Indices:**
- DXY (US Dollar Index) - ICE
- EXY (Euro Currency Index) - TradingView
- BIS Effective Exchange Rates
- ECB Euro Effective Exchange Rate

**Methodology:**
- BIS: "Calculating Effective Exchange Rates and ULC-based Competitiveness Indicators"
- Federal Reserve: "Trade Weighted US Dollar Index"
- ECB: "The ECB's Enhanced Effective Exchange Rates"

---

## Summary

The geometric mean method provides **professional-quality synthetic indices** that:
- ✅ Properly isolate each currency's movement
- ✅ Use standard methodology (same as DXY/EXY)
- ✅ Work for all 11 currencies
- ✅ Provide full transparency via validation files
- ✅ Support daily updates without external dependencies

This is a **significant improvement** over simple EUR-based ratios and provides the foundation for accurate realization checking in Step 6.
