# Skill: step1-download-eur-pairs

Download EUR-based exchange rates for all tracked currencies.

## Purpose

Fetch current FX rates from external sources. This is the foundation data for the entire pipeline.

## Running This Step

```bash
cd /workspace/group/fx-portfolio
python3 scripts/fetch-prices.py
```

## Output

**File**: `/data/prices/fx-rates-{date}.json`

```json
{
  "timestamp": "2026-02-21T10:00:00Z",
  "base": "EUR",
  "rates": {
    "USD": 1.18,
    "GBP": 0.874,
    "JPY": 182.44,
    "CHF": 0.912,
    "AUD": 1.67,
    "CAD": 1.61,
    "NOK": 11.25,
    "SEK": 10.68,
    "CNY": 8.14,
    "MXN": 20.31
  }
}
```

## Dependencies

- None (this is Step 1)

## Next Steps

After running this step, run Step 2 to generate synthetic indices.

## Debugging

Check CSV export:
```bash
python3 scripts/export-pipeline-data.py
cat data/exports/step1_eur_pairs.csv
```

## Notes

- Runs daily
- Stores one file per day
- Currently uses manual/mock data - future: integrate with real FX API
