# Skill: step9-export-and-publish

Export pipeline data to CSVs and publish dashboard.

## Purpose

Generate CSV exports for debugging and update the static dashboard website.

## Running This Step

### Part 1: Export CSVs

```bash
cd /workspace/group/fx-portfolio
python3 scripts/export-pipeline-data.py
```

This generates CSV files for each pipeline step:
- `data/exports/step1_eur_pairs.csv`
- `data/exports/step2_indices.csv`
- `data/exports/step3_news.csv`
- `data/exports/step4_horizons.csv`
- `data/exports/step5_signals.csv`
- `data/exports/step6_realization.csv`

### Part 2: Publish Dashboard

Use GitHub Pages deployment:

```bash
SITE_NAME="fx-dashboard"
SOURCE="/workspace/group/sites/$SITE_NAME"
DEPLOY_DIR="/tmp/nanopages-deploy"
REPO_URL=$(echo "$GITHUB_REPO" | sed "s|https://|https://x-access-token:${GITHUB_TOKEN}@|").git
GITHUB_USER=$(echo "$GITHUB_REPO" | awk -F'/' '{print $4}')
GITHUB_REPO_NAME=$(echo "$GITHUB_REPO" | awk -F'/' '{print $5}')
PAGES_URL="https://${GITHUB_USER}.github.io/${GITHUB_REPO_NAME}/${SITE_NAME}/"

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
fi
echo "Dashboard URL: $PAGES_URL"
```

Dashboard URL: https://michaeldowd2.github.io/nanopages/fx-dashboard/

## Output

**CSV files** for debugging each step's data

**Static website** showing:
- Architecture (9-step pipeline diagram)
- Pipeline status per step
- Data tabs for each step (Steps 1-6)
- Signals and realization status

## Dependencies

- All previous steps (1-7) should be run first
- GitHub token set in `GITHUB_TOKEN` environment variable
- GitHub repository set in `GITHUB_REPO` environment variable

## Debugging

Check CSV file sizes:
```bash
wc -l data/exports/*.csv
```

Test git deployment:
```bash
git clone "$REPO_URL" /tmp/test-deploy
```

## Notes

- CSVs regenerated each run (overwrite previous)
- Dashboard published to same URL (overwrites previous)
- Can run this step independently for debugging
- CSV exports useful for Excel analysis or custom visualizations
