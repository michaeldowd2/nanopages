# Deployment Best Practices

## Critical Rule 🚨

**ALWAYS use `./scripts/deploy-dashboard.sh` for deployment**

Never bypass this script with manual git commands!

---

## Why This Matters

### ✅ The Deploy Script Does Everything Right

`./scripts/deploy-dashboard.sh` automatically:

1. **Exports fresh data** from all pipeline steps
   - Runs `export-pipeline-data.py` (converts JSON to CSV)
   - Runs `export-logs.py` (exports pipeline logs)
   - Runs `export-exchange-rates.py` (exports rate matrix)

2. **Copies to dashboard**
   - Copies all CSVs to `sites/fx-dashboard/data/`
   - Copies all JSONs to `sites/fx-dashboard/data/`

3. **Deploys to GitHub Pages**
   - Clones nanopages repo
   - Updates fx-dashboard subfolder
   - Commits and pushes
   - Shows URL when complete

### ❌ What Happens If You Bypass It

If you run git commands manually:
- **Skips export step** → Stale data deployed
- **Skips copy step** → Missing files in dashboard
- **Creates confusion** → Appears broken when it's not

**Example of what NOT to do**:
```bash
# ❌ WRONG - Manual deployment
git clone ...
cp -r sites/fx-dashboard ...
git commit && git push
```

**Example of what TO do**:
```bash
# ✅ CORRECT - Use the script
./scripts/deploy-dashboard.sh
```

---

## Complete Workflow

### Daily Pipeline Run

```bash
cd /workspace/group/fx-portfolio

# Run all analysis steps
./run-pipeline.sh

# Deploy dashboard (exports + deploys)
./scripts/deploy-dashboard.sh
```

### Quick Deploy (Re-deploy Existing Data)

If you've already run the pipeline and just want to redeploy:

```bash
cd /workspace/group/fx-portfolio

# This STILL exports fresh data before deploying
./scripts/deploy-dashboard.sh
```

**Why export again?** Because data might have changed since last export. Always safer to re-export.

### Individual Step Testing

If you're testing a single step:

```bash
# Run the step
python3 scripts/analyze-time-horizons-llm.py

# Deploy (which will export all steps including the one you just ran)
./scripts/deploy-dashboard.sh
```

---

## What Each Script Does

### `run-pipeline.sh` (Pipeline Execution)

**Purpose**: Runs all 7 analysis steps

**Steps**:
1. Fetch FX rates
2. Calculate currency indices
3. Fetch news articles
4. Analyze time horizons (LLM)
5. Generate sentiment signals
6. Check signal realization
7. Execute trading strategies

**What it DOESN'T do**: Export or deploy

**When to use**: Daily pipeline runs, after code changes

### `deploy-dashboard.sh` (Export + Deploy)

**Purpose**: Export data and deploy to GitHub Pages

**Steps**:
1. **Export all data** (JSON → CSV)
2. **Copy to dashboard** folder
3. **Deploy to GitHub Pages**

**When to use**: After pipeline runs, when you want to update dashboard

---

## Common Scenarios

### Scenario 1: Daily Pipeline Run

```bash
# Run analysis
./run-pipeline.sh

# Deploy
./scripts/deploy-dashboard.sh
```

### Scenario 2: Only News Changed

```bash
# Re-fetch news
python3 scripts/fetch-news.py
python3 scripts/analyze-time-horizons-llm.py
python3 scripts/generate-sentiment-signals.py

# Deploy (will export all steps)
./scripts/deploy-dashboard.sh
```

### Scenario 3: Dashboard UI Changes

If you only changed `sites/fx-dashboard/index.html`:

```bash
# Still use deploy script (it's idempotent)
./scripts/deploy-dashboard.sh
```

This will re-export data (harmless) and deploy the new HTML.

### Scenario 4: Debugging Why Dashboard Is Stale

**Wrong approach**:
```bash
# ❌ Check if CSVs are up to date
ls -la sites/fx-dashboard/data/

# ❌ Manually copy files
cp data/exports/*.csv sites/fx-dashboard/data/

# ❌ Manually deploy
git clone ... && git push ...
```

**Right approach**:
```bash
# ✅ Just redeploy (exports + deploys)
./scripts/deploy-dashboard.sh
```

The script handles everything correctly!

---

## Troubleshooting

### "Dashboard showing old data"

**Solution**: Redeploy
```bash
./scripts/deploy-dashboard.sh
```

This will export fresh data and deploy it.

### "Step 4 data not showing"

**Check**: Did you run the deploy script?
```bash
# Run analysis
python3 scripts/analyze-time-horizons-llm.py

# Deploy (exports step 4 to CSV)
./scripts/deploy-dashboard.sh
```

### "Empty CSV in dashboard"

**Cause**: Either:
1. No source data (JSON files don't exist)
2. Deploy script wasn't used

**Solution**:
```bash
# Check if JSON files exist
ls data/article-analysis/*.json

# If they exist, redeploy
./scripts/deploy-dashboard.sh
```

---

## Script Hierarchy

```
run-pipeline.sh           (Runs all analysis steps 1-7)
    ├── fetch-fx-rates.py
    ├── calculate-indices.py
    ├── fetch-news.py
    ├── analyze-time-horizons-llm.py
    ├── generate-sentiment-signals.py
    ├── check-signal-realization.py
    └── execute-strategies.py

deploy-dashboard.sh       (Exports + deploys)
    ├── export-pipeline-data.py     (JSON → CSV)
    ├── export-logs.py
    ├── export-exchange-rates.py
    ├── cp data/exports/* → sites/fx-dashboard/data/
    └── git clone + commit + push
```

**Key insight**: These are separate because:
- Pipeline runs can happen multiple times per day
- Deployment happens less frequently
- You might want to run pipeline without deploying (testing)
- But you NEVER want to deploy without exporting!

---

## Deployment Checklist ✓

Before deploying, ensure:

- [ ] Pipeline has run (or at least the steps you care about)
- [ ] You're using `./scripts/deploy-dashboard.sh`
- [ ] NOT using manual git commands
- [ ] NOT copying files manually

After deploying:

- [ ] Check output for "Deployment Complete"
- [ ] Note the dashboard URL
- [ ] Wait 1-2 minutes for GitHub Pages
- [ ] Hard refresh browser (Ctrl+Shift+R)

---

## Summary

### The Golden Rule 🏆

**Always use `./scripts/deploy-dashboard.sh` for deployment**

This script:
- ✅ Exports fresh data automatically
- ✅ Copies to dashboard automatically
- ✅ Deploys to GitHub Pages automatically
- ✅ Is idempotent (safe to run multiple times)
- ✅ Handles errors gracefully

### Why It Existed But Got Bypassed

The deploy script was already perfect! The issue on 2026-02-25 was operator error (me) bypassing it with manual git commands. This created the false impression that data export was missing.

**Lesson**: Trust the automation scripts! They exist for a reason.

---

## Quick Reference

```bash
# Daily workflow
./run-pipeline.sh                    # Run analysis
./scripts/deploy-dashboard.sh        # Export + deploy

# Quick deploy
./scripts/deploy-dashboard.sh        # Always exports first!

# NEVER do this
git clone ... && git push ...        # ❌ Bypasses export
```

**Dashboard URL**: https://michaeldowd2.github.io/nanopages/fx-portfolio/
