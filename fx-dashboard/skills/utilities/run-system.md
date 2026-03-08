# run-system

**Procedural pipeline execution script that runs processes in dependency order based on configuration.**

## Purpose

The `run-system` script provides a config-driven way to execute the FX Portfolio Pipeline. Instead of manually running each process script, this utility:

- Reads process definitions from `config/pipeline_steps.json`
- Resolves dependencies automatically
- Executes processes in correct order
- Supports selective reruns by date and/or process IDs
- Handles errors and provides clear logging

**Key benefit**: Make reruns procedural and eliminate manual script execution.

---

## Quick Start

```bash
# Run all processes for today
python3 scripts/utilities/run-system.py

# Run all processes for specific date
python3 scripts/utilities/run-system.py --date 2024-01-15

# Run specific processes for today
python3 scripts/utilities/run-system.py --process-ids 1 2 3

# Run specific processes for specific date
python3 scripts/utilities/run-system.py --date 2024-01-15 --process-ids 5 6 7

# Include deployment step
python3 scripts/utilities/run-system.py --include-deployment

# Preview execution plan without running
python3 scripts/utilities/run-system.py --dry-run
```

---

## Parameters

### `--date` (optional)
- **Format**: YYYY-MM-DD
- **Default**: Today's date
- **Purpose**: Specify which date to process
- **Example**: `--date 2024-01-15`

### `--process-ids` (optional)
- **Format**: Space-separated list of process IDs
- **Default**: All processes (1-9, excluding deployment)
- **Purpose**: Run only specific processes
- **Example**: `--process-ids 1 2 3` or `--process-ids 5 6 7 8`

### `--include-deployment` (optional)
- **Type**: Flag
- **Default**: False
- **Purpose**: Include deployment step (process 10) in execution
- **Example**: `--include-deployment`

### `--dry-run` (optional)
- **Type**: Flag
- **Default**: False
- **Purpose**: Show execution plan without actually running processes
- **Example**: `--dry-run`

---

## How It Works

### 1. Configuration-Driven

The script reads `config/pipeline_steps.json` which defines:
- All pipeline processes (IDs, names, scripts)
- Dependencies between processes
- Which processes support date filtering
- Execution metadata

### 2. Dependency Resolution

When you specify process IDs to run, the script:
- Includes the requested processes
- Automatically includes all **downstream** processes that depend on them
- Orders execution to satisfy dependencies
- Excludes deployment (process 10) unless explicitly requested

**Important**: This runs processes **downstream** (not upstream) to avoid unnecessary reruns of expensive processes like LLM-based analysis.

**Example**:
- Request: `--process-ids 7` (aggregate-signals)
- Resolves to: Processes 7, 8, 9
- Reason: Process 8 depends on 7, and process 9 depends on 8
- **Does NOT include**: Processes 1-6 (upstream dependencies that already have data)

### 3. Execution

Processes are executed sequentially in dependency order:
- Date parameter passed to processes that support it
- Stdout/stderr captured and logged
- Execution stops on first failure
- Clear success/failure reporting

---

## Process IDs

| ID | Process Name | Supports Date Filter | Dependencies |
|----|--------------|----------------------|--------------|
| 1 | Exchange Rates | ✓ | None |
| 2 | Currency Indices | ✓ | 1 |
| 3 | News Aggregation | ✓ | None |
| 4 | Time Horizon Analysis | ✓ | 3 |
| 5 | Sentiment Signals | ✓ | 3 |
| 6 | Signal Realization | ✓ | 2, 4, 5 |
| 7 | Signal Aggregation | ✓ | 6 |
| 8 | Trade Calculation | ✓ | 7 |
| 9 | Portfolio Execution | ✓ | 1, 8 |
| 10 | Dashboard Deployment | ✗ | 1-9 |

---

## Common Use Cases

### Full Pipeline Run

Run the entire pipeline for today:
```bash
python3 scripts/utilities/run-system.py
```

Run the entire pipeline for specific date:
```bash
python3 scripts/utilities/run-system.py --date 2024-01-15
```

### Backfill Historical Date

Process a historical date (e.g., missed day):
```bash
python3 scripts/utilities/run-system.py --date 2024-01-10
```

### Regenerate Signals

Reprocess signal generation and downstream steps:
```bash
# Regenerate signals for today (runs 5→6→7→8→9)
python3 scripts/utilities/run-system.py --process-ids 5

# Regenerate signals for specific date
python3 scripts/utilities/run-system.py --date 2024-01-12 --process-ids 5
```

Note: Specifying process 5 automatically includes downstream processes 6, 7, 8, 9.

### Recalculate Trades Only

Recalculate trades and portfolio execution (runs 8→9):
```bash
python3 scripts/utilities/run-system.py --process-ids 8
```

### Preview Execution Plan

See what would run without executing:
```bash
python3 scripts/utilities/run-system.py --process-ids 5 6 7 --dry-run
```

### Full Pipeline + Deployment

Run everything including deployment:
```bash
python3 scripts/utilities/run-system.py --include-deployment
```

---

## Expected Output

### Execution Plan

```
============================================================
EXECUTION PLAN
============================================================
Date: 2024-01-15
Processes to execute: 7

  1. Process 1: Exchange Rates [date filter: ✓]
  2. Process 2: Currency Indices [date filter: ✓]
     Dependencies: 1
  3. Process 3: News Aggregation [date filter: ✓]
  4. Process 5: Sentiment Signals [date filter: ✓]
     Dependencies: 3
  5. Process 6: Signal Realization [date filter: ✓]
     Dependencies: 5, 4, 2
  6. Process 7: Signal Aggregation [date filter: ✓]
     Dependencies: 6
  7. Process 8: Trade Calculation [date filter: ✓]
     Dependencies: 7
============================================================
```

### Execution Progress

```
Starting execution...

Executing: Process 1 - Exchange Rates for date 2024-01-15
Command: python3 /workspace/group/fx-portfolio/scripts/pipeline/fetch-exchange-rates.py --date 2024-01-15
✓ Process 1 (Exchange Rates) completed successfully

Executing: Process 2 - Currency Indices for date 2024-01-15
Command: python3 /workspace/group/fx-portfolio/scripts/pipeline/calculate-currency-indices.py --date 2024-01-15
✓ Process 2 (Currency Indices) completed successfully

...
```

### Execution Summary

```
============================================================
EXECUTION SUMMARY
============================================================
Successful: 7
Failed: 0
Total: 7
✓ All processes completed successfully
```

---

## Error Handling

### Process Failure

If a process fails:
- Execution stops immediately
- Error details logged
- Non-zero exit code returned
- Failed process identified in summary

**Example**:
```
✗ Process 5 (Sentiment Signals) failed with code 1
Error: Missing API key: ANTHROPIC_API_KEY

Process 5 failed - stopping execution

============================================================
EXECUTION SUMMARY
============================================================
Successful: 4
Failed: 1
Total: 5
✗ Pipeline execution failed
```

### Invalid Process IDs

If you specify an invalid process ID:
```
ERROR: Invalid process ID: 99
```

### Missing Script

If a process script is missing:
```
ERROR: Script not found: /workspace/group/fx-portfolio/scripts/pipeline/missing.py
✗ Process 5 (Sentiment Signals) failed with exception
```

---

## Logging

All execution logged to:
- **Console**: Real-time progress
- **Log file**: `data/logs/pipeline-YYYYMMDD-HHMMSS.log`

Log levels:
- **INFO**: Normal execution progress
- **WARNING**: Non-critical issues
- **ERROR**: Process failures
- **DEBUG**: Detailed output (first 500 chars of stdout)

---

## Integration with Scheduled Tasks

Use `run-system.py` in scheduled tasks for consistent execution:

```bash
# Daily full pipeline run
python3 scripts/utilities/run-system.py

# Daily pipeline + deployment
python3 scripts/utilities/run-system.py --include-deployment
```

Benefits:
- Single command to run entire pipeline
- Automatic dependency resolution
- Clear logging for debugging
- Easy to modify what runs (just change --process-ids)

---

## Notes

- **Default behavior**: Runs all processes (1-9) except deployment
- **Deployment not included**: Use `--include-deployment` flag to deploy
- **Date propagation**: Date parameter automatically passed to processes that support it
- **Process 4.1**: Currency Events step has no script (reference data only) - automatically skipped
- **Sequential execution**: Processes run one at a time in order
- **Fail-fast**: Execution stops on first error to prevent cascading issues
- **Legacy path handling**: Script automatically updates old paths in config to new folder structure

---

## Troubleshooting

### "Configuration file not found"
- Check that `config/pipeline_steps.json` exists
- Verify you're running from correct directory

### "Process X has no script"
- Normal for Process 4.1 (Currency Events) - it's reference data
- For other processes, check config has correct script path

### "Script not found"
- Verify script exists at path specified in config
- Check folder structure matches: `scripts/pipeline/`, `scripts/utilities/`

### Date filter not working
- Check process supports date filtering in config
- Verify date format is YYYY-MM-DD
- Some processes ignore date parameter by design (e.g., deployment)

---

## Related

- **Configuration**: See `config/pipeline_steps.json` for process definitions
- **Architecture**: See `docs/ARCHITECTURE.md` for system overview
- **Logging**: See `docs/LOGGING_SYSTEM.md` for log details
- **Individual Skills**: See `skills/pipeline/*.md` for process-specific documentation
