# Managing Pipeline Step Numbers

**Last Updated**: 2026-02-26

## Overview

The FX Portfolio Pipeline uses sequential step numbering (1, 2, 3, ..., N). This document explains how to insert new steps or renumber existing ones without breaking the system.

## Current Step Numbering (as of 2026-02-26)

```
1. Exchange Rates
2. Currency Indices
3. News Aggregation
4. Time Horizon Analysis
5. Sentiment Signals
6. Signal Realization
7. Trade Calculation
8. Portfolio Execution
9. Dashboard Deployment
```

## Architecture Design

The pipeline is **config-driven** to minimize manual updates when renumbering:

### ✅ Config-Driven Components (Update Automatically)
These read from `config/pipeline_steps.json` and adapt automatically:
- `scripts/resolve-dependencies.py` - Dependency resolution
- `scripts/rerun-steps-v2.sh` - Step orchestration
- `scripts/clear-data-v2.sh` - Data clearing
- `scripts/export-pipeline-data.py` - Data export
- Visual dependency graph on dashboard

### ⚠️ Manual Update Required
These have hardcoded step references that must be updated manually:
- `run-pipeline.sh` - Main pipeline runner (echo statements)
- `sites/fx-dashboard/index.html` - Dashboard navigation and tabs
- Documentation files (`.md` files)
- Export file naming patterns (`step7_trades.csv` → `step8_trades.csv`)

## How to Insert a New Step

### Example: Insert "Risk Analysis" as Step 9 (between Portfolio and Dashboard)

Current state: `... → 8 (Portfolio) → 9 (Dashboard)`
Goal: `... → 8 (Portfolio) → 9 (Risk Analysis) → 10 (Dashboard)`

### Step 1: Update `config/pipeline_steps.json`

```json
{
  "steps": {
    "8": {
      "id": "8",
      "name": "Portfolio Execution",
      "depends_on": ["7"],
      ...
    },
    "9": {
      "id": "9",
      "name": "Risk Analysis",
      "script": "scripts/analyze-risk.py",
      "description": "Calculate VaR and risk metrics",
      "depends_on": ["8"],
      "outputs": {
        "source": ["data/risk/*.json"],
        "exports": ["data/exports/step9_risk.csv"]
      },
      "supports_date_filter": true,
      "is_safe_to_clear": true
    },
    "10": {
      "id": "10",
      "name": "Dashboard Deployment",
      "depends_on": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
      ...
    }
  }
}
```

**Key points:**
- Renumber old step 9 → 10
- Insert new step 9
- Update step 10's `depends_on` array to include new step 9

### Step 2: Update `run-pipeline.sh`

```bash
# Step 8: Execute Portfolio Strategies
echo "Step 8: Executing portfolio strategies..."
python3 scripts/execute-strategies.py
echo ""

# Step 9: Analyze Risk
echo "Step 9: Analyzing portfolio risk..."
python3 scripts/analyze-risk.py
echo ""

# Step 10: Export and Deploy Dashboard
echo "Step 10: Deploying dashboard..."
./scripts/deploy-dashboard.sh
echo ""
```

### Step 3: Update Dashboard HTML (`sites/fx-dashboard/index.html`)

#### 3a. Update Navigation Tabs
```html
<div class="tabs">
  ...
  <div class="tab" onclick="showTab('step8')">STEP 8: PORTFOLIOS</div>
  <div class="tab" onclick="showTab('step9')">STEP 9</div>
  <div class="tab" onclick="showTab('trades')">TRADES</div>
  ...
</div>
```

#### 3b. Update Graph Layout (JavaScript)
```javascript
const layout = {
  '1': { x: 100, y: 50, layer: 0 },
  '3': { x: 100, y: 200, layer: 0 },
  '2': { x: 300, y: 50, layer: 1 },
  '4': { x: 300, y: 200, layer: 1 },
  '5': { x: 300, y: 280, layer: 1 },
  '6': { x: 500, y: 150, layer: 2 },
  '7': { x: 700, y: 150, layer: 3 },
  '8': { x: 900, y: 150, layer: 4 },
  '9': { x: 1100, y: 150, layer: 5 },  // NEW
  '10': { x: 1300, y: 150, layer: 6 }  // Renumbered from 9
};
```

#### 3c. Update Step Sorting
```javascript
const sortedSteps = Object.keys(steps).sort((a, b) => {
  const order = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10'];
  return order.indexOf(a) - order.indexOf(b);
});
```

#### 3d. Add Tab Content Section
```html
<div id="step9" class="tab-content">
  <div class="section">
    <h2>Step 9: Risk Analysis <a href="data/step9_risk.csv" class="csv-download" download>CSV</a></h2>
    <p class="step-header">Portfolio risk metrics</p>

    <div class="csv-table-container">
      <div class="loading" id="step9-loading">Loading...</div>
      <table id="step9-table" style="display:none;">
        <thead id="step9-thead"></thead>
        <tbody id="step9-tbody"></tbody>
      </table>
    </div>
  </div>
</div>
```

#### 3e. Update CSV Loading (JavaScript)
```javascript
// Add 'step9' to the array
['step2', 'step3', 'step4', 'step5', 'step6', 'step9'].forEach(loadCSV);
```

### Step 4: Rename Export Files

If the old dashboard deployment (step 9 → 10) produces exports, the filenames don't need renaming since deployment doesn't create step-numbered files. However, if your new step creates `step9_risk.csv`, ensure:

```python
# In scripts/analyze-risk.py
output_file = 'data/exports/step9_risk.csv'
```

### Step 5: Update Documentation

Update these files to reflect new numbering:
- `README.md` - If it mentions step numbers
- `docs/PIPELINE_ARCHITECTURE*.md` - Update step diagrams
- `TESTING.md` - If it references specific steps

### Step 6: Test

```bash
# Validate dependency graph
./scripts/resolve-dependencies.py --validate

# Test dry-run
./scripts/rerun-steps-v2.sh 9 --dry-run

# Test execution
./scripts/rerun-steps-v2.sh 9

# Deploy
./scripts/deploy-dashboard.sh
```

## How to Renumber Steps (Bulk)

If you need to renumber multiple steps at once (e.g., 7a→7, 7b→8, 8→9):

### Quick Checklist

1. **Config**:
   - Update `config/pipeline_steps.json` step IDs
   - Update `depends_on` arrays
   - Update notes section references

2. **Scripts**:
   - Update `run-pipeline.sh` echo statements
   - Check for hardcoded step numbers in custom scripts

3. **Dashboard**:
   - Update `sites/fx-dashboard/index.html`:
     - Navigation tab labels
     - Tab `id` attributes (`id="step7"` → `id="step8"`)
     - Graph layout positions
     - Step sorting order array
     - CSV download hrefs
     - JavaScript element IDs
     - `loadCSV()` array

4. **Exports**:
   - Rename export files if needed (`step7_*.csv` → `step8_*.csv`)
   - Update any scripts that reference old filenames

5. **Documentation**:
   - Update all `.md` files mentioning step numbers
   - Update architecture diagrams

6. **Test**:
   - Run `./scripts/resolve-dependencies.py --validate`
   - Test with `--dry-run` flags
   - Check dashboard renders correctly

## File Naming Convention for Exports

**Pattern**: `step{N}_{description}.{ext}`

Examples:
- `step1_exchange_rates.csv`
- `step7_trades.csv`
- `step8_strategies.csv`

When renumbering, use search & replace:
```bash
# Example: Renaming step 7 exports to step 8
mv data/exports/step7_trades.csv data/exports/step8_trades.csv
```

## Common Gotchas

1. **Forgetting Dashboard Tab IDs**: The `id` attribute must match the onclick handler
   ```html
   <!-- WRONG -->
   <div class="tab" onclick="showTab('step8')">STEP 7</div>
   <div id="step7" class="tab-content">...</div>

   <!-- RIGHT -->
   <div class="tab" onclick="showTab('step8')">STEP 8</div>
   <div id="step8" class="tab-content">...</div>
   ```

2. **Forgetting Graph Layout**: Add new steps to the `layout` object with appropriate x,y coordinates

3. **Not Updating Dependencies**: When inserting a step, update `depends_on` for ALL downstream steps

4. **Export File Names**: If a step produces `step7_*.csv`, renaming the step to 8 requires renaming files

## Future Improvement: Fully Config-Driven Dashboard

To eliminate manual HTML updates, consider:
- Generate dashboard tabs dynamically from `pipeline_steps.json`
- Auto-calculate graph layout based on dependency depth
- Use step `name` field for tab labels
- Make CSV filenames configurable in config

This would make the system fully extensible without HTML/JS editing.

## Questions?

- See `docs/PIPELINE_ARCHITECTURE_2026-02-26.md` for system overview
- Check `config/pipeline_steps.json` for current configuration
- Run `./scripts/resolve-dependencies.py --help` for dependency tools
