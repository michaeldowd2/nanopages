# Skill: export-pipeline-data

Export pipeline data to CSVs and publish dashboard.

## Purpose

Generate CSV exports for the dashboard and publish the entire project (scripts, skills, docs, config, site_data, and dashboard HTML) to GitHub Pages.

---

## Quick Start

### Part 1: Export CSVs

```bash
cd /workspace/group/fx-portfolio
python3 scripts/deployment/export-pipeline-data.py
```

---

## Expected Output

### Output Files

All files generated in `site_data/` directory:

**Exchange Rates**:
- `site_data/step1_exchange_rates_matrix.csv` (~10 KB)

**Currency Indices**:
- `site_data/step2_indices.csv` (~20 KB)

**News Articles**:
- `site_data/step3_news.csv` (~100 KB)

**Time Horizons**:
- `site_data/step4_horizons.csv` (~50 KB)
- `site_data/step4_1_currency_events.csv` (~30 KB)

**Sentiment Signals**:
- `site_data/step5_signals.csv` (~150 KB)

**Signal Realization**:
- `site_data/step6_realization.csv` (~150 KB)

**Aggregated Signals**:
- `site_data/step7_aggregated_signals.csv` (~5 KB)

**Trades**:
- `site_data/step8_trades.csv` (~10 KB)

**Strategies**:
- `site_data/step9_strategies.csv` (~20 KB)

**Configuration**:
- `site_data/system_config.json` (~5 KB)
- `site_data/pipeline_steps.json` (~2 KB)

**Total Size**: ~552 KB (compressed to ~100 KB for GitHub)

### Interpretation

- All CSV files are dashboard-ready formats
- Files are regenerated completely on each run (no appending)
- Data spans the entire pipeline history (30 days rolling window for most data)
- **Use this data to**: Power the FX Dashboard visualizations and analysis

---

### Generated CSV files in `site_data/`:
- `site_data/step1_exchange_rates_matrix.csv`
- `site_data/step2_indices.csv`
- `site_data/step3_news.csv`
- `site_data/step4_horizons.csv`
- `site_data/step4_1_currency_events.csv`
- `site_data/step5_signals.csv`
- `site_data/step6_realization.csv`
- `site_data/step7_aggregated_signals.csv`
- `site_data/step8_trades.csv`
- `site_data/step9_strategies.csv`
- `site_data/system_config.json`
- `site_data/pipeline_steps.json`

### Part 2: Publish Dashboard

Deploy the entire fx-portfolio project to GitHub Pages:

```bash
SOURCE="/workspace/group/fx-portfolio"
DEPLOY_DIR="/tmp/nanopages-deploy"
SITE_NAME="fx-dashboard"

REPO_URL=$(echo "$GITHUB_REPO" | sed "s|https://|https://x-access-token:${GITHUB_TOKEN}@|").git
GITHUB_USER=$(echo "$GITHUB_REPO" | awk -F'/' '{print $4}')
GITHUB_REPO_NAME=$(echo "$GITHUB_REPO" | awk -F'/' '{print $5}')
PAGES_URL="https://${GITHUB_USER}.github.io/${GITHUB_REPO_NAME}/${SITE_NAME}/"

# Clone repo
rm -rf "$DEPLOY_DIR"
git clone "$REPO_URL" "$DEPLOY_DIR" 2>&1 | grep -v "Cloning"
cd "$DEPLOY_DIR"
git config user.name "nano"
git config user.email "nano@nanoclaw"

# Clear and copy project (exclude data/ folder)
rm -rf "$DEPLOY_DIR/$SITE_NAME"
mkdir -p "$DEPLOY_DIR/$SITE_NAME"
cd "$SOURCE"
for item in config scripts skills docs site_data index.html; do
  if [ -e "$item" ]; then
    cp -r "$item" "$DEPLOY_DIR/$SITE_NAME/"
  fi
done

# Commit and push
cd "$DEPLOY_DIR"
git add -A
if git diff --cached --quiet; then
  echo "No changes — already up to date."
else
  git commit -m "Update FX Dashboard: $(date -u '+%Y-%m-%d %H:%M UTC')

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
  git push origin main 2>&1 | grep -v "remote:"
fi
echo "Dashboard URL: $PAGES_URL"
```

Dashboard URL: https://michaeldowd2.github.io/nanopages/fx-dashboard/

## What Gets Deployed

**Included in GitHub:**
- `config/` - System configuration
- `scripts/` - All Python pipeline scripts
- `skills/` - Automation skill files
- `docs/` - Documentation
- `site_data/` - Exported CSV files for dashboard (1.8MB)
- `index.html` - Dashboard HTML

**Excluded from GitHub:**
- `data/` - Raw pipeline data (7.7MB) - local only

## Output

**CSV files** in `site_data/` for dashboard visualization

**GitHub Pages site** showing:
- Interactive dashboard with all pipeline data
- Full source code (scripts, skills)
- Complete documentation
- System configuration

## Dependencies

- All previous steps (1-9) should be run first
- GitHub token set in `GITHUB_TOKEN` environment variable
- GitHub repository set in `GITHUB_REPO` environment variable

## Debugging

Check CSV file sizes:
```bash
ls -lh site_data/*.csv
```

Check what will be deployed:
```bash
cd /workspace/group/fx-portfolio
find . -maxdepth 2 -type f | grep -v data/
```

## Notes

- CSVs regenerated each run (overwrite previous in site_data/)
- Dashboard and all project files published to GitHub
- `data/` folder is excluded from deployment (local working data only)
- Deployment includes full source code for transparency
- Use `../skills/publish-fx-dashboard.md` for detailed deployment docs
