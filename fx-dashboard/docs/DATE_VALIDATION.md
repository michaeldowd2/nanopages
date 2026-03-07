# Pipeline Date Validation & Dependency Checking

**Date**: 2026-02-26
**Status**: ✅ Fully Implemented

## Overview

The pipeline now validates that all upstream dependencies have data for a specific date before executing any step. This prevents inconsistent results from running steps with incomplete or missing dependency data.

## Key Features

### 1. **Automatic Latest Date Detection**

When running steps without specifying a date, the orchestrator automatically finds the latest date where ALL upstream dependencies have data:

```bash
# Auto-detect latest available date for Step 7
./scripts/rerun-steps-v2.sh 7 --latest

# Auto-detect for multiple steps
./scripts/rerun-steps-v2.sh 5 --downstream --latest
```

**How it works:**
- Scans export files for each dependency
- Finds dates available in each dependency's output
- Returns the latest date present in ALL dependencies
- Each step runs for its own optimal latest date

### 2. **Explicit Date Validation**

When specifying a date explicitly, the orchestrator validates that all dependencies exist for that date:

```bash
# Run Step 7 for specific date (validates dependencies first)
./scripts/rerun-steps-v2.sh 7 --date 2026-02-25

# If validation fails, shows which dependencies are missing
./scripts/rerun-steps-v2.sh 7 --date 2026-02-26
```

**Validation output example:**
```
✗ Step 7 (Trade Calculation): Missing dependencies for 2026-02-26
  • Step 1 (Exchange Rates) missing data for 2026-02-26
    Available dates: 2026-02-25, 2026-02-24
  • Step 4 (Time Horizon Analysis) missing data for 2026-02-26
    Available dates: 2026-02-25
```

### 3. **Standalone Validation Tool**

Query date availability directly without running steps:

```bash
# Show dependency status for a step
./scripts/validate-step-dates.py 7

# Find latest available date
./scripts/validate-step-dates.py 7 --find-latest

# Check if specific date is valid
./scripts/validate-step-dates.py 7 --date 2026-02-25
```

## How It Works

### Date Detection Algorithm

The validation system:

1. **Reads pipeline config** to get step dependencies
2. **Scans export files** in `data/exports/` for date patterns
3. **Extracts dates** from:
   - Filenames with YYYY-MM-DD patterns
   - CSV files with `date` column (reads all rows)
   - JSON files with date keys
4. **Computes intersection** of available dates across all dependencies
5. **Returns latest common date** or validates specific date

### File Pattern Matching

The system recognizes dates in export files:

```
✓ step2_indices.csv with date column
✓ step3_news.csv with date column
✓ fx-rates-2026-02-26.json (date in filename)
✓ step1_exchange_rates_matrix_2026-02-25.json (date in filename)
```

### Dependency Resolution

Uses transitive dependency resolution:

```
Step 7 depends on Step 6
Step 6 depends on Steps 2, 4, 5
Step 5 depends on Step 3
Step 4 depends on Step 3
Step 2 depends on Step 1

Therefore Step 7's full dependencies: [1, 2, 3, 4, 5, 6]
```

All upstream dependencies must have data for the target date.

## Usage Examples

### Running with Latest Date

**Scenario:** Run Step 7 with the most recent data available

```bash
./scripts/rerun-steps-v2.sh 7 --latest
```

**Output:**
```
============================================================
Detecting Latest Available Dates
============================================================

  Step 7 (Trade Calculation): 2026-02-25

============================================================
Pipeline Execution Plan
============================================================

Steps to execute (in order):

[7] Trade Calculation
  Script: scripts/calculate-trades.py
  ✓ Will run for date: 2026-02-25
```

### Running Multiple Steps with Latest Dates

**Scenario:** Rerun Step 5 and all downstream with latest data

```bash
./scripts/rerun-steps-v2.sh 5 --downstream --latest
```

Each step runs for its own latest available date:
- Step 5: 2026-02-25 (latest where Steps 1,3 exist)
- Step 6: 2026-02-25 (latest where Steps 1,2,3,4,5 exist)
- Step 7: 2026-02-25 (latest where Steps 1,2,3,4,5,6 exist)
- Step 8: 2026-02-25 (latest where Step 7 exists)

### Validating Specific Date

**Scenario:** Run Step 7 for yesterday's data

```bash
./scripts/rerun-steps-v2.sh 7 --date 2026-02-25
```

**If valid:**
```
Validating Date Dependencies for 2026-02-25
  ✓ Step 7 (Trade Calculation): Dependencies satisfied for 2026-02-25
```

**If invalid:**
```
Validating Date Dependencies for 2026-02-27
  ✗ Step 7 (Trade Calculation): Missing dependencies for 2026-02-27

Cannot run Step 7 (Trade Calculation) for 2026-02-27:
  • Step 1 (Exchange Rates) missing data for 2026-02-27
    Available dates: 2026-02-25, 2026-02-24
  ...

✗ Validation failed - cannot proceed

Suggestions:
  • Run missing dependency steps first
  • Use --latest to auto-detect available dates
  • Check available dates with: ./scripts/validate-step-dates.py 7
```

### Checking Date Availability

**Scenario:** Check which dates are available for Step 7

```bash
./scripts/validate-step-dates.py 7
```

**Output:**
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

### Finding Latest Date Programmatically

**Scenario:** Get latest date as JSON for scripting

```bash
./scripts/validate-step-dates.py 7 --find-latest --json
```

**Output:**
```json
{"latest_date": "2026-02-25"}
```

## Command Reference

### Orchestrator (`rerun-steps-v2.sh`)

```bash
./scripts/rerun-steps-v2.sh <step> [options]
```

**New options:**
- `--latest` - Auto-detect latest date with all dependencies available
- `--date YYYY-MM-DD` - Run for specific date (validates dependencies exist)

**Behavior:**
- **No date flags**: Runs for all available dates (old behavior)
- **--latest**: Each step runs for its own latest available date
- **--date YYYY-MM-DD**: All steps run for specified date (validates first)

### Validation Tool (`validate-step-dates.py`)

```bash
./scripts/validate-step-dates.py <step_id> [options]
```

**Options:**
- `--find-latest` - Find latest date available for all dependencies
- `--date YYYY-MM-DD` - Validate specific date is available
- `--json` - Output result as JSON

**Examples:**
```bash
# Show dependency info
./scripts/validate-step-dates.py 7

# Find latest date
./scripts/validate-step-dates.py 7 --find-latest

# Validate specific date
./scripts/validate-step-dates.py 7 --date 2026-02-25

# Get latest date as JSON
./scripts/validate-step-dates.py 7 --find-latest --json
```

## Integration with Workflow

### Daily Pipeline Run

```bash
# Run entire pipeline for today
./run-pipeline.sh

# Then rerun specific steps with latest data
./scripts/rerun-steps-v2.sh 5 --downstream --latest
```

### Backfilling Data

```bash
# Check available dates
./scripts/validate-step-dates.py 7

# Backfill specific date
./scripts/rerun-steps-v2.sh 7 --date 2026-02-20

# Backfill will fail if dependencies missing
```

### Debugging Missing Data

```bash
# Step 7 failing? Check dependencies
./scripts/validate-step-dates.py 7 --date 2026-02-25

# See which dependency is missing
# Run that dependency first
./scripts/rerun-steps-v2.sh 4 --date 2026-02-25
```

## Special Cases

### Steps Without Date Filtering

Some steps don't support date filtering:
- **Step 9 (Dashboard Deployment)**: Always deploys all available data

These steps:
- Show "Date filtering not supported" in validation
- Always run regardless of `--date` or `--latest` flags
- Don't block execution if other steps have dates

### Steps Without Dated Exports

Some steps export files without dates:
- Treated as "available for all dates"
- Don't constrain the latest date calculation
- Example: System config files, pipeline metadata

### Root Steps (No Dependencies)

Steps with no dependencies (Steps 1, 3):
- `--latest` uses their own latest export date
- No validation needed (no dependencies to check)
- Can run for any date

## Error Handling

### Missing Dependency Data

```bash
$ ./scripts/rerun-steps-v2.sh 7 --date 2026-02-27

✗ Step 7 (Trade Calculation): Missing dependencies for 2026-02-27
  • Step 1 (Exchange Rates) missing data for 2026-02-27
    Available dates: 2026-02-25, 2026-02-24

✗ Validation failed - cannot proceed

Suggestions:
  • Run missing dependency steps first
  • Use --latest to auto-detect available dates
```

**Resolution:**
1. Run missing dependency: `./scripts/rerun-steps-v2.sh 1 --date 2026-02-27`
2. Then retry: `./scripts/rerun-steps-v2.sh 7 --date 2026-02-27`

Or use `--latest` to avoid the issue entirely.

### No Common Date Available

```bash
$ ./scripts/validate-step-dates.py 7 --find-latest

No common date found for Step 7 (Trade Calculation) dependencies

Dependency status:
  Step 1 (Exchange Rates): 2 dates, latest = 2026-02-25
  Step 4 (Time Horizon Analysis): 0 dates (missing data!)
```

**Resolution:**
Run the missing dependency to generate data.

## Implementation Details

### Files

- **`scripts/validate-step-dates.py`** - Core validation logic
  - Date extraction from files
  - Dependency resolution
  - Latest date calculation
  - Validation reporting

- **`scripts/rerun-steps-v2.sh`** - Enhanced orchestrator
  - Calls validation script before execution
  - Auto-detects dates with `--latest`
  - Validates dates with `--date`
  - Per-step date tracking

### Key Functions

#### `get_available_dates_for_step(step_id)`
Scans export files and returns set of available dates

#### `find_latest_common_date(step_id)`
Returns latest date present in ALL dependencies

#### `validate_date_for_step(step_id, date)`
Returns validation result with missing dependencies

### Date Extraction Logic

```python
# 1. Check filename for YYYY-MM-DD pattern
dates = re.findall(r'\d{4}-\d{2}-\d{2}', filename)

# 2. If CSV, read date column
if file.endswith('.csv'):
    # Parse CSV, find 'date' column, extract all dates

# 3. If no dates found, treat as "all dates available"
```

## Benefits

### ✅ Data Consistency
Never run steps with incomplete dependencies

### ✅ Clear Error Messages
Know exactly which dependency is missing

### ✅ Automatic Date Detection
No need to manually track available dates

### ✅ Flexible Execution
Choose between latest or specific date

### ✅ Safe Backfilling
Validate before running expensive operations

## Future Enhancements

### Parallel Execution
Could run independent steps in parallel once dates validated

### Date Range Processing
Support `--date-range 2026-02-20:2026-02-25` to backfill multiple days

### Incremental Updates
Auto-detect missing dates and offer to fill gaps

### Dependency Graph Visualization
Show which dates are available across entire pipeline

## Testing

```bash
# Test latest date detection
./scripts/validate-step-dates.py 7 --find-latest

# Test specific date validation (should pass)
./scripts/validate-step-dates.py 7 --date 2026-02-25

# Test specific date validation (should fail)
./scripts/validate-step-dates.py 7 --date 2099-12-31

# Test orchestrator dry-run with latest
./scripts/rerun-steps-v2.sh 7 --latest --dry-run

# Test orchestrator dry-run with invalid date
./scripts/rerun-steps-v2.sh 7 --date 2099-12-31 --dry-run

# Test downstream with latest
./scripts/rerun-steps-v2.sh 5 --downstream --latest --dry-run
```

## Summary

The date validation system ensures data consistency by:
1. **Validating** all dependencies exist before execution
2. **Auto-detecting** latest available dates
3. **Preventing** incomplete pipeline runs
4. **Providing** clear error messages with suggestions

This makes the pipeline more robust and easier to operate, especially when backfilling data or debugging issues.
