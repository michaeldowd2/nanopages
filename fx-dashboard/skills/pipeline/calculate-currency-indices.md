# Skill: calculate-currency-indices

Generate currency strength indices using geometric mean methodology.

---

## Purpose

Calculate currency indices to measure individual currency strength independent of trading pairs. Uses geometric mean to properly isolate each currency's movement. Used by realization checker to determine if predicted movements occurred.

**Implementation Date**: 2026-02-22

---

## Quick Start

```bash
cd /workspace/group/fx-portfolio
python3 scripts/pipeline/calculate-currency-indices.py
```

**Output**: `/data/indices/{CURRENCY}_index.json`

---

## Expected Output

### Output Files

**Primary Output**: `/data/indices/{CURRENCY}_index.json` (one file per currency)
- Format: JSON
- Updated: Appended daily
- Size: ~10-20 KB per currency (30 days of data)

**CSV Export**: `/data/exports/step2_indices.csv`
- Format: CSV for dashboard visualization
- Contains all currencies × all dates

### Output Schema

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| date | string | Trading date (YYYY-MM-DD) | 2026-02-23 |
| currency | string | ISO currency code | USD |
| index | float | Normalized index value (base = 100) | 102.35 |
| prev_index | float | Previous day's index | 100.00 |
| daily_change_pct | float | Daily percentage change | 2.35 |
| base_date | string | Base date for normalization | 2026-02-22 |
| pairs_count | integer | Number of pairs used in calculation | 10 |
| calculation_method | string | Method used | geometric_mean |

### Sample Output

```json
{
  "currency": "USD",
  "calculation_method": "geometric_mean",
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
      "index": 102.35,
      "prev_index": 100.0,
      "daily_change_pct": 2.35,
      "base_date": "2026-02-22",
      "pairs_count": 10,
      "calculation_method": "geometric_mean"
    }
  ]
}
```

### Interpretation

- **index > 100**: Currency has strengthened since base date
- **index < 100**: Currency has weakened since base date
- **daily_change_pct**: Positive = strengthening, negative = weakening
- **Typical range**: 95-105 over a 30-day period (5% movement)
- **Use this data to**: Check signal realization by comparing predicted vs actual currency movements

---

## Methodology: Geometric Mean

### Why Geometric Mean?

**The Problem with Simple EUR-Based Ratios**:
```
USD_index = (base_EUR/USD / current_EUR/USD) × 100
```

This captures:
- USD movement (desired)
- EUR movement (contamination)

**Solution**: Use geometric mean across all pairs where currency is denominator.

### Mathematical Foundation

For each currency (e.g., USD):

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

When averaged across many currencies, the movements of other currencies (EUR, GBP, JPY, etc.) cancel out statistically, leaving only the isolated movement of the target currency.

**Result**: Index represents pure currency movement, independent of trading pairs.

---

## Output Files

### 1. Per-Currency Index Files

**Location**: `/workspace/group/fx-portfolio/data/indices/{CURRENCY}_index.json`

**Example**: `USD_index.json`
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

**Location**: `/workspace/group/fx-portfolio/data/exports/step2_indices.csv`

**Columns**:
- `date` - Date (YYYY-MM-DD)
- `currency` - Currency code (EUR, USD, etc.)
- `index` - Normalized index value (base = 100)
- `prev_index` - Previous day's index
- `daily_change_pct` - Daily percentage change
- `base_date` - Base date for normalization
- `pairs_count` - Number of pairs used in calculation
- `calculation_method` - "geometric_mean"

### 3. Validation File

**Location**: `/workspace/group/fx-portfolio/data/exports/step2_indices_validation.json`

Shows exactly how each index was calculated for the latest date:

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

---

## Daily Workflow

```bash
cd /workspace/group/fx-portfolio
python3 scripts/pipeline/calculate-currency-indices.py
```

**Output**:
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

## Advantages of Geometric Mean

1. **Isolates Currency Movement**
   - Removes contamination from trading pairs
   - EUR/USD rise = pure USD strength signal

2. **Standard Methodology**
   - Same approach as DXY (US Dollar Index)
   - Same approach as EXY (Euro Currency Index)
   - Used by central banks worldwide

3. **Mathematically Sound**
   - Geometric mean = multiplicative average
   - Appropriate for ratios (exchange rates)
   - Maintains proportional relationships

4. **Equal Treatment**
   - All currencies weighted equally
   - No bias toward major currencies

5. **Transparent & Auditable**
   - Validation file shows exact calculation
   - Can verify each pair's contribution

---

## Dependencies

- **fetch-exchange-rates**: Requires EUR pair prices

---

## Next Steps

After running this step:
```bash
# fetch-news: Aggregate news
python3 scripts/pipeline/fetch-news.py

# Or run full pipeline
```

---

## Debugging

Check CSV export:
```bash
python3 scripts/deployment/export-pipeline-data.py
cat data/exports/step2_indices.csv
```

Verify calculation method:
```bash
cat data/indices/USD_index.json | grep calculation_method
# Should show: "geometric_mean"
```

---

## Troubleshooting

### Issue: Missing pairs in calculation

**Symptom**: `pairs_count` less than 10 for a currency

**Cause**: Missing price data from fetch-exchange-rates

**Solution**:
- Verify fetch-exchange-rates ran successfully
- Check `/data/prices/fx-rates-{date}.json` has all currencies

### Issue: Index values seem incorrect

**Symptom**: Index moves opposite to expected direction

**Solution**:
- Check validation file to see calculation details
- Verify pairs were normalized correctly (inverted when needed)
- Review geometric mean inputs

---

## Notes

- Runs daily after fetch-exchange-rates
- Needs 7-14 days of history for meaningful realization checks
- All 11 currencies get indices
- Significant improvement over simple EUR-based ratios
