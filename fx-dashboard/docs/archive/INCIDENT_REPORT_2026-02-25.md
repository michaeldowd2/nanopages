# Incident Report: Wrong Deployment Target (2026-02-25)

## Executive Summary

**Incident**: Dashboard data deployed to wrong GitHub Pages subfolder
**Impact**: Time horizon analysis data not visible to user
**Duration**: 13 minutes (19:54 - 20:07 UTC)
**Resolution**: Correct deployment completed, incorrect deployment removed
**Root Cause**: Operator error - used wrong site name in manual deployment

---

## What Happened

### Timeline

**19:41 UTC** - User requested dashboard redeployment
- Context: Time horizon analysis had just completed (38 articles analyzed)
- Expected: Use existing `deploy-dashboard.sh` script
- Actual: Attempted manual git deployment

**19:54 UTC** - Manual deployment with wrong site name
- Used `SITE_NAME="fx-portfolio"` instead of `SITE_NAME="fx-dashboard"`
- Created new subfolder in repo at `/fx-portfolio/`
- Data deployed successfully to wrong location
- Correct location `/fx-dashboard/` still had empty CSV (0 bytes)

**19:56 UTC** - User reported data not showing
- User checked correct URL: `https://michaeldowd2.github.io/nanopages/fx-dashboard/`
- Step 4 horizons CSV was empty (0 bytes)
- Actual data was at: `https://michaeldowd2.github.io/nanopages/fx-portfolio/`

**20:04 UTC** - Investigation revealed the error
- Found two folders in repo: `fx-dashboard` and `fx-portfolio`
- `fx-dashboard/data/step4_horizons.csv`: 0 bytes (empty)
- `fx-portfolio/data/step4_horizons.csv`: 26KB (full data)
- Root cause identified: wrong site name variable

**20:05 UTC** - Correct deployment using deploy script
- Ran `./scripts/deploy-dashboard.sh`
- Deployed to correct location with correct site name
- `fx-dashboard/data/step4_horizons.csv`: now 26KB

**20:07 UTC** - Cleanup and documentation
- Removed incorrect `fx-portfolio` folder from repo
- Created incident documentation
- Updated README and deploy script with warnings

---

## Root Cause Analysis

### Primary Cause: Operator Error

**What went wrong**: Used wrong site name variable in manual deployment

**Code that caused the issue**:
```bash
# Wrong
SITE_NAME="fx-portfolio"    # ❌ Incorrect - used project folder name

# Correct
SITE_NAME="fx-dashboard"    # ✅ Correct - actual dashboard site name
```

### Contributing Factors

1. **Confusing naming convention**
   - Project folder: `fx-portfolio`
   - Dashboard site: `fx-dashboard`
   - Natural mistake to use project name as site name

2. **Manual deployment instead of script**
   - Deploy script has correct site name hardcoded
   - By bypassing script, introduced opportunity for error

3. **No validation**
   - No check to verify site name before deploying
   - No warning about naming mismatch

---

## Impact Assessment

### User Impact

- **Severity**: Medium
- **Duration**: 13 minutes
- **Effect**: User couldn't see time horizon analysis data on dashboard
- **Workaround**: Data existed but at wrong URL (not discoverable by user)

### System Impact

- **Data integrity**: No impact - data was correct, just in wrong location
- **Service availability**: Dashboard remained accessible
- **Repository pollution**: Created unnecessary folder (cleaned up)

### Business Impact

- **User trust**: Minor - quick resolution, well documented
- **Development time**: ~15 minutes to investigate, fix, and document
- **Learning value**: High - identified critical naming issue

---

## Resolution

### Immediate Fixes (2026-02-25 20:05-20:07 UTC)

1. ✅ **Correct deployment**
   - Used `./scripts/deploy-dashboard.sh`
   - Deployed to correct `fx-dashboard` location
   - Verified data visible at correct URL

2. ✅ **Cleanup**
   - Removed incorrect `fx-portfolio` folder from repo
   - Removed all 15 files that were in wrong location

3. ✅ **Verification**
   - Checked GitHub repo structure
   - Verified file sizes (26KB for step4_horizons.csv)
   - Confirmed correct URL loads data

### Documentation Fixes (2026-02-25 20:07-20:10 UTC)

1. ✅ **Created incident documentation**
   - DEPLOYMENT_SITE_NAME_ERROR.md (detailed technical doc)
   - INCIDENT_REPORT_2026-02-25.md (this executive summary)

2. ✅ **Updated existing docs**
   - DEPLOYMENT_BEST_PRACTICES.md (emphasized site name)
   - PIPELINE_ORCHESTRATION_FIX.md (added operator error section)
   - README.md (added warning about site name)

3. ✅ **Updated deploy script**
   - Added header comment with critical warning
   - Documented site name mismatch
   - Referenced correct URL

### Process Improvements

1. ✅ **Deploy script is now required**
   - Never use manual git commands
   - Script has correct configuration
   - Documented in multiple places

2. ✅ **Site name documented everywhere**
   - README has warning
   - Deploy script has comment
   - Multiple docs reference it

3. ✅ **Verification checklist created**
   - Pre-deployment checks
   - Post-deployment verification
   - URL and folder name validation

---

## Lessons Learned

### What Went Well ✅

1. **Quick detection** - User noticed immediately (2 minutes)
2. **Good investigation** - Found root cause quickly
3. **Clean resolution** - Fixed correctly with script
4. **Thorough documentation** - Multiple docs created
5. **No data loss** - All data intact, just misplaced

### What Went Wrong ❌

1. **Bypassed existing script** - Should have used `deploy-dashboard.sh`
2. **Used wrong variable** - Confused project name with site name
3. **No validation** - Didn't verify target before deploying
4. **Manual commands** - Error-prone, should automate

### What We'll Do Differently ✅

1. **Always use deploy script** - Never bypass automation
2. **Add validation** - Check site name before deploying
3. **Document naming** - Make mismatch very clear
4. **Verify result** - Always check repo after deploying

---

## Prevention Measures

### Immediate (Completed)

- ✅ Updated README with warning
- ✅ Added comment to deploy script
- ✅ Created DEPLOYMENT_SITE_NAME_ERROR.md
- ✅ Updated DEPLOYMENT_BEST_PRACTICES.md
- ✅ Removed incorrect deployment

### Short-term (Recommended)

- [ ] Add validation to deploy script
  ```bash
  if [ "$SITE_NAME" != "fx-dashboard" ]; then
    echo "ERROR: Site name must be fx-dashboard"
    exit 1
  fi
  ```

- [ ] Add post-deploy verification
  ```bash
  # Check that correct folder has data
  if [ ! -s "$DEPLOY_DIR/$SITE_NAME/data/step4_horizons.csv" ]; then
    echo "WARNING: step4_horizons.csv is empty!"
  fi
  ```

- [ ] Create pre-commit hook to prevent incorrect deployments

### Long-term (Recommended)

- [ ] Consider renaming project folder to match site name
  - Rename `fx-portfolio` → `fx-dashboard` everywhere
  - Would eliminate naming confusion
  - Major refactor but worth considering

- [ ] Add CI/CD pipeline for deployments
  - Automatically deploy on push to main
  - Validate site name in CI
  - Run post-deploy tests

- [ ] Add monitoring to detect empty CSVs
  - Alert if step4_horizons.csv is 0 bytes
  - Alert if deployment target changes

---

## Verification

### Current State (2026-02-25 20:10 UTC)

```bash
✅ Correct folder in repo: fx-dashboard/
✅ Incorrect folder removed: fx-portfolio/ (deleted)
✅ Data file size: 26KB (38 articles)
✅ Dashboard URL: https://michaeldowd2.github.io/nanopages/fx-dashboard/
✅ Step 4 data visible: Yes
✅ Documentation complete: Yes
```

### Testing Performed

1. ✅ Cloned repo and verified structure
2. ✅ Checked CSV file sizes
3. ✅ Verified correct URL loads data
4. ✅ Confirmed incorrect folder removed
5. ✅ Tested deploy script works correctly

---

## Action Items

### Completed ✅

- [x] Deploy to correct location
- [x] Remove incorrect deployment
- [x] Document the incident
- [x] Update README with warning
- [x] Update deploy script with comment
- [x] Create incident report
- [x] Verify resolution

### Future Work 📋

- [ ] Add validation to deploy script
- [ ] Add post-deploy verification
- [ ] Consider renaming project folder
- [ ] Add CI/CD pipeline
- [ ] Add monitoring for empty CSVs

---

## Key Takeaways

### Critical Rules Established 🚨

1. **ALWAYS use `./scripts/deploy-dashboard.sh` for deployment**
   - Never use manual git commands
   - Script has correct configuration
   - Automation prevents errors

2. **Site name is `fx-dashboard`, NOT `fx-portfolio`**
   - Confusing because project folder is `fx-portfolio`
   - But dashboard site has always been `fx-dashboard`
   - This is documented everywhere now

3. **Verify before and after deployment**
   - Check site name before deploying
   - Check repo structure after deploying
   - Check live URL after deploying

### System Design Insights 💡

1. **Naming consistency matters**
   - Mismatch between project name and site name caused confusion
   - Consider aligning names in future

2. **Automation prevents errors**
   - Deploy script would have prevented this
   - Bypassing automation is risky

3. **Documentation is critical**
   - User couldn't find issue without investigation
   - Clear docs help prevent and diagnose issues

---

## References

- [DEPLOYMENT_SITE_NAME_ERROR.md](DEPLOYMENT_SITE_NAME_ERROR.md) - Detailed technical analysis
- [DEPLOYMENT_BEST_PRACTICES.md](DEPLOYMENT_BEST_PRACTICES.md) - Deployment guidelines
- [PIPELINE_ORCHESTRATION_FIX.md](PIPELINE_ORCHESTRATION_FIX.md) - Earlier orchestration issues

---

## Sign-off

**Incident**: Resolved ✅
**Date**: 2026-02-25
**Duration**: 13 minutes
**Impact**: Low (user inconvenience only)
**Learning**: High (identified critical naming issue)

**Status**: Dashboard now showing all 38 horizon analyses correctly at:
https://michaeldowd2.github.io/nanopages/fx-dashboard/
