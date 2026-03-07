# What's New: Date Validation & Dependency Checking

**Date**: 2026-02-26

## Summary

The pipeline orchestrator now validates that all upstream dependencies have data for a specific date before running any step. This prevents inconsistent results from incomplete data.

## Key Features

### 🎯 Auto-Detect Latest Date

```bash
# Run Step 7 with the most recent complete data
./scripts/rerun-steps-v2.sh 7 --latest

# Run Step 5 + downstream with latest dates
./scripts/rerun-steps-v2.sh 5 --downstream --latest
```

The system finds the latest date where **ALL** dependencies have data.

### ✅ Validate Specific Dates

```bash
# Run for specific date (validates first)
./scripts/rerun-steps-v2.sh 7 --date 2026-02-25
```

If any dependency is missing for that date, you get a clear error:

```
✗ Step 7 (Trade Calculation): Missing dependencies for 2026-02-26
  • Step 1 (Exchange Rates) missing data for 2026-02-26
    Available dates: 2026-02-25, 2026-02-24
  • Step 4 (Time Horizon Analysis) missing data for 2026-02-26
    Available dates: 2026-02-25

Suggestions:
  • Run missing dependency steps first
  • Use --latest to auto-detect available dates
```

### 🔍 Check Date Availability

```bash
# See what dates are available for Step 7
./scripts/validate-step-dates.py 7
```

Output:
```
Step 7: Trade Calculation
Dependencies: 1, 2, 3, 4, 5, 6

Dependency data availability:
  Step 1 (Exchange Rates): 3 dates available (latest: 2026-02-25)
  Step 2 (Currency Indices): 3 dates available (latest: 2026-02-25)
  Step 3 (News Aggregation): 3 dates available (latest: 2026-02-25)
  Step 4 (Time Horizon Analysis): 2 dates available (latest: 2026-02-25)
  Step 5 (Sentiment Signals): 3 dates available (latest: 2026-02-25)
  Step 6 (Signal Realization): 3 dates available (latest: 2026-02-25)

✓ Latest common date: 2026-02-25
```

## Usage Examples

### Daily Workflow

```bash
# Run the full pipeline for today
./run-pipeline.sh

# Then rerun specific analysis with latest data
./scripts/rerun-steps-v2.sh 5 --downstream --latest
```

### Backfilling Data

```bash
# Check what dates are available
./scripts/validate-step-dates.py 7

# Backfill a specific date
./scripts/rerun-steps-v2.sh 7 --date 2026-02-20

# If it fails, run missing dependencies first
./scripts/rerun-steps-v2.sh 4 --date 2026-02-20
./scripts/rerun-steps-v2.sh 7 --date 2026-02-20
```

### Safe Execution

```bash
# Always validate before running
./scripts/rerun-steps-v2.sh 7 --date 2026-02-25 --dry-run

# Or just use --latest to be safe
./scripts/rerun-steps-v2.sh 7 --latest
```

## How It Works

1. **Scans export files** in `data/exports/` for date patterns
2. **Extracts dates** from filenames and CSV content
3. **Checks all dependencies** (direct + transitive)
4. **Finds intersection** of available dates
5. **Returns latest common date** or validates specific date

## Benefits

✅ **Never run steps with incomplete data**
✅ **Clear error messages** showing exactly what's missing
✅ **Automatic date detection** - no manual tracking needed
✅ **Safe backfilling** - validate before expensive operations
✅ **Better debugging** - instantly see dependency status

## Backward Compatibility

Old behavior still works:

```bash
# Run for all dates (old behavior)
./scripts/rerun-steps-v2.sh 7

# But now you can be more precise:
./scripts/rerun-steps-v2.sh 7 --latest
```

## Documentation

- **Full guide**: `docs/DATE_VALIDATION.md`
- **Architecture**: `docs/PIPELINE_ARCHITECTURE_2026-02-26.md`
- **Tool reference**: Run `./scripts/validate-step-dates.py --help`

## Quick Reference

```bash
# Auto-detect latest date
./scripts/rerun-steps-v2.sh <step> --latest

# Validate specific date
./scripts/rerun-steps-v2.sh <step> --date YYYY-MM-DD

# Check availability
./scripts/validate-step-dates.py <step>

# Find latest date
./scripts/validate-step-dates.py <step> --find-latest

# Dry-run before executing
./scripts/rerun-steps-v2.sh <step> --latest --dry-run
```

## Notes

- Step 9 (Dashboard Deployment) doesn't support date filtering - always deploys all data
- Root steps (1, 3) with no dependencies can run for any date
- Files without dates in filename/content are treated as "available for all dates"
