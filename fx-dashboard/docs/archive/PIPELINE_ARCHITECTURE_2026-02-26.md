# Pipeline Architecture & Orchestration

**Date**: 2026-02-26
**Author**: nano (Claude Code)

## Overview

The FX Portfolio Trading Pipeline is a config-driven, dependency-aware orchestration system with visual monitoring.

## Architecture Principles

### 1. **Single Source of Truth**
- All step definitions live in `config/pipeline_steps.json`
- Scripts read from this config (no hardcoded dependencies)
- Easy to add new steps without modifying orchestration logic

### 2. **Dependency-Driven Execution**
- Steps declare their direct dependencies via `depends_on` array
- Orchestrator automatically resolves transitive dependencies
- Topological sorting ensures correct execution order

### 3. **Visual Observability**
- Interactive SVG dependency graph on dashboard
- Color-coded nodes (safe/unsafe/LLM-cost)
- Real-time step status tracking

## Core Components

### Configuration (`config/pipeline_steps.json`)

Defines all pipeline steps with:
- `id`: Step identifier (1, 2, 3, 4, 5, 6, 7, 8, 9)
- `name`: Human-readable name
- `script`: Path to executable script
- `description`: What the step does
- `depends_on`: Array of step IDs this step needs
- `outputs.source`: Files created in workspace
- `outputs.exports`: Files exported to dashboard
- `supports_date_filter`: Whether step can run for specific dates
- `is_safe_to_clear`: Whether safe to delete and regenerate
- `warning`: Optional safety/cost warning
- `note`: Optional additional information

### Dependency Resolver (`scripts/resolve-dependencies.py`)

Python utility that:
- Reads `config/pipeline_steps.json`
- Performs topological sort for execution order
- Finds all upstream dependencies (what a step needs)
- Finds all downstream dependents (what depends on a step)
- Validates graph for cycles
- Exports to bash arrays for scripting

**Usage:**
```bash
# See what depends on step 3
./scripts/resolve-dependencies.py --downstream 3

# See what step 6 needs to run
./scripts/resolve-dependencies.py --upstream 6

# Get execution order for multiple steps
./scripts/resolve-dependencies.py --order 3 5 7 8

# Validate no cycles exist
./scripts/resolve-dependencies.py --validate

# Export as bash array for scripting
./scripts/resolve-dependencies.py --downstream 3 --bash
```

### Orchestrator Scripts

#### `scripts/rerun-steps-v2.sh`
Config-driven step executor with date validation:
- Reads step info from `pipeline_steps.json`
- Uses `resolve-dependencies.py` for dependency resolution
- Uses `validate-step-dates.py` for date dependency checking
- Supports:
  - `--downstream`: Run step + all dependents
  - `--date YYYY-MM-DD`: Run for specific date (validates dependencies first)
  - `--latest`: Auto-detect latest date with all dependencies available
  - `--dry-run`: Preview execution plan
  - `--skip-deploy`: Skip Step 9

**Examples:**
```bash
# Rerun step 3 and everything that depends on it
./scripts/rerun-steps-v2.sh 3 --downstream

# Preview what would run
./scripts/rerun-steps-v2.sh 3 --downstream --dry-run

# Run for specific date (validates all dependencies exist)
./scripts/rerun-steps-v2.sh 5 --date 2026-02-25

# Run with auto-detected latest date
./scripts/rerun-steps-v2.sh 7 --latest

# Run downstream with latest dates
./scripts/rerun-steps-v2.sh 5 --downstream --latest

# Run entire pipeline
./scripts/rerun-steps-v2.sh all
```

#### `scripts/validate-step-dates.py`
Date dependency validation utility:
- Scans export files to find available dates
- Validates that all upstream dependencies have data for target date
- Finds latest common date across all dependencies
- Used by orchestrator for date checking

**Examples:**
```bash
# Show dependency status
./scripts/validate-step-dates.py 7

# Find latest available date
./scripts/validate-step-dates.py 7 --find-latest

# Check if specific date is valid
./scripts/validate-step-dates.py 7 --date 2026-02-25
```

#### `scripts/clear-data-v2.sh`
Config-driven data clearer:
- Reads output patterns from `pipeline_steps.json`
- Uses `resolve-dependencies.py` for dependency resolution
- Supports:
  - `--downstream`: Clear step + all dependents
  - `--date YYYY-MM-DD`: Clear only specific date
  - `--dry-run`: Preview what would be deleted

**Examples:**
```bash
# Clear step 3 and all downstream data
./scripts/clear-data-v2.sh 3 --downstream

# Preview what would be cleared
./scripts/clear-data-v2.sh 3 --downstream --dry-run

# Clear specific date only
./scripts/clear-data-v2.sh 5 --date 2026-02-25
```

### Dashboard Visualization

#### Visual Dependency Graph
- Interactive SVG rendered on Architecture page
- Nodes positioned in layers by dependency depth
- Color-coded by safety:
  - 🟢 Green: Safe to clear (regenerable)
  - 💰 Yellow: LLM costs when regenerated
  - 🔴 Red: Unsafe (cumulative state)
- Arrows show dependency flow
- Hover effects for interactivity

#### Detailed Step Info
- Lists all steps with dependencies
- Shows warnings and notes
- Displays output file patterns
- Includes orchestration command examples

## Current Pipeline Graph

```
Step 1: Exchange Rates (root)
  ↓
Step 2: Currency Indices
  ↓
Step 3: News Aggregation (root)
  ↓
  ├─→ Step 4: Time Horizon Analysis
  └─→ Step 5: Sentiment Signals
      ↓
Step 6: Signal Realization ← (also depends on Steps 2, 4)
  ↓
Step 7: Trade Calculation
  ↓
Step 8: Portfolio Execution
  ↓
Step 9: Dashboard Deployment ← (depends on ALL steps 1-8)
```

### Parallel Roots
Steps 1 and 3 can run in parallel (no dependencies on each other):
- Step 1: Exchange Rates → needed for indices
- Step 3: News → needed for horizons and sentiment

### Convergence Point
Step 6 (Signal Realization) converges:
- Needs Step 5 (sentiment signals)
- Needs Step 4 (time horizons)
- Needs Step 2 (currency indices for realization checking)

### Critical Node
Step 8 (Portfolio Execution):
- Has cumulative state (not safe to clear)
- Only depends on Step 7 (trades)
- All signal info already embedded in trades

## Adding a New Step

### 1. Define the Step in Config

Edit `config/pipeline_steps.json` and add your step:

```json
{
  "9": {
    "id": "9",
    "name": "Risk Analysis",
    "script": "scripts/analyze-risk.py",
    "description": "Calculate VaR and risk metrics for portfolios",
    "depends_on": ["8"],
    "outputs": {
      "source": ["data/risk/*.json"],
      "exports": ["data/exports/step9_risk.csv"]
    },
    "supports_date_filter": true,
    "is_safe_to_clear": true,
    "note": "Uses historical portfolio values from Step 8"
  }
}
```

### 2. Create the Script

Create `scripts/analyze-risk.py`:
- Must read from dependencies' output files
- Must write to configured output paths
- Should support `--date` flag if `supports_date_filter: true`

### 3. Update Dashboard Deployment (if needed)

If Step 8 should export your new step's data:
- Update `scripts/export-pipeline-data.py` to export your data
- Dashboard will automatically show new step in graph

### 4. Test

```bash
# Validate dependency graph
./scripts/resolve-dependencies.py --validate

# Test with dry-run
./scripts/rerun-steps-v2.sh 9 --dry-run

# Run the step
./scripts/rerun-steps-v2.sh 9
```

### 5. Deploy

```bash
./scripts/deploy-dashboard.sh
```

The visual graph will automatically update with your new step!

## Best Practices

### Dependency Design
1. **Declare minimum dependencies**: Only list direct dependencies, not transitive
2. **Avoid cycles**: Steps cannot depend on each other (validator will catch this)
3. **Separate concerns**: Each step should do one thing well
4. **Consider parallelization**: Steps with no shared dependencies can run in parallel

### Step Implementation
1. **Idempotent**: Running twice should produce same result
2. **Date-aware**: Support `--date` flag for selective processing
3. **Fail fast**: Exit with non-zero code on errors
4. **Log clearly**: Output should be human-readable for debugging

### Safety
1. **Mark cumulative steps unsafe**: Set `is_safe_to_clear: false` for state that can't be regenerated
2. **Warn about costs**: Add warnings for LLM or API costs
3. **Always dry-run first**: Use `--dry-run` to preview before executing
4. **Back up critical data**: Before clearing Step 8 (portfolio state)

## Migration from Old Scripts

Old scripts (`clear-data.sh`, `rerun-steps.sh`) still work but are deprecated.

Migrate to v2 scripts for:
- Automatic dependency resolution from config
- No hardcoded dependency arrays to maintain
- Easier to add new steps
- Better error messages
- More consistent behavior

## Troubleshooting

### "Cycle detected in dependency graph!"
- You've created a circular dependency
- Run `./scripts/resolve-dependencies.py --validate` to check
- Review `depends_on` arrays in config

### Step runs in wrong order
- Check `depends_on` array includes all direct dependencies
- Run `./scripts/resolve-dependencies.py --upstream <step>` to see full tree

### New step not showing in dashboard
- Ensure step exported to `data/exports/`
- Check export script includes your step
- Verify `outputs.exports` in config is correct
- Redeploy dashboard with `./scripts/deploy-dashboard.sh`

## Performance

### Parallel Execution (Future Enhancement)
Current scripts run sequentially. Could be optimized to:
- Run independent steps in parallel (Steps 1 & 3)
- Run dependent steps only after prerequisites complete
- Use process pools for parallel execution

### Incremental Processing
Many steps support `--date` for incremental updates:
```bash
# Only process today's data
./scripts/rerun-steps-v2.sh 5 --downstream --date $(date +%Y-%m-%d)
```

## References

- Configuration: `config/pipeline_steps.json`
- Resolver: `scripts/resolve-dependencies.py`
- Orchestrator: `scripts/rerun-steps-v2.sh`
- Clearer: `scripts/clear-data-v2.sh`
- Dashboard: https://michaeldowd2.github.io/nanopages/fx-dashboard/
