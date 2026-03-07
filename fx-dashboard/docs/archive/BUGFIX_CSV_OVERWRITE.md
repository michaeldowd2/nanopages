# Critical Bug Fix: CSV Date Safety

**Date**: 2026-02-26
**Severity**: CRITICAL - Data loss bug
**Status**: FIXED

## The Bug

### What Happened
When running Steps 7 or 8 without the `--date` parameter, the scripts would **overwrite the entire CSV file**, deleting all historical data for other dates.

### Root Cause

The append logic had a fatal flaw:

```python
# OLD BROKEN CODE
if file_exists and date_str:  # ← date_str could be None here!
    # Read existing dates
    existing_dates = set(row['date'] for row in reader)
    should_append = bool(existing_dates and date_str not in existing_dates)

if should_append:
    # Append mode
    writer.writerows(all_trades)
else:
    # OVERWRITES ENTIRE FILE! ←  BUG: This runs when date_str is None
    with open(csv_file, 'w', newline='') as f:
        writer.writeheader()
        writer.writerows(all_trades)
```

**The problem:**
- When `date_str` is None (even temporarily), the condition `if file_exists and date_str:` evaluates to False
- This causes `should_append` to stay False
- The code falls through to the `else` block which opens the file in **write mode** (`'w'`)
- Write mode **truncates the file**, deleting all existing data
- Only the current run's data gets written

### Impact
- Running `./run-pipeline.sh` (without --date) would delete all historical trading data
- Data from previous dates would be **permanently lost**
- This affected Steps 7 (trades) and 8 (portfolios)

## The Fix

### New Safe Approach

Both `calculate-trades.py` and `execute-strategies.py` now use a safer pattern:

```python
# NEW SAFE CODE

# 1. Safety check - fail fast if date_str is missing
if not date_str:
    logger.error("CRITICAL: date_str is None when writing CSV!")
    raise ValueError("date_str must be set before writing CSV")

# 2. Read existing file if it exists
if file_exists:
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        existing_rows = list(reader)

    # 3. Filter: keep all OTHER dates, discard current date
    other_date_rows = [row for row in existing_rows
                       if row.get('date') != date_str]

    # 4. Write: other dates + new data for current date
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(other_date_rows)      # ← Preserve other dates
        writer.writerows(all_trades)            # ← Add/replace current date
else:
    # New file - just write current date
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_trades)
```

### Key Safety Features

1. **Explicit date_str check**: Fail immediately if date is missing
2. **Read-filter-write pattern**: Never blindly overwrite
3. **Preserve other dates**: Explicitly keep rows from different dates
4. **Replace current date**: Remove old data for current date before adding new
5. **No append mode**: Always read → filter → write (cleaner, safer)

## Why This is Safer

### Before (Broken)
```
File exists? Yes
date_str set? No (it gets set later, but check happens too early!)
→ should_append = False
→ Open file in 'w' mode
→ 💥 ALL DATA DELETED
```

### After (Fixed)
```
date_str set? No
→ 💥 CRASH with clear error message
→ Developer fixes the code
→ No data loss possible
```

OR if date_str is set:
```
date_str set? Yes (e.g., "2026-02-25")
File exists? Yes
→ Read all existing rows
→ Keep rows where date != "2026-02-25"
→ Write: kept rows + new 2026-02-25 rows
→ ✅ Other dates preserved, 2026-02-25 updated
```

## Testing

Verified the fix works correctly:

```bash
# Before fix - all three dates present
$ cut -d',' -f1 data/exports/step8_strategies.csv | sort -u
2026-02-24
2026-02-25
2026-02-26

# Rerun Step 8 for 2026-02-25 (this would have deleted 2024 and 2026 before!)
$ python3 scripts/execute-strategies.py --date 2026-02-25

# After fix - all three dates still present
$ cut -d',' -f1 data/exports/step8_strategies.csv | sort -u
2026-02-24  ← PRESERVED
2026-02-25  ← UPDATED
2026-02-26  ← PRESERVED
```

Each date has exactly 9 rows (9 strategies):
```bash
$ grep -c "^2026-02-24" data/exports/step8_strategies.csv
9
$ grep -c "^2026-02-25" data/exports/step8_strategies.csv
9
$ grep -c "^2026-02-26" data/exports/step8_strategies.csv
9
```

## Prevention

### Code Review Checklist
- [ ] Never use append mode (`'a'`) without reading the file first
- [ ] Always validate `date_str` is set before CSV operations
- [ ] Use read-filter-write pattern for multi-date files
- [ ] Test with existing multi-date data before deploying
- [ ] Fail fast with clear errors rather than silently corrupting data

### Best Practices
1. **Explicit over implicit**: Check date_str explicitly, don't assume it's set
2. **Read before write**: Always read existing data when file exists
3. **Filter before write**: Explicitly decide what to keep vs replace
4. **Test destructive operations**: Always test with valuable data present
5. **Use version control**: Git saved us here - data was recoverable

## Files Modified
- `scripts/calculate-trades.py` - Lines 383-405 rewritten
- `scripts/execute-strategies.py` - Lines 645-696 rewritten
- Both now use identical safe CSV writing pattern

## Related Issues
- Data loss occurred during pipeline run on 2026-02-26
- 2026-02-24 data was lost, had to be manually restored
- No permanent data loss due to Git version control
- Bug would have been catastrophic without backups

## Lessons Learned
1. **Data loss bugs are the worst** - they're silent and catastrophic
2. **Append mode is dangerous** - it seems safe but has edge cases
3. **Always validate inputs** - especially dates used for data segmentation
4. **Read-filter-write is safer** - more explicit about what's happening
5. **Test with real data** - unit tests wouldn't have caught this
6. **Version control is essential** - Git saved us from permanent loss
