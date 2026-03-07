# Legacy Files and Code Cleanup Report

Date: 2026-03-01

## Summary

This document identifies legacy files and outdated code references that can be cleaned up following the Step 6 refactor.

---

## Current Data Flow (Correct)

```
Step 5: Sentiment Signals
  → Output: data/signals/{CURRENCY}/{DATE}.json
  → Export: data/exports/step5_signals.csv

Step 6: Signal Realization
  → Input: data/signals/{CURRENCY}/{DATE}.json (from Step 5)
  → Input: data/article-analysis/{DATE}.json (from Step 4)
  → Input: data/indices/{CURRENCY}_index.json (from Step 2)
  → Output: data/signal-realization/{DATE}.json (NEW LOCATION)
  → Export: data/exports/step6_realization.csv

Step 7: Signal Aggregation
  → Input: data/signal-realization/{DATE}.json (from Step 6)
  → Export: data/exports/step7_aggregated_signals.csv
```

---

## ✅ Files Updated (Correct)

### Scripts
- ✅ `scripts/check-signal-realization.py` - Outputs to signal-realization directory
- ✅ `scripts/aggregate-signals.py` - Reads from signal-realization directory
- ✅ `scripts/export-pipeline-data.py` - Exports step6 from signal-realization
- ✅ `config/pipeline_steps.json` - Updated Step 6 output paths

### Documentation
- ✅ `scripts/aggregate-signals.py` - Updated docstring to reference signal-realization

---

## 🗑️ Legacy Directories to Remove

### 1. `/workspace/group/fx-portfolio/data/portfolio/`
- **Status**: Empty directory
- **Replaced by**: `data/portfolios/` (with 's')
- **Safe to delete**: YES
- **Command**: `rmdir data/portfolio`

### 2. `/workspace/group/fx-portfolio/data/trades/`
- **Status**: Empty directory
- **Usage**: Unknown - appears to be unused
- **Safe to delete**: YES (verify no scripts reference it first)
- **Command**: `rmdir data/trades`

---

## ✓ Data Files (Correct - DO NOT REMOVE)

### `data/signals/{CURRENCY}/{DATE}.json`
- **Status**: ACTIVE - Step 5 output
- **Used by**: Step 6 as input
- **Keep**: YES - This is the correct location for Step 5 outputs

### `data/signal-realization/{DATE}.json`
- **Status**: ACTIVE - Step 6 output (new location)
- **Used by**: Step 7 as input
- **Keep**: YES - This is the new consolidated format

---

## Scripts Review - No Issues Found

All scripts have been verified to use the correct data paths:

| Script | Step | Input | Output | Status |
|--------|------|-------|--------|--------|
| `generate-sentiment-signals-v2.py` | 5 | news articles | `data/signals/{CURRENCY}/{DATE}.json` | ✅ Correct |
| `check-signal-realization.py` | 6 | signals + horizons + indices | `data/signal-realization/{DATE}.json` | ✅ Correct |
| `aggregate-signals.py` | 7 | signal-realization | CSV export | ✅ Correct |
| `calculate-trades-step8.py` | 8 | aggregated signals | CSV export | ✅ Correct |
| `execute-strategies-step9.py` | 9 | trades + rates | `data/portfolios/*.json` | ✅ Correct |
| `export-pipeline-data.py` | - | all steps | CSV exports | ✅ Correct |

---

## Recommended Cleanup Actions

### 1. Remove Empty Directories
```bash
cd /workspace/group/fx-portfolio

# Remove legacy portfolio directory
rmdir data/portfolio

# Remove legacy trades directory (verify first)
rmdir data/trades
```

### 2. Update .gitignore (if exists)
Ensure the new `data/signal-realization/` directory is properly tracked:
```
# Keep signal realization outputs
data/signal-realization/*.json
```

---

## Notes

### Why data/signals/ is NOT legacy
The `data/signals/{CURRENCY}/{DATE}.json` files are **still actively used**:
- They are the output of Step 5 (Sentiment Signal Generation)
- Step 6 reads from these files to create the consolidated realization output
- They contain the raw per-currency signal data before realization checking

### Migration Complete
The Step 6 refactor successfully moved from:
- **Old**: Modifying signal files in-place with `realized: true/false` flags
- **New**: Creating consolidated realization output in `data/signal-realization/`

This change provides:
1. **Temporal validity windows** - Articles tracked across multiple days if still valid
2. **Accumulating signals** - Shows growing list of active predictions
3. **Clean separation** - Step 5 outputs remain unchanged, Step 6 creates new data
4. **Better data model** - All realization data in one place with full context

---

## Validation Commands

### Check for orphaned references
```bash
# Search for old realization patterns
grep -r "\.get('realized')" scripts/ --include="*.py"

# Should only find:
# - aggregate-signals.py (correctly reading from signal-realization)
# - check-signal-realization.py (correctly setting realized flag)
```

### Verify data flow
```bash
# Step 5 output exists
ls data/signals/EUR/2026-*.json

# Step 6 output exists
ls data/signal-realization/2026-*.json

# No orphaned files
find data/ -type f -name "*.json" -mtime +30
```

---

## Conclusion

✅ **All scripts updated correctly**
✅ **Data flow is clean and consistent**
🗑️ **Two empty legacy directories identified for removal**
📝 **Documentation updated**

The pipeline is now using the correct data paths with the refactored Step 6 architecture.
