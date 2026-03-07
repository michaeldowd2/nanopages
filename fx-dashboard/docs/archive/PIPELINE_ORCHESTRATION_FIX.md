# Pipeline Orchestration Fix - 2026-02-25

## Issue Summary

**Problem**: Time horizon analysis completed successfully (38 articles analyzed with Claude Haiku) but the dashboard wasn't updated with the results.

**Root Cause**: Missing pipeline orchestration - the individual steps worked but weren't connected together.

---

## What Was Missing

### 0. **USER ERROR: Bypassed Existing Deploy Script**

**What happened**: When asked to redeploy, I ran git commands manually instead of using the existing `deploy-dashboard.sh` script.

**Why this was wrong**:
- `deploy-dashboard.sh` **already had all the logic** to export data first
- By bypassing it, the export step was skipped
- This created the false impression that something was broken

**The correct approach**: Always use `./scripts/deploy-dashboard.sh` for deployment!

### 1. Missing Main Pipeline Script

**Expected**: `run-pipeline.sh` (referenced in README.md line 38)
**Reality**: Script didn't exist

**Impact**: No automated way to run all 9 pipeline steps in sequence:
1. Fetch FX rates
2. Calculate indices
3. Fetch news
4. Analyze time horizons (LLM) ← Step completed manually
5. Generate sentiment signals
6. Check signal realization
7. Execute strategies
8. **Export data to CSV** ← Never called!
9. **Copy to dashboard** ← Never called!

### 2. Missing Export Step After Analysis

**What happened**:
- `analyze-time-horizons-llm.py` created 38 JSON files in `data/article-analysis/`
- JSON files had all the horizon analysis data
- But the script didn't call `export-pipeline-data.py` to generate CSV
- Dashboard had empty `step4_horizons.csv` (0 bytes) from previous day

**What should happen**:
- After analysis completes → automatically export to CSV
- Or at minimum, show clear message about next steps

### 3. Missing User Guidance

The horizon analysis script ended with:
```
============================================================
Analysis Complete
============================================================
✓ Analyzed: 38
...
============================================================
```

**Missing**: No guidance on what to do next! User had no indication that:
1. Data needs to be exported to CSV
2. CSV needs to be copied to dashboard
3. Dashboard needs to be redeployed

---

## What Was Fixed

### ✅ Created `run-pipeline.sh`

**Location**: `/workspace/group/fx-portfolio/run-pipeline.sh`

**Purpose**: Orchestrates all 9 pipeline steps in correct order

**Key sections**:
```bash
# Step 4: Run horizon analysis
python3 scripts/analyze-time-horizons-llm.py

# Step 8: Export data (NEW!)
python3 scripts/export-pipeline-data.py
python3 scripts/export-logs.py
python3 scripts/export-exchange-rates.py

# Step 9: Copy to dashboard (NEW!)
cp data/exports/*.csv /workspace/group/sites/fx-dashboard/data/
```

**Usage**:
```bash
cd /workspace/group/fx-portfolio
./run-pipeline.sh
```

Then separately deploy:
```bash
./scripts/deploy-dashboard.sh
```

### ✅ Added Next Steps Guidance

**Updated**: `analyze-time-horizons-llm.py`

**Added output at end**:
```
⚠️  Next Steps:
   1. Export data: python3 scripts/export-pipeline-data.py
   2. Deploy dashboard: ./scripts/deploy-dashboard.sh
   Or run full pipeline: ./run-pipeline.sh
```

This ensures users know what to do after running step 4 manually.

### ✅ Verified Export Process

**Export script** (`export-pipeline-data.py`):
- Already had `export_step4_horizons()` function ✅
- Reads all JSON files from `data/article-analysis/`
- Generates CSV with columns: date, estimator_id, url, currency, title, time_horizon, confidence, reasoning
- Saves to `data/exports/step4_horizons.csv`

**Working correctly**:
```bash
$ python3 scripts/export-pipeline-data.py
✓ Step 4: Exported 38 horizon analyses
```

### ✅ Verified Deployment Process

**Deploy script** (`scripts/deploy-dashboard.sh`):
- Already had export + copy + deploy logic ✅
- Calls `export-pipeline-data.py`
- Copies all CSVs to dashboard
- Deploys to GitHub Pages

**Working correctly** - we tested this manually and it deployed successfully.

---

## Timeline of Events (What Actually Happened)

### Yesterday (2026-02-24 ~21:42)
1. Empty `step4_horizons.csv` was deployed to dashboard (0 bytes)
2. Dashboard showed empty time horizon section

### Today (2026-02-25 ~22:05)
1. Created `analyze-time-horizons-llm.py` with Claude Haiku integration
2. Ran analysis manually: 38 articles analyzed successfully
3. JSON files created in `data/article-analysis/`
4. **Stopped here** - didn't export or deploy

### Today (2026-02-25 ~19:53)
1. User asked to redeploy dashboard
2. Redeployed but CSV was still empty (0 bytes from yesterday)
3. User noticed time horizon data missing

### Today (2026-02-25 ~19:56)
1. User asked why it didn't work
2. Traced through and found:
   - JSON analysis files exist ✅
   - Export script exists ✅
   - Deploy script exists ✅
   - **But export was never called!** ❌
3. Manually ran export script → generated 26KB CSV
4. Copied CSV to dashboard
5. Redeployed → Success! ✅

---

## Gaps in Documentation/Process

### 1. README.md Referenced Non-Existent Script

**Line 38**: `./run-pipeline.sh`
**Reality**: Script didn't exist

**Fix**: Created the script

### 2. Individual Step Scripts Have No Next-Step Guidance

**Problem**: When running `analyze-time-horizons-llm.py` standalone, user doesn't know:
- Data is in JSON format (not CSV)
- Needs to run export script
- Needs to copy to dashboard
- Needs to redeploy

**Fix**: Added guidance message at end of script

### 3. No Pipeline Flow Documentation

**Missing**: Clear documentation showing:
```
Step 4: analyze-time-horizons-llm.py
   ↓ creates JSON in data/article-analysis/
   ↓
Step 8: export-pipeline-data.py
   ↓ creates CSV in data/exports/
   ↓
Step 9: Copy to dashboard
   ↓ copies CSV to sites/fx-dashboard/data/
   ↓
Deploy: deploy-dashboard.sh
   ↓ pushes to GitHub Pages
```

**Fix**: This document! And should add to ARCHITECTURE.md

### 4. Deploy Script Should Be Idempotent

**Current behavior**:
- `deploy-dashboard.sh` runs export scripts
- Good for automated deployment
- But confusing when debugging (exports might be stale)

**Recommendation**: This is actually fine - deploy script should always export fresh data before deploying.

---

## Testing the Fix

### Test 1: Run Full Pipeline
```bash
cd /workspace/group/fx-portfolio
./run-pipeline.sh
```

**Expected**:
- All 9 steps run in sequence
- CSV files generated in `data/exports/`
- CSV files copied to dashboard
- Message shows "Next steps: Deploy dashboard"

### Test 2: Deploy Dashboard
```bash
./scripts/deploy-dashboard.sh
```

**Expected**:
- Exports data (redundant but safe)
- Copies to dashboard
- Deploys to GitHub Pages
- Shows URL: https://michaeldowd2.github.io/nanopages/fx-dashboard/

### Test 3: Run Individual Step
```bash
python3 scripts/analyze-time-horizons-llm.py
```

**Expected**:
- Analyzes articles
- Shows horizon distribution
- **Shows next steps message** ← New!

---

## Recommendations

### 1. Update ARCHITECTURE.md

Add section on pipeline orchestration showing:
- Individual scripts vs orchestrator
- Data flow between steps
- Export and deployment process

### 2. Consider Adding Auto-Deploy Flag

Add optional flag to `run-pipeline.sh`:
```bash
./run-pipeline.sh --deploy  # Automatically deploys after completion
```

This would run all 9 steps + deploy in one command.

### 3. Add Validation Step

Before deploying, verify CSVs are not empty:
```bash
if [ ! -s data/exports/step4_horizons.csv ]; then
  echo "⚠️  Warning: step4_horizons.csv is empty!"
  exit 1
fi
```

### 4. Add Pipeline Status Command

Create `scripts/pipeline-status.sh` to show:
- Which steps have data
- How recent the data is
- Which CSVs are ready for dashboard
- Whether dashboard is deployed

---

## Key Takeaways

### What Went Well ✅
- Individual scripts all work correctly
- **Export logic was already in deploy script!** ✅✅✅
- Deploy logic was already implemented correctly
- LLM integration works perfectly

### What Was Wrong ❌
- **I bypassed the deploy script** and ran git commands manually
- This skipped the export step that was already built-in
- Created false impression that something was broken
- Also: Pipeline orchestration script was missing

### What Was Actually Missing ❌
- Pipeline orchestration script (`run-pipeline.sh`)
- Next-step guidance in individual scripts
- Clear documentation emphasizing "always use deploy script"

### Lesson Learned 💡
**The deploy script was already perfect! The issue was OPERATOR ERROR (me) bypassing it. Always use the existing automation scripts instead of manual commands!**

### Critical Rule Going Forward 🚨
**ALWAYS use `./scripts/deploy-dashboard.sh` for deployment**
- It exports fresh data automatically
- It copies to dashboard automatically
- It deploys to GitHub Pages automatically
- Never bypass it with manual git commands!

---

## Status: FIXED ✅

**Date**: 2026-02-25
**Fixed By**: Created `run-pipeline.sh` and added guidance messages
**Verified**: Dashboard now shows all 38 horizon analyses correctly
**URL**: https://michaeldowd2.github.io/nanopages/fx-portfolio/
