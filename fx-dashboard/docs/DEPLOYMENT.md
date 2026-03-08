# FX Dashboard Deployment Guide

Complete guide for deploying the FX Portfolio Dashboard to GitHub Pages.

---

## Table of Contents

1. [Deployment Method](#deployment-method)
2. [Prerequisites](#prerequisites)
3. [Quick Deployment](#quick-deployment)
4. [What Gets Deployed](#what-gets-deployed)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Deployment Method

⚠️ **ONLY DEPLOYMENT METHOD: GitHub Pages via Git Push**

The FX dashboard is deployed **EXCLUSIVELY** to GitHub Pages.

- ✅ **GitHub Pages** (via git push to nanopages repo)
- ❌ **NOT Surge** (deprecated and removed)
- ❌ **NOT Vercel, Netlify, or other services**

**Dashboard URL:** https://michaeldowd2.github.io/nanopages/fx-dashboard/

**GitHub Repo:** https://github.com/michaeldowd2/nanopages

---

## Prerequisites

### Required Environment Variables

Set these in `/workspace/project/.env`:

```bash
GITHUB_TOKEN=github_pat_xxxxx       # GitHub personal access token
GITHUB_REPO=https://github.com/michaeldowd2/nanopages
```

### GitHub Token Setup

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (fine-grained)
3. Repository access: `michaeldowd2/nanopages`
4. Permissions: **Contents** (read and write)
5. Copy token and add to `.env` file

---

## Quick Deployment

### Step 1: Export Latest Data

```bash
cd /workspace/group/fx-portfolio
python3 scripts/export-pipeline-data.py
```

This exports all pipeline data to `site_data/`.

### Step 2: Deploy to GitHub Pages

Use the deployment skill or run manually:

```bash
SOURCE="/workspace/group/fx-portfolio"
DEPLOY_DIR="/tmp/nanopages-deploy"
SITE_NAME="fx-dashboard"

REPO_URL=$(echo "$GITHUB_REPO" | sed "s|https://|https://x-access-token:${GITHUB_TOKEN}@|").git
GITHUB_USER=$(echo "$GITHUB_REPO" | awk -F'/' '{print $4}')
GITHUB_REPO_NAME=$(echo "$GITHUB_REPO" | awk -F'/' '{print $5}')

# Clone repo
rm -rf "$DEPLOY_DIR"
git clone "$REPO_URL" "$DEPLOY_DIR"
cd "$DEPLOY_DIR"
git config user.name "nano"
git config user.email "nano@nanoclaw"

# Copy project files (excluding data/ folder)
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
git commit -m "Update FX Dashboard: $(date -u '+%Y-%m-%d %H:%M UTC')"
git push origin main
```

### Step 3: Verify Deployment

Visit: https://michaeldowd2.github.io/nanopages/fx-dashboard/

GitHub Pages may take 1-2 minutes to rebuild.

---

## What Gets Deployed

### Included in GitHub:

```
fx-dashboard/
├── config/          # System configuration
├── scripts/         # All Python pipeline scripts
├── skills/          # Automation skill files
├── docs/            # Documentation
├── site_data/       # Exported CSV files (1.8MB)
└── index.html       # Dashboard HTML (79KB)
```

### Excluded from GitHub:

```
data/                # Raw pipeline data (7.7MB) - local only
```

**Why separate?**
- `data/` contains raw working data (logs, portfolios, news articles)
- `site_data/` contains clean, dashboard-ready CSV exports
- Keeps repo size manageable
- Separates system data from presentation data

---

## Best Practices

### Before Deployment

1. ✅ **Run all pipeline steps** for latest dates
2. ✅ **Export data** with `export-pipeline-data.py`
3. ✅ **Verify site_data/** has latest CSVs
4. ✅ **Test locally** if possible (open index.html)

### Security

1. ✅ **Never commit API keys** to docs or code
2. ✅ **Use environment variables** for all secrets
3. ✅ **Redact keys** from example code (use `<your-key-here>`)
4. ✅ **Review docs** before deploying

### Commit Messages

Good commit message format:

```
Update FX Dashboard: Brief description

- Specific change 1
- Specific change 2
- Updated data for dates X-Y

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Deployment Frequency

- **Daily**: If pipeline runs daily
- **After changes**: When modifying scripts, dashboard, or config
- **After data updates**: When exporting new pipeline results

---

## Troubleshooting

### Issue: "Authentication failed"

**Cause:** GitHub token missing or invalid

**Solution:**
```bash
# Check token exists
echo $GITHUB_TOKEN

# Verify token has correct permissions
# Go to GitHub → Settings → Developer settings → Tokens
# Ensure token has "Contents: Read and write" permission
```

### Issue: "No changes to commit"

**Cause:** No files changed since last deployment

**Solution:** This is normal. Deploy only when you have actual changes.

### Issue: "Dashboard shows old data"

**Cause:** Forgot to export before deploying

**Solution:**
```bash
# 1. Export latest data
python3 scripts/export-pipeline-data.py

# 2. Deploy again
# (re-run deployment script)
```

### Issue: "GitHub Pages not updating"

**Cause:** GitHub Pages build delay

**Solution:**
- Wait 1-2 minutes after push
- Check GitHub Actions tab for build status
- Hard refresh browser (Ctrl+Shift+R)

### Issue: "Missing CSV files on dashboard"

**Cause:** site_data/ not exported or not copied

**Solution:**
```bash
# Verify site_data/ has all files
ls -lh site_data/

# Should see: step1-9 CSV files, JSON configs
```

---

## Repository Structure

The `nanopages` repository is organized as subfolders:

```
nanopages/
├── fx-dashboard/          # Your FX Portfolio Dashboard
├── other-project/         # Other potential projects
└── index.html (optional)  # Root directory listing
```

Each subfolder is a separate "site" served at:
- `https://username.github.io/nanopages/folder-name/`

**Benefits:**
- Multiple projects in one repo
- Simple deployment (just push to subfolder)
- No need to create new repos for each project

---

## Deployment Skill

For convenience, use the deployment skill:

**Location:** `skills/publish-fx-dashboard.md`

**Usage:**
```bash
# From anywhere in the project
cd /workspace/group/fx-portfolio
# Run the skill commands from publish-fx-dashboard.md
```

The skill automates the deployment process.

---

## Summary

**To deploy:**
1. Export data: `python3 scripts/export-pipeline-data.py`
2. Run deployment script (manual or via skill)
3. Wait 1-2 minutes for GitHub Pages
4. Verify at dashboard URL

**Key points:**
- Only use GitHub Pages (no other hosting)
- Export before deploying
- Exclude `data/` folder (too large)
- Include `site_data/` (dashboard needs it)
- Check for secrets before deploying

**Dashboard URL:** https://michaeldowd2.github.io/nanopages/fx-dashboard/
