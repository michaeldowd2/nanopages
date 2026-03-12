# Skill: spot-check-pipeline-data

Validate pipeline data quality by running automated spot checks after pipeline execution.

## Purpose

Detects common data quality issues early in the pipeline:
- **Duplicate rates across dates**: Exchange rates identical to previous day (stale API data)
- **Missing data**: Expected files or records not present
- **Schema violations**: Incorrect columns or data types
- **Anomalies**: Extreme values or unexpected patterns

## When to Use

Run this immediately after pipeline execution to catch issues before they propagate downstream:
1. After Step 1 (exchange rates) - detect stale data
2. After Step 3 (news) - verify article counts
3. After Step 9 (portfolios) - validate strategy results
4. Before deployment - final validation

## Usage

```bash
cd /workspace/group/fx-portfolio
python3 scripts/validation/spot-check-pipeline-data.py --date 2026-03-12
```

Or run all checks:
```bash
python3 scripts/validation/spot-check-pipeline-data.py --date 2026-03-12 --all
```

## Checks Performed

### 1. Duplicate Exchange Rates
Compares today's rates with previous day:
- ✓ Pass: Rates differ (normal market movement)
- ✗ Fail: All rates identical (stale API data)
- ⚠️ Warn: >90% rates identical (suspicious)

### 2. Data Completeness
Verifies expected data volumes:
- Exchange rates: 121 rows (11×11 currency matrix)
- News articles: 10-100 articles expected
- Signals: At least 2× article count
- Portfolios: 9 strategies expected

### 3. Value Ranges
Checks for anomalous values:
- Exchange rates: 0.01 to 1000 (reasonable range)
- Portfolio values: Within 50-200% of starting value
- Confidence scores: 0.0 to 1.0

### 4. Temporal Consistency
- Dates in sequential order
- No future dates
- No gaps in time series

## Output

Returns status code:
- **0**: All checks passed ✓
- **1**: Critical failures ✗ (stop deployment)
- **2**: Warnings only ⚠️ (proceed with caution)

Logs to: `data/validation/spot-check-YYYY-MM-DD.json`

## Auto-Retry on Stale Data

If duplicate rates detected, the script can:
1. Wait 60 seconds for API to update
2. Retry Step 1 with cache-busting
3. Re-run dependent steps if needed

Enable with: `--auto-retry`

## Example Output

```
============================================================
Pipeline Data Spot Check - 2026-03-12
============================================================

[1/4] Checking exchange rates...
   ✗ FAIL: Duplicate rates detected
   EUR/USD: 1.162041 (same as 2026-03-11)
   GBP/USD: 0.864702 (same as 2026-03-11)
   100% of rates unchanged - likely stale API data

[2/4] Checking data completeness...
   ✓ PASS: 121 exchange rates (expected)
   ✓ PASS: 54 news articles (within range)
   ✓ PASS: 108 signals generated

[3/4] Checking value ranges...
   ✓ PASS: All rates within normal range
   ✓ PASS: Portfolio values reasonable

[4/4] Checking temporal consistency...
   ✓ PASS: No future dates
   ✓ PASS: Sequential order maintained

============================================================
Result: CRITICAL FAILURES DETECTED
Exit code: 1
============================================================

Recommendation: Re-run Step 1 with date-specific API endpoint
```

## Integration with Pipeline

Add to scheduled task:
```bash
# Run pipeline
python3 scripts/pipeline/fetch-exchange-rates.py --date $DATE

# Spot check data
if ! python3 scripts/validation/spot-check-pipeline-data.py --date $DATE --check rates; then
    echo "⚠️ Stale data detected, retrying with date-specific endpoint..."
    python3 scripts/pipeline/fetch-exchange-rates.py --date $DATE --force-date-endpoint
fi

# Continue with remaining steps...
```

## Notes

- Spot checks are **fast** (<1 second)
- Non-destructive (read-only)
- Logs all findings for debugging
- Can be run standalone or integrated into pipeline
- Supports custom check thresholds via config

## Related Files

- `/scripts/validation/spot-check-pipeline-data.py` - Implementation
- `/config/validation_rules.json` - Check thresholds
- `/data/validation/` - Check results log
