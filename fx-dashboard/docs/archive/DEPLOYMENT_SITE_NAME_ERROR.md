# CRITICAL: Deployment Site Name Error - 2026-02-25

## Incident Summary

**What Happened**: Deployed to wrong site name (`fx-portfolio` instead of `fx-dashboard`), causing data to appear in wrong location.

**Impact**: User couldn't see time horizon analysis data because it was deployed to wrong URL.

**Root Cause**: Operator error - manually deployed with incorrect `SITE_NAME` variable.

---

## The Error

### What I Did Wrong (2026-02-25 19:54 UTC)

When manually redeploying, I used:

```bash
SITE_NAME="fx-portfolio"    # ❌ WRONG
SOURCE="/workspace/group/sites/fx-dashboard"
```

This created a deployment at:
- **Wrong URL**: `https://michaeldowd2.github.io/nanopages/fx-portfolio/`
- Had all the correct data (26KB step4_horizons.csv)
- But user was looking at the correct URL which had empty data

### What I Should Have Done

Used the existing deploy script:

```bash
./scripts/deploy-dashboard.sh    # ✅ CORRECT
```

Which has the correct configuration:

```bash
SITE_NAME="fx-dashboard"    # ✅ CORRECT
SOURCE="/workspace/group/sites/$SITE_NAME"
```

---

## Critical Rules

### 🚨 RULE #1: ALWAYS Use Deploy Script

**NEVER manually run git commands for deployment**

```bash
# ✅ CORRECT
./scripts/deploy-dashboard.sh

# ❌ WRONG - Manual deployment
SITE_NAME="..."
git clone ... && git commit ... && git push ...
```

### 🚨 RULE #2: Site Name is ALWAYS "fx-dashboard"

**The site name is `fx-dashboard`, NOT `fx-portfolio`**

- ✅ Correct site name: `fx-dashboard`
- ✅ Correct URL: `https://michaeldowd2.github.io/nanopages/fx-dashboard/`
- ✅ Correct local path: `/workspace/group/sites/fx-dashboard/`
- ✅ Correct deploy script variable: `SITE_NAME="fx-dashboard"`

**Why "fx-dashboard" and not "fx-portfolio"?**
- The project folder is named `fx-portfolio` (confusing!)
- But the dashboard site is named `fx-dashboard`
- This is historical and unchangeable

### 🚨 RULE #3: Verify Deploy Target Before Pushing

Before any manual deployment (which you shouldn't do anyway), verify:

```bash
echo "Site name: $SITE_NAME"
echo "Target URL: https://${GITHUB_USER}.github.io/${GITHUB_REPO_NAME}/${SITE_NAME}/"
```

Expected output:
```
Site name: fx-dashboard
Target URL: https://michaeldowd2.github.io/nanopages/fx-dashboard/
```

If it says anything else, STOP and fix it!

---

## How This Happened

### Timeline of Errors

**19:41 UTC** - User requested dashboard redeployment
- Should have used: `./scripts/deploy-dashboard.sh`
- Instead: Wrote manual git commands

**19:54 UTC** - Manual deployment executed
- Used `SITE_NAME="fx-portfolio"` (wrong!)
- Created incorrect folder in repo
- Data deployed to wrong URL

**19:56 UTC** - User noticed data not showing
- Checked correct URL: `/fx-dashboard/` (empty)
- Data was at wrong URL: `/fx-portfolio/` (full)

**20:05 UTC** - Correct deployment
- Used `./scripts/deploy-dashboard.sh`
- Deployed to correct location
- Data now visible

**20:07 UTC** - Cleanup
- Removed incorrect `fx-portfolio` folder from repo
- Documented the error

---

## Why This Was Confusing

### The Name Mismatch

**Project folder**: `fx-portfolio`
```
/workspace/group/fx-portfolio/
├── scripts/
├── data/
└── sites/
    └── fx-dashboard/    ← Dashboard site folder
```

**Dashboard site**: `fx-dashboard`
```
https://github.com/michaeldowd2/nanopages
└── fx-dashboard/        ← Deployed site
    ├── index.html
    └── data/
```

The project is called "fx-portfolio" but the dashboard site is called "fx-dashboard"!

This mismatch led to the error when I used the project name instead of the site name.

---

## How to Prevent This

### 1. Always Use the Deploy Script

The deploy script has the correct site name hardcoded:

```bash
# From deploy-dashboard.sh line 25
SITE_NAME="fx-dashboard"
```

By using the script, you can't get this wrong.

### 2. Add Validation to Manual Deployments

If you MUST deploy manually (you shouldn't!), add validation:

```bash
SITE_NAME="fx-dashboard"

# Validate
if [ "$SITE_NAME" != "fx-dashboard" ]; then
  echo "❌ ERROR: Site name must be 'fx-dashboard', not '$SITE_NAME'"
  exit 1
fi

# Continue with deployment...
```

### 3. Document the Site Name Everywhere

Added to multiple places:
- This document
- DEPLOYMENT_BEST_PRACTICES.md
- deploy-dashboard.sh (comment at top)
- README.md (verified correct URL)

### 4. Add Deploy Script Comment

Updated `deploy-dashboard.sh` to have a warning comment at the top.

---

## Verification Checklist

Before any deployment, verify:

- [ ] Using `./scripts/deploy-dashboard.sh` (not manual commands)
- [ ] Site name is `fx-dashboard` (not `fx-portfolio`)
- [ ] Target URL is `https://michaeldowd2.github.io/nanopages/fx-dashboard/`
- [ ] Source folder is `/workspace/group/sites/fx-dashboard/`
- [ ] Data files are in `/workspace/group/sites/fx-dashboard/data/`

After deployment, verify:

- [ ] Check GitHub repo has `fx-dashboard` folder (not `fx-portfolio`)
- [ ] Check `fx-dashboard/data/step4_horizons.csv` has data (not 0 bytes)
- [ ] Wait 1-2 minutes for GitHub Pages
- [ ] Load `https://michaeldowd2.github.io/nanopages/fx-dashboard/`
- [ ] Hard refresh browser (Ctrl+Shift+R)
- [ ] Verify Step 4 tab shows data

---

## What Was Fixed

### Immediate Fixes

1. ✅ Deployed to correct location (`fx-dashboard`)
2. ✅ Removed incorrect deployment (`fx-portfolio`)
3. ✅ Verified data is now visible

### Documentation Fixes

1. ✅ Created this incident document
2. ✅ Updated DEPLOYMENT_BEST_PRACTICES.md
3. ✅ Updated PIPELINE_ORCHESTRATION_FIX.md
4. ✅ Added comment to deploy-dashboard.sh

### Process Fixes

1. ✅ Emphasized "always use deploy script"
2. ✅ Documented site name rules
3. ✅ Created verification checklist

---

## Key Takeaways

### For Future Deployments

1. **ALWAYS use `./scripts/deploy-dashboard.sh`**
   - Never bypass it with manual commands
   - It has the correct site name
   - It handles export + copy + deploy

2. **Site name is `fx-dashboard`, not `fx-portfolio`**
   - This is confusing because the project folder is `fx-portfolio`
   - But the dashboard site has always been `fx-dashboard`
   - This cannot be changed (historical)

3. **Verify before pushing**
   - Check the site name
   - Check the target URL
   - Check the deployed folder name

### Lessons Learned

1. **Don't assume project name = site name**
   - They can be different
   - Always check the deploy script

2. **Manual deployments are error-prone**
   - Easy to use wrong variable
   - Easy to deploy to wrong location
   - Always use automation

3. **Verify the result**
   - Don't assume it worked
   - Check the repo after deployment
   - Check the live URL after deployment

---

## Status: RESOLVED ✅

**Date**: 2026-02-25
**Resolution**: Correct deployment completed, incorrect deployment removed
**Verified**: Data now visible at https://michaeldowd2.github.io/nanopages/fx-dashboard/

**Future Prevention**: Always use `./scripts/deploy-dashboard.sh`

---

## Quick Reference

### Correct Configuration

```bash
Project folder:      /workspace/group/fx-portfolio/
Dashboard site:      /workspace/group/sites/fx-dashboard/
Site name:           fx-dashboard
Deploy script:       ./scripts/deploy-dashboard.sh
GitHub folder:       nanopages/fx-dashboard/
Public URL:          https://michaeldowd2.github.io/nanopages/fx-dashboard/
```

### Deploy Command

```bash
cd /workspace/group/fx-portfolio
./scripts/deploy-dashboard.sh
```

**Never use anything else!**
