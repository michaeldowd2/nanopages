#!/bin/bash
set -e

# ============================================================================
# FX Dashboard Deployment Script
# ============================================================================
# CRITICAL: Site name is "fx-dashboard" (NOT "fx-portfolio")
#
# The project folder is named "fx-portfolio" but the dashboard site is "fx-dashboard"
# This is historical and unchangeable. Always use this script for deployment.
#
# Correct URL: https://michaeldowd2.github.io/nanopages/fx-dashboard/
# ============================================================================

echo "================================================================"
echo "FX Dashboard Deployment"
echo "================================================================"

# 1. Export data
echo ""
echo "1. Exporting pipeline data..."
cd /workspace/group/fx-portfolio
python3 scripts/export-pipeline-data.py
python3 scripts/export-logs.py
python3 scripts/export-exchange-rates.py

# 2. Copy to dashboard
echo ""
echo "2. Copying to dashboard..."
# Clean old export files from dashboard (keep system_config.json)
echo "  • Cleaning old export files..."
find /workspace/group/sites/fx-dashboard/data/ -type f \( -name "step*.csv" -o -name "step*.json" \) -delete 2>/dev/null || true
# Copy fresh exports
cp data/exports/*.csv /workspace/group/sites/fx-dashboard/data/ 2>/dev/null || true
cp data/exports/*.json /workspace/group/sites/fx-dashboard/data/ 2>/dev/null || true
# Copy system config (source of truth)
cp config/system_config.json /workspace/group/sites/fx-dashboard/data/ 2>/dev/null || true
echo "  ✓ Copied system_config.json"

# 3. Deploy
echo ""
echo "3. Deploying to GitHub Pages..."
SITE_NAME="fx-dashboard"
SOURCE="/workspace/group/sites/$SITE_NAME"
DEPLOY_DIR="/tmp/nanopages-deploy"
REPO_URL=$(echo "$GITHUB_REPO" | sed "s|https://|https://x-access-token:${GITHUB_TOKEN}@|")
GITHUB_USER=$(echo "$GITHUB_REPO" | awk -F'/' '{print $4}')
GITHUB_REPO_NAME=$(echo "$GITHUB_REPO" | awk -F'/' '{print $5}')
PAGES_URL="https://${GITHUB_USER}.github.io/${GITHUB_REPO_NAME}/${SITE_NAME}/"

rm -rf "$DEPLOY_DIR"
git clone "$REPO_URL" "$DEPLOY_DIR" 2>&1 | grep -E "(Cloning|done)" || true
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
  git push origin main 2>&1 | grep -E "(Writing|main|->)" || true
  echo ""
  echo "================================================================"
  echo "✓ Deployment Complete"
  echo "================================================================"
  echo "Dashboard URL: $PAGES_URL"
  echo ""
  echo "Note: GitHub Pages may take 30-60 seconds to rebuild."
  echo "      Hard refresh your browser (Ctrl+Shift+R) to see changes."
fi
