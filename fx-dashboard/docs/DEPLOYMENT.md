# FX Dashboard Deployment Guide

## CRITICAL: DEPLOYMENT METHOD

⚠️ **ONLY DEPLOYMENT METHOD: GitHub Pages via Git Push** ⚠️

The FX dashboard is deployed **EXCLUSIVELY** to GitHub Pages using git push.

**NO OTHER DEPLOYMENT METHODS ARE PERMITTED.**
- ❌ **DO NOT use Surge** (deprecated and removed)
- ❌ **DO NOT use any other hosting service**
- ✅ **ONLY use GitHub Pages via git push**

**Dashboard URL:** https://michaeldowd2.github.io/nanopages/fx-dashboard/

---

## Prerequisites

1. **Environment Variables**
   ```bash
   GITHUB_TOKEN=github_pat_xxxxx  # GitHub personal access token
   GITHUB_REPO=https://github.com/username/nanopages  # Repository URL
   ```

2. **Repository Structure**
   ```
   nanopages/
   └── fx-dashboard/
       ├── index.html
       ├── data/
       │   ├── step1_exchange_rates.csv
       │   ├── step2_indices.csv
       │   ├── ...
       │   └── tracking_dates.json
       └── ...
   ```

---

## Deployment Steps

### 1. Export Latest Data

```bash
cd /workspace/group/fx-portfolio

# Export pipeline data
python3 scripts/export-pipeline-data.py

# Export logs
python3 scripts/export-logs.py

# Export exchange rates
python3 scripts/export-exchange-rates.py
```

### 2. Copy Data to Dashboard

```bash
# Copy all exports to dashboard data directory
cp data/exports/*.csv /workspace/group/sites/fx-dashboard/data/
cp data/exports/*.json /workspace/group/sites/fx-dashboard/data/
```

### 3. Deploy to GitHub Pages

```bash
SITE_NAME="fx-dashboard"
SOURCE="/workspace/group/sites/$SITE_NAME"
DEPLOY_DIR="/tmp/nanopages-deploy"
REPO_URL=$(echo "$GITHUB_REPO" | sed "s|https://|https://x-access-token:${GITHUB_TOKEN}@|")

# Clone repository
rm -rf "$DEPLOY_DIR"
git clone "$REPO_URL" "$DEPLOY_DIR"

# Configure git
cd "$DEPLOY_DIR"
git config user.name "nano"
git config user.email "nano@nanoclaw"

# Copy files
rm -rf "$DEPLOY_DIR/$SITE_NAME"
mkdir -p "$DEPLOY_DIR/$SITE_NAME"
cp -r "$SOURCE/." "$DEPLOY_DIR/$SITE_NAME/"

# Commit and push
git add -A
if git diff --cached --quiet; then
  echo "No changes — already up to date."
else
  git commit -m "Update $SITE_NAME: $(date -u '+%Y-%m-%d %H:%M UTC')"
  git push origin main
  echo "✓ Deployed to: https://michaeldowd2.github.io/nanopages/$SITE_NAME/"
fi
```

### 4. Verify Deployment

Visit: https://michaeldowd2.github.io/nanopages/fx-dashboard/

Check:
- ✓ OVERVIEW tab loads
- ✓ Step tabs (1-7) show data
- ✓ TRACKING tab shows run logs
- ✓ CONFIG tab shows configurations

---

## Automated Deployment

### Recommended: Python Script (Full Pipeline)

The Python deployment script handles the complete process with proper logging:

```bash
cd /workspace/group/fx-portfolio
python3 scripts/deploy-dashboard.py
```

**What it does:**
1. **Clears** old dashboard data files
2. **Re-exports** all pipeline data from source (runs all export scripts)
3. **Copies** fresh exports to dashboard folder
4. **Deploys** to GitHub Pages with git push
5. **Logs** the entire process to pipeline logs

**Benefits:**
- Ensures dashboard always has latest data
- No stale files from previous runs
- Full pipeline logging
- Single command deployment

### Alternative: Bash Script (Legacy)

The bash script is also available:

```bash
#!/bin/bash
set -e

echo "================================================================"
echo "FX Dashboard Deployment"
echo "================================================================"

# 1. Export data
echo "1. Exporting pipeline data..."
cd /workspace/group/fx-portfolio
python3 scripts/export-pipeline-data.py
python3 scripts/export-logs.py
python3 scripts/export-exchange-rates.py

# 2. Copy to dashboard
echo "2. Copying to dashboard..."
cp data/exports/*.csv /workspace/group/sites/fx-dashboard/data/ 2>/dev/null || true
cp data/exports/*.json /workspace/group/sites/fx-dashboard/data/ 2>/dev/null || true

# 3. Deploy
echo "3. Deploying to GitHub Pages..."
SITE_NAME="fx-dashboard"
SOURCE="/workspace/group/sites/$SITE_NAME"
DEPLOY_DIR="/tmp/nanopages-deploy"
REPO_URL=$(echo "$GITHUB_REPO" | sed "s|https://|https://x-access-token:${GITHUB_TOKEN}@|")

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
  echo "No changes — already up to date."
else
  git commit -m "Update $SITE_NAME: $(date -u '+%Y-%m-%d %H:%M UTC')"
  git push origin main
  echo ""
  echo "================================================================"
  echo "✓ Deployment Complete"
  echo "================================================================"
  echo "Dashboard URL: https://michaeldowd2.github.io/nanopages/$SITE_NAME/"
fi
```

**Usage:**
```bash
./scripts/deploy-dashboard.sh
```

**Note:** The Python script (`deploy-dashboard.py`) is recommended as it includes data clearing and re-export steps.

---

## Troubleshooting

### Issue: Clone fails
**Symptom:** `fatal: could not read Username`

**Solution:** Check GITHUB_TOKEN is set:
```bash
echo ${GITHUB_TOKEN:0:20}...  # Should show token prefix
```

### Issue: Push rejected
**Symptom:** `! [rejected] main -> main (fetch first)`

**Solution:** Pull latest changes first:
```bash
cd /tmp/nanopages-deploy
git pull origin main
# Then retry deploy
```

### Issue: Changes not visible
**Symptom:** Dashboard shows old data

**Solutions:**
1. **Wait 2-3 minutes** - GitHub Pages takes time to rebuild
2. **Hard refresh browser** - Ctrl+Shift+R (or Cmd+Shift+R)
3. **Check commit** - Verify files were updated in GitHub repo
4. **Check GitHub Actions** - Look for Pages build/deploy in repo Actions tab

---

## File Updates

When adding new data to dashboard, update these files:

### Data Files (auto-generated)
- `step1_exchange_rates.csv` - Exchange rates (all pairs)
- `step1_exchange_rates_matrix.json` - Matrix format for visualization
- `step2_indices.csv` - Currency indices
- `step3_news.csv` - News articles
- `step4_horizons.csv` - Time horizons
- `step5_signals.csv` - Sentiment signals
- `step6_realization.csv` - Signal realization
- `step7_strategies.csv` - Strategy results
- `step7_strategies_detail.json` - Detailed strategy data
- `tracking_dates.json` - Available log dates
- `tracking_YYYY-MM-DD.json` - Daily logs

### Dashboard HTML
- `index.html` - Main dashboard (only update for UI changes)

---

## GitHub Pages Configuration

**Repository:** michaeldowd2/nanopages

**Branch:** main

**Directory:** `/fx-dashboard`

**Settings:**
1. Go to repository Settings → Pages
2. Source: Deploy from a branch
3. Branch: main
4. Folder: / (root)
5. Custom domain: (none)

**Build time:** ~30-60 seconds after push

**Cache:** Browsers may cache for up to 10 minutes

---

## Clearing Data (Testing Empty State)

To test the dashboard with no data or start fresh:

```bash
# Clear all generated data (exports + logs + dashboard)
./scripts/clear-all-data.sh

# Then deploy empty dashboard
publish-github-pages fx-dashboard
```

This removes:
- All CSV exports (step1-step7)
- All validation/detail JSON files
- All log files
- All dashboard data files

But preserves:
- Config files (`config/*.json`)
- `system_config.json` (dashboard modules/parameters)
- Source data (prices, news, signals, indices)

---

## Best Practices

1. **Always export before deploy**
   - Run all export scripts to ensure latest data
   - Check CSV row counts: `wc -l data/exports/*.csv`

2. **Test locally first** (optional)
   - Open `sites/fx-dashboard/index.html` in browser
   - Verify all tabs load correctly

3. **Commit messages**
   - Use descriptive messages: "Update dashboard: added logging system"
   - Include timestamp: `$(date -u '+%Y-%m-%d %H:%M UTC')`

4. **Verify after deploy**
   - Wait 2-3 minutes for GitHub Pages rebuild
   - Check dashboard URL
   - Test all tabs

5. **Monitor repo size**
   - Dashboard assets should be < 10 MB
   - Large files (> 1 MB) should be optimized
   - Git history grows with each deploy

---

## Summary

**Deployment workflow:**
1. Export data: `python3 scripts/export-*.py`
2. Copy to dashboard: `cp data/exports/* sites/fx-dashboard/data/`
3. Deploy: `./scripts/deploy-dashboard.sh`
4. Verify: Visit https://michaeldowd2.github.io/nanopages/fx-dashboard/

**Key points:**
- Uses GitHub Pages (not Surge)
- Git-based deployment
- Automatic via script
- 30-60 second build time
- Hard refresh browser if changes not visible
