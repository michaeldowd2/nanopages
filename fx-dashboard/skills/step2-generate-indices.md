# Skill: step2-generate-indices

Generate synthetic currency strength indices from EUR pairs.

## Purpose

Calculate currency indices to measure individual currency strength (not just pairs). Used by realization checker to determine if predicted movements occurred.

## Running This Step

```bash
cd /workspace/group/fx-portfolio
python3 scripts/calculate-currency-indices.py
```

## Output

**Files**: `/data/indices/{CURRENCY}_index.json`

```json
{
  "currency": "USD",
  "base_currency": "EUR",
  "calculation_method": "synthetic_eur_normalized",
  "note": "Higher index = stronger currency relative to base date",
  "data": [
    {
      "date": "2026-02-21",
      "index": 100.0,
      "eur_rate": 1.18,
      "base_rate": 1.18,
      "base_date": "2026-02-20",
      "pct_change": 0.0
    }
  ]
}
```

## Index Calculation

Formula: `index = (base_rate / current_rate) × 100`

- Higher index = stronger currency
- Index = 100 on base date
- If USD strengthens vs EUR, rate decreases, index increases

## Dependencies

- **Step 1**: Requires EUR pair prices

## Next Steps

After running this step, run Step 3 to aggregate news.

## Debugging

Check CSV export:
```bash
python3 scripts/export-pipeline-data.py
cat data/exports/step2_indices.csv
```

## Limitation

Currently uses synthetic indices calculated from EUR pairs. Future improvement: use real currency indices (DXY, EUR TWI, etc.) for more accurate movement tracking.

## Notes

- Runs daily after Step 1
- Needs 7-14 days of history for meaningful realization checks
- All 11 currencies get indices (including EUR itself = always 100)
