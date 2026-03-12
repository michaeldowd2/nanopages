# Exchange Rate Data Sources - Investigation & Solutions

**Date**: 2026-03-12
**Issue**: Pipeline downloaded stale exchange rate data (identical to previous day)

## Problem Identified

The scheduled pipeline run on 2026-03-12 retrieved exchange rates that were **identical** to 2026-03-11:
- EUR/USD: 1.162041 (both days)
- All 121 currency pairs unchanged
- Result: Indices showed 0% change, analysis ran on static market

### Root Cause

**CDN Caching Issue** with GitHub Currency API (`@latest` endpoint):
- The `@latest` tag uses CDN caching that can be stale
- API endpoint: `https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/eur.json`
- The API **does have fresh data**, but CDN served cached version
- Date-specific endpoint (`@2026-03-12`) returns correct, fresh data

### Verification

Testing showed the API has correct data when using date-specific endpoints:
```bash
# Stale (@latest): EUR/USD = 1.162041
curl https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/eur.json

# Fresh (@2026-03-12): EUR/USD = 1.15340737
curl https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@2026-03-12/v1/currencies/eur.json
```

---

## Solutions

### 1. ✅ Use Date-Specific API Endpoints (Recommended)

**Modify fetch-exchange-rates.py** to use date in URL:
```python
# Current (problematic):
CURRENCY_API_PRIMARY = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/eur.json"

# Fixed (cache-busting):
date_str = "2026-03-12"
CURRENCY_API_PRIMARY = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date_str}/v1/currencies/eur.json"
CURRENCY_API_FALLBACK = f"https://{date_str}.currency-api.pages.dev/v1/currencies/eur.json"
```

**Benefits**:
- Bypasses CDN cache completely
- Guarantees correct date data
- Works with historical dates
- Same API, just different URL pattern

**Implementation**: Modify `fetch_eur_rates_from_api()` to accept date parameter

### 2. ✅ Auto-Detection + Retry (Defense in Depth)

**Add spot-check after Step 1**:
```bash
# Run Step 1
python3 scripts/pipeline/fetch-exchange-rates.py --date $DATE

# Spot check for stale data
if ! python3 scripts/validation/spot-check-pipeline-data.py --date $DATE --check rates; then
    echo "⚠️ Stale data detected, retrying..."
    sleep 60  # Wait for API update
    python3 scripts/pipeline/fetch-exchange-rates.py --date $DATE --force-refresh
fi
```

**Benefits**:
- Catches any stale data issues
- Automated recovery
- Logs incidents for debugging

### 3. ✅ Add Alternative Data Source (Fallback)

**Frankfurter API** - Free, no signup, reliable:
```python
# Primary: GitHub Currency API (date-specific)
primary_url = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date_str}/v1/currencies/eur.json"

# Fallback 1: GitHub Currency API (pages.dev)
fallback1_url = f"https://{date_str}.currency-api.pages.dev/v1/currencies/eur.json"

# Fallback 2: Frankfurter API
fallback2_url = f"https://api.frankfurter.dev/v1/{date_str}?base=EUR"
```

**Frankfurter Details**:
- URL: `https://api.frankfurter.dev/`
- **No API key required**
- **No rate limits** ("There are no limits")
- **No signup**
- Historical data: 1999 to present
- All our currencies supported (EUR, USD, GBP, JPY, CHF, AUD, CAD, NOK, SEK, CNY, MXN)
- Format: `{"date":"2026-03-12","base":"EUR","rates":{"USD":1.1547,"GBP":0.86243,...}}`

---

## Alternative Data Sources Evaluated

| Source | Free | No Signup | Our Currencies | Historical | Notes |
|--------|------|-----------|----------------|------------|-------|
| **Frankfurter** | ✅ | ✅ | ✅ All 11 | 1999-present | **Best fallback option** |
| GitHub Currency API | ✅ | ✅ | ✅ All 11 | Multi-year | Current (with fix) |
| ExchangeRate.host | ✅ | ⚠️ API key | ✅ | Yes | Requires registration |
| ForexRateAPI | Free tier | ⚠️ API key | ✅ | Yes | Account needed |
| Fixer.io | Limited free | ⚠️ API key | ✅ | Yes | Credit card for more |
| Open Exchange Rates | Limited free | ⚠️ API key | ✅ | Yes | 1000 req/mo free |

**Recommendation**: Add Frankfurter as third fallback (no dependencies, truly free)

---

## Recommended Implementation Plan

### Phase 1: Quick Fix (Immediate)
1. ✅ Modify `fetch-exchange-rates.py` to use date-specific endpoints
2. ✅ Add spot-check script (already created)
3. Test with today's data

### Phase 2: Validation (Short-term)
1. Integrate spot-check into scheduled pipeline
2. Add retry logic for stale data detection
3. Log all data source switches

### Phase 3: Resilience (Medium-term)
1. Add Frankfurter as third fallback ✅ (completed)
2. Add data quality dashboard
3. Monitor API reliability metrics

---

## Testing Commands

### Test Date-Specific Endpoint
```bash
# GitHub Currency API (date-specific)
curl "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@2026-03-12/v1/currencies/eur.json"

# Frankfurter API
curl "https://api.frankfurter.dev/v1/2026-03-12?base=EUR"
```

### Run Spot Check
```bash
cd /workspace/group/fx-portfolio
python3 scripts/validation/spot-check-pipeline-data.py --date 2026-03-12 --check rates
```

### Download Historical Range
```bash
# Frankfurter time series (for backfill)
curl "https://api.frankfurter.dev/v1/2026-03-01..2026-03-12?base=EUR"
```

---

## Files Modified/Created

### Created
- ✅ `/skills/validation/spot-check-pipeline-data.md` - Validation skill documentation
- ✅ `/scripts/validation/spot-check-pipeline-data.py` - Spot-check implementation
- ✅ `/docs/EXCHANGE_RATE_DATA_SOURCES.md` - This document

### Modified
- ✅ `/scripts/pipeline/fetch-exchange-rates.py` - Now uses date-specific URLs and handles any historical date

---

## Related Resources

- **Frankfurter API**: https://frankfurter.dev/
- **GitHub Currency API**: https://github.com/fawazahmed0/exchange-api
- **API Comparison**: https://exchangerate.host/ (lists alternatives)

---

## Next Steps

1. **Update fetch-exchange-rates.py** to use date-specific endpoints
2. **Test** with current date to verify fresh data
3. **Re-run pipeline** for 2026-03-12 with corrected data
4. **Integrate spot-check** into scheduled task
5. **Monitor** for future occurrences
