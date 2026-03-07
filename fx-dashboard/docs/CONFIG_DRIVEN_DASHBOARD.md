# Config-Driven Dashboard Architecture

**Date**: 2026-02-26
**Status**: ✅ Fully Implemented

## Overview

The FX Portfolio Dashboard is now **100% config-driven**. Adding a new pipeline step requires **only** editing `config/pipeline_steps.json` - no HTML/JavaScript editing needed.

## How It Works

### 1. Single Source of Truth

**File**: `config/pipeline_steps.json`

This JSON file defines:
- All pipeline steps (1-9)
- Step names and descriptions
- Dependencies between steps
- Output file patterns
- Whether steps support date filtering

### 2. Dynamic Tab Generation

On page load, JavaScript:
1. Fetches `pipeline_steps.json`
2. **Generates navigation tabs** dynamically for each step
3. **Creates tab content sections** automatically
4. **Loads CSV data** for each step
5. **Populates date filters** where applicable

### 3. Zero Manual HTML Editing

**Before** (Manual):
```html
<!-- Had to manually add -->
<div class="tab" onclick="showTab('step9')">STEP 9</div>

<div id="step9" class="tab-content">
  <div class="section">
    <h2>Step 9: Risk Analysis</h2>
    <!-- ... lots of boilerplate ... -->
  </div>
</div>
```

**After** (Config-Driven):
```json
{
  "steps": {
    "9": {
      "id": "9",
      "name": "Risk Analysis",
      "description": "Calculate VaR and risk metrics",
      "depends_on": ["8"],
      "outputs": {
        "exports": ["data/exports/step9_risk.csv"]
      },
      "supports_date_filter": true
    }
  }
}
```

The dashboard **automatically**:
- Adds "STEP 9" tab to navigation
- Creates content section with table
- Adds date filter (if `supports_date_filter: true`)
- Loads `step9_risk.csv`
- Handles CSV rendering

## Adding a New Step

### Example: Add "Risk Analysis" as Step 9

**Step 1**: Insert into `config/pipeline_steps.json`

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
    "is_safe_to_clear": true
  },
  "10": {
    "id": "10",
    "name": "Dashboard Deployment",
    "depends_on": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    ...
  }
}
```

**Step 2**: Create the script

```python
# scripts/analyze-risk.py
# Output to: data/exports/step9_risk.csv
```

**Step 3**: Deploy

```bash
./scripts/deploy-dashboard.sh
```

**That's it!** The dashboard will:
- Show "STEP 9" tab automatically
- Create the data table
- Add date filtering
- Load and render the CSV

## Special Cases

### Step 1 (Exchange Rates)
- Uses **matrix format** instead of standard table
- Has custom JavaScript (`loadExchangeRateMatrix()`)
- Manually defined in HTML (exception to the rule)

### Step 8 (Portfolio Execution)
- Gets **enhanced UI** with:
  - Portfolio value charts
  - Strategy selector dropdown
  - Currency signals display
  - Trade recommendations
- Defined by `generatePortfolioContent()` function
- Still config-driven, just with richer UI

### Step 9 (Dashboard Deployment)
- **Excluded from tabs** (filter: `id !== '9'`)
- Not a data viewing step, so no tab needed

## File Naming Convention

The dashboard expects exports to follow this pattern:

```
data/exports/step{N}_{name}.csv
```

Examples:
- `step2_indices.csv`
- `step3_news.csv`
- `step7_trades.csv`
- `step8_strategies.csv`
- `step9_risk.csv` (future)

The `{name}` part is determined by `getDefaultFilename()`:

```javascript
function getDefaultFilename(stepId) {
  const filenames = {
    '2': 'indices',
    '3': 'news',
    '4': 'horizons',
    '5': 'signals',
    '6': 'realization',
    '7': 'trades',
    '8': 'strategies',
    '9': 'risk'  // Add new ones here
  };
  return filenames[stepId] || 'data';
}
```

## Dashboard Structure

```
OVERVIEW     → Pipeline architecture, visual graph, step dependencies
CONFIG       → System configuration (estimators, generators, strategies)
STEP 1       → Exchange rates (special matrix view)
STEP 2       → Currency indices (auto-generated from config)
STEP 3       → News aggregation (auto-generated)
STEP 4       → Time horizons (auto-generated)
STEP 5       → Sentiment signals (auto-generated)
STEP 6       → Signal realization (auto-generated)
STEP 7       → Trade calculation (auto-generated)
STEP 8       → Portfolio execution (auto-generated with enhanced UI)
TRACKING     → Pipeline run logs
```

## Benefits

### ✅ Easy to Extend
Add new steps by editing one JSON file

### ✅ Consistent UI
All steps use the same table layout and date filtering

### ✅ No Code Duplication
Step tabs are generated from a template

### ✅ Self-Documenting
The config file serves as documentation

### ✅ Maintainable
Changes propagate automatically across the entire dashboard

## Implementation Details

### Key Functions

#### `initializeDashboard()`
- Entry point
- Loads config and triggers generation
- Fallback to static tabs if config fails

#### `generateDynamicTabs(config)`
- Reads `config.steps`
- Creates `<div class="tab">` elements
- Inserts into navigation bar
- Filters out step 9 (deployment)

#### `generateDynamicContent(config)`
- Creates `<div id="stepX" class="tab-content">` sections
- Adds headers, descriptions, date filters
- Calls `generateTableContent()` or `generatePortfolioContent()`
- Inserts before tracking tab

#### `generateTableContent(stepId)`
- Standard table template
- Used for steps 2-7

#### `generatePortfolioContent(stepId)`
- Enhanced template for step 8
- Adds charts and strategy selector

### CSV Loading

The `loadCSV(step)` function:
1. Checks file mapping in `csvFile` object
2. Fetches the CSV
3. Parses with `parseCSV()`
4. Populates date filter
5. Renders table with headers/rows

## Migration Notes

### What Was Removed

**Static HTML tabs**:
- Deleted hardcoded step2-8 `<div>` sections
- Removed TRADES tab (redundant with step 7)

**Hardcoded loading**:
- Removed `forEach(loadCSV)` with hardcoded array
- Now reads step IDs from config

### What Was Kept

**Step 1**:
- Special matrix view requires custom JavaScript
- Too complex to auto-generate

**TRACKING tab**:
- Not a pipeline step
- Utility view for debugging

**CONFIG tab**:
- System configuration view
- Not a pipeline step

## Future Enhancements

### Auto-Calculate Graph Layout
Currently `layout` object has hardcoded coordinates:
```javascript
const layout = {
  '7': { x: 700, y: 150, layer: 3 },
  '8': { x: 900, y: 150, layer: 4 }
};
```

Could be auto-calculated from dependency depth:
```javascript
function calculateLayout(steps) {
  // Topological sort to get layers
  // Space nodes evenly within each layer
  // Return {stepId: {x, y, layer}}
}
```

### Configurable File Patterns
Instead of hardcoded `getDefaultFilename()`, read from config:
```json
{
  "9": {
    "outputs": {
      "exports": [
        {"path": "step9_risk.csv", "label": "Risk Metrics"}
      ]
    }
  }
}
```

### Template Overrides
Allow steps to specify custom templates:
```json
{
  "9": {
    "ui_template": "chart_view",  // vs. default "table_view"
    ...
  }
}
```

## Testing

After modifying `pipeline_steps.json`:

1. **Validate JSON**:
   ```bash
   python3 -m json.tool config/pipeline_steps.json
   ```

2. **Check dependencies**:
   ```bash
   ./scripts/resolve-dependencies.py --validate
   ```

3. **Deploy**:
   ```bash
   ./scripts/deploy-dashboard.sh
   ```

4. **Verify**:
   - Hard refresh browser (Ctrl+Shift+R)
   - Check new tab appears
   - Verify CSV loads
   - Test date filtering

## Summary

The dashboard is now **fully config-driven** with zero HTML editing required to add new steps. This makes the system:
- **Scalable** - Easy to add steps 10, 11, 12...
- **Maintainable** - One source of truth
- **Consistent** - All steps use same UI patterns
- **Self-documenting** - Config explains the structure

Adding a new step is as simple as editing a JSON file and creating the data export script!
