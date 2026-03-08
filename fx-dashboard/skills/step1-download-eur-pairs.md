# Skill: step1-download-eur-pairs

Download EUR-based exchange rates for all tracked currencies using the GitHub Currency API.

---

## Purpose

Fetch real-time exchange rates from external API. This is the foundation data for the entire pipeline.

**Data Source**: GitHub Currency API (free, no API key required)

---

## Quick Start

```bash
cd /workspace/group/fx-portfolio
python3 scripts/fetch-exchange-rates.py
```

**Output**: `/data/prices/fx-rates-{date}.json`

---

## API Details

### Source

- **Repository**: https://github.com/fawazahmed0/exchange-api
- **Cost**: Free
- **API Key**: Not required
- **Rate Limits**: None
- **Update Frequency**: Daily
- **Coverage**: 200+ currencies including major fiat, emerging markets, crypto, and metals

### Endpoints

**Primary** (CDN-backed):
```
https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/eur.json
```

**Fallback** (Cloudflare Pages):
```
https://latest.currency-api.pages.dev/v1/currencies/eur.json
```

### Fallback Strategy

1. **Try Primary CDN** (fast, global distribution)
2. **Fall back to Cloudflare Pages** (if CDN fails)
3. **Final fallback to mock data** (only if both APIs fail - logs warning)

---

## Output Format

```json
{
  "timestamp": "2026-02-23T10:00:00Z",
  "base": "EUR",
  "rates": {
    "USD": 1.18290676,
    "GBP": 0.87451988,
    "JPY": 182.46884181,
    "CHF": 0.91263474,
    "AUD": 1.67173377,
    "CAD": 1.61632137,
    "NOK": 11.24769343,
    "SEK": 10.67358356,
    "CNY": 8.16992815,
    "MXN": 20.2907358
  },
  "pairs": {
    "EUR/USD": 1.183,
    "USD/JPY": 154.32,
    "GBP/USD": 1.352,
    ... (121 total pairs = 11 × 11)
  }
}
```

**How cross-rates are calculated:**
- USD/JPY = EUR/JPY ÷ EUR/USD
- GBP/USD = EUR/USD ÷ EUR/GBP
- All pairs calculated from EUR base rates

---

## Verifying Data Source

Check that real API data is being used (not mock):

```bash
# Check today's log
cat data/logs/$(date +%Y-%m-%d).json | grep data_source

# Should show:
# "data_source": "github-currency-api"

# NOT:
# "data_source": "mock-data-fallback"
```

View fetched rates:
```bash
cat data/prices/fx-rates-$(date +%Y-%m-%d).json | head -20
```

---

## Monitoring

The script logs:
- **Data source** (`github-currency-api` or `mock-data-fallback`)
- **API date** (date of rates from API)
- **Currencies fetched** (should be 11 for standard config)
- **Endpoint used** (primary CDN or fallback)

Logs location: `/workspace/group/fx-portfolio/data/logs/YYYY-MM-DD.json`

---

## Troubleshooting

### Issue: Mock data fallback triggered

**Symptom**: Log shows `"data_source": "mock-data-fallback"`

**Causes**:
- Network connectivity issues
- API temporarily unavailable
- Request timeout (>10 seconds)

**Solution**:
- Check network: `curl https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/eur.json`
- Wait a few minutes and retry
- API has been very reliable, so this should be rare

### Issue: Missing currencies

**Symptom**: Some currencies not in output

**Solution**:
- Verify currency codes in `config/system_config.json`
- Check they use uppercase codes (USD not usd)
- Verify API supports the currency (check API docs)

### Issue: Old exchange rates

**Symptom**: Rates don't match current market

**Solution**:
- API updates daily, not real-time
- Check API date in log file
- For hourly/minute data, would need paid API

---

## Export to Dashboard

After fetching rates, export to CSV for dashboard:

```bash
python3 scripts/export-pipeline-data.py
```

Dashboard file: `site_data/step1_exchange_rates_matrix.csv`

---

## Dependencies

- None (Step 1 is the starting point)
- Uses Python standard library only (`urllib.request`, `json`)
- No external packages needed

---

## Next Steps

After running Step 1:
```bash
# Step 2: Calculate currency indices
python3 scripts/calculate-currency-indices.py

# Or run full pipeline date
# (runs all steps for a specific date)
```

---

## Notes

- **Runs daily**: Designed to fetch once per day
- **Stores one file per day**: `fx-rates-YYYY-MM-DD.json`
- **Real API data**: No longer using mock data (as of 2026-02-23)
- **No authentication**: Simpler code, fewer failure points
- **Free forever**: Open-source community project

---

## Benefits vs Alternatives

**vs Mock Data** (previous implementation):
- ✅ Real market rates (updated daily)
- ✅ Reflects actual FX movements
- ✅ No manual updates needed

**vs Commercial APIs** (Fixer.io, Alpha Vantage, etc.):
- ✅ No cost
- ✅ No API key or signup
- ✅ No rate limits
- ✅ Simpler integration

**Trade-offs**:
- ⚠️ Daily updates only (not real-time)
- ⚠️ Community-maintained (not enterprise SLA)
- ✅ But: sufficient for daily FX signals pipeline

---

## Quick Reference

```bash
# Fetch today's rates
python3 scripts/fetch-exchange-rates.py

# Verify data source
cat data/logs/$(date +%Y-%m-%d).json | grep data_source

# View rates
cat data/prices/fx-rates-$(date +%Y-%m-%d).json

# Export to dashboard
python3 scripts/export-pipeline-data.py
```
