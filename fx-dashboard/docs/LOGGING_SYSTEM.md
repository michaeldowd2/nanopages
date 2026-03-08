# Pipeline Logging System

## Overview

Comprehensive logging infrastructure for all FX portfolio pipeline steps. Each script logs execution details (start/end times, durations, counts, errors, warnings) to structured JSON files that can be viewed in the dashboard.

## Implementation Date

2026-02-22

---

## Architecture

### Components

1. **PipelineLogger Module** (`scripts/pipeline_logger.py`)
   - Unified logging interface for all pipeline steps
   - Structured JSON output
   - Automatic timestamping and duration tracking
   - Error and warning collection

2. **Log Files** (`data/logs/YYYY-MM-DD.json`)
   - One file per day
   - Contains all step executions for that date
   - Supports multiple runs per step (overwrites previous)

3. **Export Script** (`scripts/export-logs.py`)
   - Exports logs to dashboard-friendly format
   - Creates summary of all available dates
   - Enriches data with display formatting

4. **Dashboard Tracking Tab**
   - Date selector dropdown
   - Visual step-by-step execution view
   - Displays counts, errors, warnings, and metadata

---

## PipelineLogger API

### Basic Usage

```python
from pipeline_logger import PipelineLogger

logger = PipelineLogger('step1', 'Fetch Exchange Rates')
logger.start()

try:
    # ... your code ...
    logger.add_count('pairs_fetched', 121)
    logger.add_info('data_source', 'fixer.io')
    logger.success()
except Exception as e:
    logger.error(f"Failed: {e}")
    logger.fail()
    raise
finally:
    logger.finish()
```

### Methods

#### `__init__(step_id, step_name, date_str=None)`
Initialize logger for a pipeline step.

**Parameters:**
- `step_id` (str): Step identifier (e.g., 'step1', 'step2')
- `step_name` (str): Human-readable name (e.g., 'Fetch Exchange Rates')
- `date_str` (str, optional): Date string (YYYY-MM-DD), defaults to today

#### `start()`
Mark step as started. Sets start timestamp and prints header.

#### `add_count(key, value)`
Add a count metric (e.g., signals generated, trades executed).

**Example:**
```python
logger.add_count('signals_generated', 29)
logger.add_count('trades_executed', 5)
```

#### `add_info(key, value)`
Add informational metadata (e.g., version, data source).

**Example:**
```python
logger.add_info('generator_version', '1.1.0')
logger.add_info('data_source', 'mock data')
```

#### `warning(message)`
Add a non-fatal warning.

**Example:**
```python
logger.warning('Using mock data - set API key for real rates')
```

#### `error(message)`
Add an error (may or may not be fatal).

**Example:**
```python
logger.error('Failed to fetch EUR rates')
```

#### `success()`
Mark step as successful. Called before `finish()`.

#### `fail()`
Mark step as failed. Called before `finish()`.

#### `finish()`
Complete logging and save to file. Calculates duration, auto-sets status if not set, saves JSON, prints summary.

---

## Log File Format

### Location
`/workspace/group/fx-portfolio/data/logs/YYYY-MM-DD.json`

### Structure

```json
{
  "date": "2026-02-22",
  "steps": [
    {
      "step_id": "step1",
      "step_name": "Fetch Exchange Rates (All Pairs)",
      "date": "2026-02-22",
      "start_time": "2026-02-22T20:16:09.200721",
      "end_time": "2026-02-22T20:16:09.202264",
      "duration": 0.0,
      "status": "success",
      "counts": {
        "currencies": 11,
        "total_pairs": 121,
        "eur_rates_fetched": 11,
        "pairs_calculated": 121
      },
      "errors": [],
      "warnings": [
        {
          "message": "Using mock data - set FIXER_API_KEY for real rates",
          "timestamp": "2026-02-22T20:16:09.201499"
        }
      ],
      "info": {
        "data_source": "mock data",
        "output_file": "/workspace/group/fx-portfolio/data/prices/fx-rates-2026-02-22.json"
      }
    },
    {
      "step_id": "step5",
      "step_name": "Generate Sentiment Signals",
      "date": "2026-02-22",
      "start_time": "2026-02-22T20:15:00.123456",
      "end_time": "2026-02-22T20:15:30.234567",
      "duration": 30.11,
      "status": "success",
      "counts": {
        "currencies_analyzed": 11,
        "total_signals": 29,
        "bullish_signals": 12,
        "bearish_signals": 15,
        "neutral_signals": 2
      },
      "errors": [],
      "warnings": [],
      "info": {
        "generator_name": "keyword-sentiment-v1.1",
        "generator_version": "1.1.0"
      }
    }
  ]
}
```

### Fields

**Step-level:**
- `step_id`: Step identifier (step1-step7)
- `step_name`: Human-readable step name
- `date`: Execution date (YYYY-MM-DD)
- `start_time`: ISO timestamp when step started
- `end_time`: ISO timestamp when step ended
- `duration`: Duration in seconds
- `status`: 'success' | 'failed' | 'running' | 'pending'
- `counts`: Dict of count metrics
- `errors`: Array of error objects
- `warnings`: Array of warning objects
- `info`: Dict of informational metadata

**Error/Warning object:**
```json
{
  "message": "Error description",
  "timestamp": "2026-02-22T20:16:09.201499"
}
```

---

## Scripts with Logging

### Step 1: Fetch Exchange Rates
**Script:** `scripts/fetch-exchange-rates.py`

**Counts logged:**
- `currencies`: Number of currencies (11)
- `total_pairs`: Total currency pairs (121)
- `eur_rates_fetched`: EUR rates downloaded (11)
- `pairs_calculated`: Cross-rates calculated (121)

**Info logged:**
- `data_source`: "fixer.io API" or "mock data"
- `output_file`: Path to saved exchange rates

**Warnings:**
- Using mock data when no API key

### Step 5: Generate Sentiment Signals
**Script:** `scripts/generate-sentiment-signals.py`

**Counts logged:**
- `currencies_analyzed`: Number of currencies analyzed (11)
- `total_signals`: Total signals generated
- `currencies_with_signals`: Currencies with at least 1 signal
- `bullish_signals`: Total bullish signals
- `bearish_signals`: Total bearish signals
- `neutral_signals`: Total neutral signals

**Info logged:**
- `generator_name`: Signal generator name
- `generator_version`: Generator version

### Step 7: Execute Trading Strategies
**Script:** `scripts/strategy-simple-momentum.py`

**Counts logged:**
- `strategy_combinations`: Number of strategy combos (9)
- `strategies_executed`: Strategies successfully executed
- `total_trades`: Total trades across all strategies

**Info logged:**
- `output_csv`: Path to CSV export
- `output_json`: Path to JSON export

**Warnings:**
- No data available for strategy combination

---

## Export for Dashboard

### Export Script
**Location:** `scripts/export-logs.py`

**Usage:**
```bash
python3 scripts/export-logs.py
```

**Output Files:**

1. **`data/exports/tracking_dates.json`** - Summary of all available dates
   ```json
   {
     "last_updated": "2026-02-22T20:20:00.000000",
     "total_runs": 3,
     "dates": [
       {
         "date": "2026-02-22",
         "total_steps": 4,
         "successful_steps": 4,
         "failed_steps": 0,
         "total_duration": 0.53,
         "total_errors": 0,
         "total_warnings": 1,
         "status": "success"
       }
     ]
   }
   ```

2. **`data/exports/tracking_YYYY-MM-DD.json`** - Individual day logs (enriched)
   - Same format as source logs
   - Additional display fields: `start_time_display`, `end_time_display`, `status_icon`

### Deployment to Dashboard

```bash
# Copy tracking files to dashboard
cp /workspace/group/fx-portfolio/data/exports/tracking_*.json /workspace/group/sites/fx-dashboard/data/

# Deploy to GitHub Pages
SITE_NAME="fx-dashboard"
SOURCE="/workspace/group/sites/$SITE_NAME"
DEPLOY_DIR="/tmp/nanopages-deploy"
REPO_URL=$(echo "$GITHUB_REPO" | sed "s|https://|https://x-access-token:${GITHUB_TOKEN}@|").git

rm -rf "$DEPLOY_DIR"
git clone "$REPO_URL" "$DEPLOY_DIR"
cd "$DEPLOY_DIR"
git config user.name "nano"
git config user.email "nano@nanoclaw"
rm -rf "$DEPLOY_DIR/$SITE_NAME"
mkdir -p "$DEPLOY_DIR/$SITE_NAME"
cp -r "$SOURCE/." "$DEPLOY_DIR/$SITE_NAME/"
git add -A
if git diff --cached --quiet; then
  echo "No changes"
else
  git commit -m "Update dashboard: $(date -u '+%Y-%m-%d %H:%M UTC')"
  git push origin main
fi
```

---

## Dashboard Integration

### TRACKING Tab

**Features:**
1. **Date Selector**
   - Dropdown showing all available dates
   - Format: "✓ 2026-02-22 (4/4 steps)"
   - Icon indicates success (✓) | partial (⚠️) | failed (❌)

2. **Summary Bar**
   - Shows: successful steps, failed steps, total duration, errors, warnings
   - Updates when date selected

3. **Step Cards**
   - Each step shown in expandable card
   - Color-coded border: green (success) | red (failed) | grey (pending)
   - Displays:
     - Step name and status icon
     - Duration
     - Start/end times
     - Counts (grid layout)
     - Info (monospace display)
     - Warnings (orange background)
     - Errors (red background)

### JavaScript Functions

**`loadTrackingDates()`**
- Fetches `tracking_dates.json`
- Populates date selector dropdown
- Adds change event listener

**`loadTrackingLog(date)`**
- Fetches `tracking_YYYY-MM-DD.json` for selected date
- Renders summary bar
- Renders step cards with all details

---

## Adding Logging to New Steps

To add logging to a new pipeline step:

### 1. Import PipelineLogger

```python
import sys
sys.path.append('/workspace/group/fx-portfolio/scripts')
from pipeline_logger import PipelineLogger
```

### 2. Wrap Main Execution

```python
def main():
    logger = PipelineLogger('step_id', 'Step Name')
    logger.start()

    try:
        # ... existing code ...

        # Add counts
        logger.add_count('items_processed', count)

        # Add info
        logger.add_info('version', '1.0.0')

        # Add warnings
        if warning_condition:
            logger.warning('Warning message')

        logger.success()

    except Exception as e:
        logger.error(f'Error: {e}')
        logger.fail()
        raise
    finally:
        logger.finish()
```

### 3. Best Practices

**Counts:**
- Use for quantitative metrics (signals, trades, items processed)
- Name with descriptive keys: `signals_generated`, not `count`
- Use integers or floats

**Info:**
- Use for qualitative metadata (version, source, filenames)
- Keep values short (< 100 chars)
- Use strings

**Warnings:**
- Use for non-fatal issues (missing optional data, fallbacks)
- Be specific: "Using mock data - set API_KEY" not "Warning"

**Errors:**
- Use for failures that may or may not be fatal
- Include context: "Failed to fetch EUR rates: Connection timeout"
- Can add multiple errors before failing

**Status:**
- Call `logger.success()` before `finish()` if successful
- Call `logger.fail()` before `finish()` if failed
- If neither called, auto-sets based on errors

---

## Benefits

### For Development
1. **Easy debugging** - See exactly where pipeline fails
2. **Performance tracking** - Duration of each step
3. **Data visibility** - Counts show what was processed
4. **Historical record** - Compare runs across days

### For Users
1. **Transparency** - See what the system is doing
2. **Trust** - Warnings and errors are visible
3. **Debugging** - Identify issues without code access
4. **Monitoring** - Track system health over time

---

## Future Enhancements

### Short-term
- Add logging to remaining steps (Step 2, 3, 4, 6)
- Add performance benchmarks (expected durations)
- Add alerts for critical failures

### Long-term
- Time series visualization of step durations
- Performance degradation detection
- Export logs to external monitoring (Datadog, etc.)
- Email alerts on failures
- Comparison view (today vs yesterday)

---

## Example Output

### Terminal Output
```
============================================================
Fetch Exchange Rates (All Pairs)
============================================================

Currencies: 11
Total pairs: 11 × 11 = 121

1. Fetching EUR-based rates...
ℹ️ requests module not available, using mock data
   ✓ Got rates for 11 currencies
⚠️ Warning: Using mock data - set FIXER_API_KEY for real rates

2. Calculating all currency pairs...
   ✓ Calculated 121 exchange rates

3. Saving to file...
✓ Saved exchange rates: /workspace/group/fx-portfolio/data/prices/fx-rates-2026-02-22.json

============================================================
Sample Exchange Rates (All Pairs)
============================================================
USD/JPY: 154.6102  (1 USD = 154.6102 JPY)
GBP/USD: 1.3501  (1 GBP = 1.3501 USD)
EUR/USD: 1.1800  (1 EUR = 1.1800 USD)
AUD/CAD: 0.9641  (1 AUD = 0.9641 CAD)
CHF/NOK: 12.3355  (1 CHF = 12.3355 NOK)
============================================================
📝 Log saved: /workspace/group/fx-portfolio/data/logs/2026-02-22.json

============================================================
✓ Fetch Exchange Rates (All Pairs): SUCCESS
Duration: 0.0s
  • currencies: 11
  • total_pairs: 121
  • eur_rates_fetched: 11
  • pairs_calculated: 121
============================================================
```

### Dashboard View

The TRACKING tab shows:
- **Date dropdown:** "✓ 2026-02-22 (4/4 steps)"
- **Summary:** "4 ✓ Total: 0.53s 1 warnings"
- **Step cards:** Each step with green border, duration, counts, warnings in orange boxes

---

## Testing

```bash
# Test logger directly
python3 scripts/pipeline_logger.py

# Run pipeline steps (generates logs)
python3 scripts/fetch-exchange-rates.py
python3 scripts/generate-sentiment-signals.py
python3 scripts/strategy-simple-momentum.py

# Export for dashboard
python3 scripts/export-logs.py

# Copy to dashboard
cp /workspace/group/fx-portfolio/data/exports/tracking_*.json /workspace/group/sites/fx-dashboard/data/

# Deploy to GitHub Pages
SITE_NAME="fx-dashboard"
SOURCE="/workspace/group/sites/$SITE_NAME"
DEPLOY_DIR="/tmp/nanopages-deploy"
REPO_URL=$(echo "$GITHUB_REPO" | sed "s|https://|https://x-access-token:${GITHUB_TOKEN}@|").git

rm -rf "$DEPLOY_DIR"
git clone "$REPO_URL" "$DEPLOY_DIR"
cd "$DEPLOY_DIR"
git config user.name "nano" && git config user.email "nano@nanoclaw"
rm -rf "$DEPLOY_DIR/$SITE_NAME" && mkdir -p "$DEPLOY_DIR/$SITE_NAME"
cp -r "$SOURCE/." "$DEPLOY_DIR/$SITE_NAME/"
git add -A && git commit -m "Update dashboard: $(date -u '+%Y-%m-%d %H:%M UTC')" && git push origin main
```

---

## Files Modified/Created

### Created
1. `/workspace/group/fx-portfolio/scripts/pipeline_logger.py` - Logger module
2. `/workspace/group/fx-portfolio/scripts/export-logs.py` - Export script
3. `/workspace/group/fx-portfolio/data/logs/` - Log directory (auto-created)
4. `/workspace/group/fx-portfolio/docs/LOGGING_SYSTEM.md` - This file

### Modified
1. `/workspace/group/fx-portfolio/scripts/fetch-exchange-rates.py` - Added logging
2. `/workspace/group/fx-portfolio/scripts/generate-sentiment-signals.py` - Added logging
3. `/workspace/group/fx-portfolio/scripts/strategy-simple-momentum.py` - Added logging
4. `/workspace/group/sites/fx-dashboard/index.html` - Added TRACKING tab with log viewer

---

## Summary

The logging system provides complete visibility into pipeline execution:
- **Structured JSON logs** with start/end times, durations, counts, errors
- **Dashboard integration** with date selector and visual step cards
- **Easy to extend** - just wrap code in try/finally with PipelineLogger
- **Automatic exports** - run export-logs.py to prepare for dashboard

This makes debugging, monitoring, and improving the FX portfolio system much easier.
