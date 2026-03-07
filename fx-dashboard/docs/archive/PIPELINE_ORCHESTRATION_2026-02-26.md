# Pipeline Orchestration & Data Management - 2026-02-26

## Summary

Created comprehensive pipeline orchestration system with:
- **Step dependency graph** (pipeline_steps.json)
- **Smart clear-data script** with dependency awareness
- **Smart rerun script** with dependency awareness
- **Safety features** and confirmation prompts
- **Date filtering** support

---

## Files Created

### 1. `config/pipeline_steps.json`
**Purpose:** Single source of truth for pipeline structure

**Contents:**
- Step definitions (ID, name, script, description)
- Dependency relationships
- Output file patterns
- Safety warnings
- Date filtering support flags

**Usage:**
- Read by orchestration scripts
- Exported to dashboard for visualization
- Used for dependency resolution

### 2. `scripts/clear-data.sh`
**Purpose:** Safely clear pipeline data with dependency awareness

**Features:**
- Clear specific step or step + downstream
- Date filtering support
- Dry-run mode
- Confirmation prompts
- Safety warnings for destructive operations
- Extra protection for portfolio state (7b)

### 3. `scripts/rerun-steps.sh`
**Purpose:** Rerun pipeline steps in correct dependency order

**Features:**
- Run specific step or step + downstream
- Automatic dependency ordering
- Date filtering support (where applicable)
- Dry-run mode
- Execution plan preview
- Skip deployment option

---

## Pipeline Dependency Graph

```
1. Exchange Rates
   ├─► 2. Currency Indices
   ├─► 6. Signal Realization
   └─► 8. Dashboard Deployment

2. Currency Indices
   └─► 8. Dashboard Deployment

3. News Aggregation
   ├─► 4. Time Horizon Analysis
   └─► 8. Dashboard Deployment

4. Time Horizon Analysis
   ├─► 5. Sentiment Signals
   └─► 8. Dashboard Deployment

5. Sentiment Signals
   ├─► 6. Signal Realization
   └─► 8. Dashboard Deployment

6. Signal Realization
   ├─► 7a. Trade Calculation
   └─► 8. Dashboard Deployment

7a. Trade Calculation
   ├─► 7b. Portfolio Execution
   └─► 8. Dashboard Deployment

7b. Portfolio Execution
   └─► 8. Dashboard Deployment

8. Dashboard Deployment
   (Terminal node - no downstream)
```

**Key Relationships:**
- Step 6 depends on both Step 5 (signals) and Step 1 (prices for realization check)
- Step 7b depends on both Step 7a (trades) and Step 6 (unrealized signals)
- Step 8 depends on all previous steps

---

## Usage Examples

### Clear Data

```bash
# Clear only Step 4 (Time Horizons)
./scripts/clear-data.sh 4

# Clear Step 3 and all downstream (3, 4, 5, 6, 7a, 7b)
./scripts/clear-data.sh 3 --downstream

# Clear Step 5 for specific date only
./scripts/clear-data.sh 5 --date 2026-02-25

# Preview what would be cleared (safe to run)
./scripts/clear-data.sh 3 --downstream --dry-run

# Clear everything (requires confirmation)
./scripts/clear-data.sh all

# Force clear without prompts (dangerous!)
./scripts/clear-data.sh 7b --force
```

### Rerun Steps

```bash
# Rerun only Step 4
./scripts/rerun-steps.sh 4

# Rerun Step 3 and all downstream (3, 4, 5, 6, 7a, 7b, 8)
./scripts/rerun-steps.sh 3 --downstream

# Rerun Step 5 for specific date
./scripts/rerun-steps.sh 5 --date 2026-02-25

# Preview execution plan (safe to run)
./scripts/rerun-steps.sh 3 --downstream --dry-run

# Run entire pipeline
./scripts/rerun-steps.sh all

# Rerun steps but skip deployment
./scripts/rerun-steps.sh 4 --downstream --skip-deploy
```

### Common Workflows

**Scenario 1: Re-fetch news for today**
```bash
# Clear today's news and reprocess everything downstream
./scripts/clear-data.sh 3 --downstream --date 2026-02-26
./scripts/rerun-steps.sh 3 --downstream --date 2026-02-26
```

**Scenario 2: Regenerate trades after fixing trade logic**
```bash
# Clear trades and portfolios, then rerun
./scripts/clear-data.sh 7a --downstream
./scripts/rerun-steps.sh 7a --downstream
```

**Scenario 3: Reset portfolio state and start fresh**
```bash
# Clear portfolios (requires confirmation)
./scripts/clear-data.sh 7b

# Rerun portfolio execution from scratch
./scripts/rerun-steps.sh 7b
```

**Scenario 4: Update LLM sentiment generator**
```bash
# Clear signals and downstream, then rerun
./scripts/clear-data.sh 5 --downstream
./scripts/rerun-steps.sh 5 --downstream
```

---

## Step Details

### Step 1: Exchange Rates
**Script:** `fetch-exchange-rates.py`
**Depends on:** Nothing (root node)
**Downstream:** 2, 6, 8
**Date filtering:** Yes
**Safe to clear:** Yes

**Outputs:**
- Source: `data/prices/fx-rates-*.json`
- Exports: `data/exports/step1_*.csv` and `*.json`

**Notes:**
- Root data source
- Always available from API

### Step 2: Currency Indices
**Script:** `calculate-currency-indices.py`
**Depends on:** 1
**Downstream:** 8
**Date filtering:** Yes
**Safe to clear:** Yes

**Outputs:**
- Source: `data/indices/*.json`
- Exports: `data/exports/step2_indices.csv`

### Step 3: News Aggregation
**Script:** `fetch-news.py`
**Depends on:** 1
**Downstream:** 4, 8
**Date filtering:** Yes
**Safe to clear:** Yes

**Outputs:**
- Source: `data/news/*/`, `data/news/url_index.json`
- Exports: `data/exports/step3_news.csv`

**⚠️  Warning:** News articles may not be re-fetchable for old dates

### Step 4: Time Horizon Analysis
**Script:** `analyze-time-horizons-llm.py`
**Depends on:** 3
**Downstream:** 5, 8
**Date filtering:** Yes
**Safe to clear:** Yes

**Outputs:**
- Source: `data/article-analysis/*.json`
- Exports: `data/exports/step4_horizons.csv`

**💰 Warning:** LLM API costs incurred when re-running

### Step 5: Sentiment Signals
**Script:** `generate-sentiment-signals-v2.py`
**Depends on:** 4
**Downstream:** 6, 8
**Date filtering:** Yes
**Safe to clear:** Yes

**Outputs:**
- Source: `data/signals/*/*.json`
- Exports: `data/exports/step5_signals.csv`

**💰 Warning:** LLM API costs incurred when re-running

### Step 6: Signal Realization
**Script:** `check-signal-realization.py`
**Depends on:** 5, 1
**Downstream:** 7a, 8
**Date filtering:** Yes
**Safe to clear:** Yes

**Outputs:**
- Source: `data/signals/*/*.json` (modifies in-place)
- Exports: `data/exports/step6_realization.csv`

**Note:** Modifies signal files to add `realized` flag

### Step 7a: Trade Calculation
**Script:** `calculate-trades.py`
**Depends on:** 6
**Downstream:** 7b, 8
**Date filtering:** Yes
**Safe to clear:** Yes

**Outputs:**
- Exports: `data/exports/step7a_trades.csv`

**Note:** No source data (recalculated each run)

### Step 7b: Portfolio Execution
**Script:** `execute-strategies.py`
**Depends on:** 7a, 6
**Downstream:** 8
**Date filtering:** Yes
**Safe to clear:** NO

**Outputs:**
- Source: `data/portfolios/*.json`
- Exports: `data/exports/step7_strategies.csv`, `step7_strategies_detail.json`

**🚨 WARNING:** Portfolio state is CUMULATIVE across dates. Clearing resets ALL history!

### Step 8: Dashboard Deployment
**Script:** `deploy-dashboard.sh`
**Depends on:** All previous steps
**Downstream:** None (terminal node)
**Date filtering:** No
**Safe to clear:** N/A

**Outputs:**
- Deploys to GitHub Pages
- No local data to clear

---

## Safety Features

### 1. Confirmation Prompts
Both scripts require confirmation before executing:
```
Proceed with clearing? (y/N):
Proceed with execution? (y/N):
```

**Override with:** `--force` (use with extreme caution!)

### 2. Dry Run Mode
Preview what would happen without actually doing it:
```bash
./scripts/clear-data.sh 3 --downstream --dry-run
./scripts/rerun-steps.sh 3 --downstream --dry-run
```

**Output:**
```
[DRY RUN] Removed: data/news/*/
[DRY RUN] Removed: data/article-analysis/*.json
...
```

### 3. Portfolio State Protection
Step 7b (Portfolio Execution) has extra protection:
```
🚨 WARNING: Portfolio state is cumulative!
Are you absolutely sure you want to clear portfolio state? (type 'yes'):
```

**Rationale:** Portfolio state accumulates across dates. Clearing it means starting over.

### 4. LLM Cost Warnings
Steps 4 and 5 show cost warnings:
```
💰 LLM API costs will be incurred when re-running
```

**Reminder:** Each article requires LLM API call for analysis/sentiment

### 5. Execution Plan Preview
Rerun script shows clear execution plan:
```
Execution order:
  3. News Aggregation
     Command: python3 scripts/fetch-news.py
  4. Time Horizon Analysis
     Command: python3 scripts/analyze-time-horizons-llm.py
     💰 LLM API costs will be incurred
  ...
```

---

## Dependency Resolution

### Clear Data Logic
When clearing with `--downstream`:
1. Identifies all downstream dependencies recursively
2. Sorts in dependency order
3. Shows what will be cleared
4. Requires confirmation
5. Executes in order

**Example:**
```bash
./scripts/clear-data.sh 3 --downstream
```

**Clears:** 3 → 4 → 5 → 6 → 7a → 7b (in order)

### Rerun Logic
When running with `--downstream`:
1. Identifies all downstream dependencies recursively
2. Sorts in topological order (respects dependencies)
3. Shows execution plan
4. Requires confirmation
5. Executes in correct order

**Example:**
```bash
./scripts/rerun-steps.sh 3 --downstream
```

**Runs:** 3 → 4 → 5 → 6 → 7a → 7b → 8 (in dependency order)

---

## Date Filtering

### Supported Steps
Steps that support date filtering:
- Step 1: Exchange Rates
- Step 2: Currency Indices
- Step 3: News Aggregation
- Step 4: Time Horizon Analysis
- Step 5: Sentiment Signals
- Step 6: Signal Realization
- Step 7a: Trade Calculation
- Step 7b: Portfolio Execution

### Not Supported
- Step 8: Dashboard Deployment (always includes all dates)

### Usage

**Clear specific date:**
```bash
./scripts/clear-data.sh 5 --date 2026-02-25
```

**Rerun for specific date:**
```bash
./scripts/rerun-steps.sh 5 --date 2026-02-25
```

**Clear multiple dates:**
```bash
# Create file with dates
echo "2026-02-24" > dates.txt
echo "2026-02-25" >> dates.txt

./scripts/clear-data.sh 5 --dates-file dates.txt
```

### How It Works

**Clear data:**
- Searches for files matching date pattern
- Deletes only matching files
- Example: `data/prices/fx-rates-2026-02-25.json`

**Rerun steps:**
- Passes `--date` argument to Python scripts
- Scripts filter/process only that date
- Falls back to latest/all if date not specified

---

## Error Handling

### Missing Configuration
```bash
Error: Pipeline configuration not found: config/pipeline_steps.json
```

**Solution:** Ensure `pipeline_steps.json` exists in config/

### Invalid Step
```bash
Error: Unknown step '9'
Valid steps: 1-6, 7a, 7b, 8, all
```

**Solution:** Use valid step ID

### Cancelled by User
```bash
Cancelled by user
```

**Solution:** User chose not to proceed (safe behavior)

---

## Integration with Existing Scripts

### Relationship to run-pipeline.sh
- `run-pipeline.sh`: Runs entire pipeline start-to-finish
- `rerun-steps.sh`: Runs specific steps with dependency handling
- `clear-data.sh`: Clears data before rerun

**When to use each:**
- **Full pipeline:** `./run-pipeline.sh`
- **Regenerate from step N:** `./scripts/rerun-steps.sh N --downstream`
- **Clear and regenerate:** `./scripts/clear-data.sh N --downstream && ./scripts/rerun-steps.sh N --downstream`

### Relationship to clear-step-data.sh
- **Old script:** `clear-step-data.sh` - Simple, no dependency handling
- **New script:** `clear-data.sh` - Smart, with dependencies and safety

**Migration:**
```bash
# Old way
./scripts/clear-step-data.sh 4

# New way (equivalent)
./scripts/clear-data.sh 4
```

**Advantages of new script:**
- Dependency awareness (`--downstream`)
- Date filtering (`--date`)
- Dry run (`--dry-run`)
- Better warnings
- Consistent interface with `rerun-steps.sh`

---

## Best Practices

### 1. Always Use Dry Run First
```bash
# Check what will happen
./scripts/clear-data.sh 3 --downstream --dry-run

# If satisfied, run for real
./scripts/clear-data.sh 3 --downstream
```

### 2. Clear and Rerun Together
```bash
# Clear then rerun in one go
./scripts/clear-data.sh 5 --downstream && ./scripts/rerun-steps.sh 5 --downstream
```

### 3. Use Date Filtering for Recent Data
```bash
# Only reprocess today's data
./scripts/clear-data.sh 4 --downstream --date $(date +%Y-%m-%d)
./scripts/rerun-steps.sh 4 --downstream --date $(date +%Y-%m-%d)
```

### 4. Back Up Portfolio State Before Clearing
```bash
# Back up before clearing 7b
cp -r data/portfolios data/portfolios.backup

# Clear if needed
./scripts/clear-data.sh 7b
```

### 5. Skip Deployment During Testing
```bash
# Rerun without deploying
./scripts/rerun-steps.sh 4 --downstream --skip-deploy
```

---

## Dashboard Integration

The `pipeline_steps.json` configuration is:
1. Copied to dashboard exports: `data/exports/pipeline_steps.json`
2. Deployed to GitHub Pages: `fx-dashboard/data/pipeline_steps.json`
3. Rendered on dashboard architecture page

**Visualization:**
- Step names and descriptions
- Dependency arrows
- Safety warnings
- Date filtering support indicators

---

## Testing the Scripts

### Test 1: Dry Run Clear
```bash
./scripts/clear-data.sh 4 --dry-run
```

**Expected:** Shows what would be cleared, no actual changes

### Test 2: Dry Run Rerun
```bash
./scripts/rerun-steps.sh 4 --dry-run
```

**Expected:** Shows execution plan, no actual execution

### Test 3: Clear Single Step
```bash
./scripts/clear-data.sh 2
```

**Expected:** Clears only Step 2 data, prompts for confirmation

### Test 4: Clear with Downstream
```bash
./scripts/clear-data.sh 4 --downstream --dry-run
```

**Expected:** Shows Steps 4, 5, 6, 7a, 7b will be cleared

### Test 5: Rerun with Downstream
```bash
./scripts/rerun-steps.sh 7a --downstream --dry-run
```

**Expected:** Shows Steps 7a, 7b, 8 will be run

---

## Permissions

Make scripts executable:
```bash
chmod +x scripts/clear-data.sh
chmod +x scripts/rerun-steps.sh
```

---

## Status: READY FOR VALIDATION ✅

**Created:**
- ✅ `config/pipeline_steps.json` - Dependency graph
- ✅ `scripts/clear-data.sh` - Smart clear script
- ✅ `scripts/rerun-steps.sh` - Smart rerun script
- ✅ `docs/PIPELINE_ORCHESTRATION_2026-02-26.md` - This documentation

**Not executed yet:**
- Scripts are ready but NOT run
- Awaiting user validation
- Safe to review without side effects

**Next Steps:**
1. User reviews configuration and scripts
2. Test with `--dry-run` flag
3. Validate dependency graph is correct
4. Deploy to dashboard for visualization

---

## Configuration Validation

### Validate pipeline_steps.json

```bash
# Check if valid JSON
cat config/pipeline_steps.json | python3 -m json.tool > /dev/null && echo "✓ Valid JSON"

# Check all steps referenced
python3 -c "
import json
with open('config/pipeline_steps.json') as f:
    config = json.load(f)
    steps = set(config['steps'].keys())
    print('Steps defined:', sorted(steps))

    # Check dependencies are valid
    for step_id, step in config['steps'].items():
        for dep in step['depends_on']:
            if dep not in steps:
                print(f'ERROR: Step {step_id} depends on undefined step {dep}')
            else:
                print(f'✓ Step {step_id} → {dep}')
"
```

---

## Future Enhancements

### 1. Parallel Execution
Steps with no dependencies could run in parallel:
```bash
# Run Steps 1 and 3 in parallel (both are independent)
./scripts/rerun-steps.sh 1,3 --parallel
```

### 2. Incremental Processing
Only process new/changed data:
```bash
./scripts/rerun-steps.sh 4 --incremental
```

### 3. Dependency Validation
Check if prerequisites are satisfied before running:
```bash
./scripts/rerun-steps.sh 7a --validate-deps
```

### 4. Progress Tracking
Show real-time progress:
```bash
./scripts/rerun-steps.sh all --progress
```

### 5. Rollback Support
Save state before clearing, allow rollback:
```bash
./scripts/clear-data.sh 4 --downstream --with-backup
./scripts/rollback.sh 4  # If something went wrong
```

---

## Summary

Created comprehensive pipeline orchestration system that:
- ✅ Defines step dependencies in JSON
- ✅ Provides safe clear-data script with dependency awareness
- ✅ Provides smart rerun script with dependency handling
- ✅ Supports date filtering for targeted operations
- ✅ Includes dry-run mode for safety
- ✅ Protects critical data (portfolios) with extra warnings
- ✅ Shows clear execution plans before running
- ✅ Can be visualized on dashboard

**Ready for user validation!**
