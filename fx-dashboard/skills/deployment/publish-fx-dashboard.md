# Skill: publish-fx-dashboard

Publish the FX Portfolio Dashboard to GitHub Pages, including the dashboard site, scripts, skills, docs, and config.

## Purpose

Deploys the entire FX Portfolio project (excluding raw data/) to the nanopages GitHub repo under the `fx-dashboard/` subfolder. This includes:
- Dashboard HTML (`index.html`)
- Site data CSV files (`site_data/`)
- Python scripts (`scripts/`)
- Automation skills (`skills/`)
- Documentation (`docs/`)
- Configuration (`config/`)

## Structure

**Local:** `/workspace/group/fx-portfolio/`
```
fx-portfolio/
├── config/         → GitHub
├── scripts/        → GitHub
├── skills/         → GitHub
├── docs/           → GitHub
├── site_data/      → GitHub
├── index.html      → GitHub
└── data/           → Excluded (raw pipeline data)
```

**GitHub:** `michaeldowd2/nanopages/fx-dashboard/`

**Public URL:** `https://michaeldowd2.github.io/nanopages/fx-dashboard/`

## Usage

```bash
cd /workspace/group/fx-portfolio
bash ../skills/publish-fx-dashboard.md
```

Or invoke directly from skills folder.

## Deploy Script

```bash
#!/bin/bash

SOURCE="/workspace/group/fx-portfolio"
DEPLOY_DIR="/tmp/nanopages-deploy"
SITE_NAME="fx-dashboard"

# Derive authenticated clone URL from GITHUB_REPO env var
REPO_URL=$(echo "$GITHUB_REPO" | sed "s|https://|https://x-access-token:${GITHUB_TOKEN}@|").git

# Extract user and repo name for the public URL
GITHUB_USER=$(echo "$GITHUB_REPO" | awk -F'/' '{print $4}')
GITHUB_REPO_NAME=$(echo "$GITHUB_REPO" | awk -F'/' '{print $5}')
PAGES_URL="https://${GITHUB_USER}.github.io/${GITHUB_REPO_NAME}/${SITE_NAME}/"

echo "📦 Deploying FX Portfolio Dashboard"
echo "═══════════════════════════════════════════════════════"
echo "Source: $SOURCE"
echo "Target: nanopages/$SITE_NAME/"
echo ""

# Clone fresh copy of the repo
echo "Cloning repository..."
rm -rf "$DEPLOY_DIR"
git clone "$REPO_URL" "$DEPLOY_DIR" 2>&1 | grep -v "Cloning"

# Configure git identity (container-local only)
cd "$DEPLOY_DIR"
git config user.name "nano"
git config user.email "nano@nanoclaw"

# Clear the subfolder
echo "Clearing existing $SITE_NAME/ folder..."
rm -rf "$DEPLOY_DIR/$SITE_NAME"
mkdir -p "$DEPLOY_DIR/$SITE_NAME"

# Copy project files, excluding data/ folder
echo "Copying project files (excluding data/)..."
cd "$SOURCE"
for item in config scripts skills docs site_data index.html; do
  if [ -e "$item" ]; then
    cp -r "$item" "$DEPLOY_DIR/$SITE_NAME/"
    echo "  ✓ Copied $item"
  fi
done

# Return to deploy directory
cd "$DEPLOY_DIR"

# Show what will be deployed
echo ""
echo "Files to deploy:"
find "$SITE_NAME" -maxdepth 2 -type f | head -20
echo "..."

# Commit and push only if there are changes
echo ""
echo "Committing changes..."
git add -A
if git diff --cached --quiet; then
  echo "No changes — already up to date."
  echo "URL: $PAGES_URL"
else
  git commit -m "Update FX Dashboard: $(date -u '+%Y-%m-%d %H:%M UTC')

Deployed from /workspace/group/fx-portfolio/
Includes: config, scripts, skills, docs, site_data, index.html

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

  git push origin main 2>&1 | grep -v "remote:"
  echo ""
  echo "✅ Published to $PAGES_URL"
fi

# Cleanup
cd /
rm -rf "$DEPLOY_DIR"
```

## Notes

- The `data/` folder (7.7MB of raw pipeline data) is intentionally excluded from GitHub
- `site_data/` contains exported CSV files for the dashboard (1.8MB) and IS included
- Clones fresh each time to avoid stale state issues
- GitHub Pages may take 1-2 minutes to reflect changes
- All project files (scripts, skills, docs, config) are now version controlled

## Dependencies

- `GITHUB_TOKEN` environment variable (fine-grained PAT)
- `GITHUB_REPO` environment variable (`https://github.com/michaeldowd2/nanopages`)
