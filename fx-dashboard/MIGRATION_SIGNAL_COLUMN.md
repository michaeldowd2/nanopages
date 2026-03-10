# Migration: Signal Column Added to Process 5

**Date:** 2026-03-10

## What Changed

The `signal` column (magnitude-weighted confidence) has been moved from Process 6 to Process 5, where it logically belongs.

### Before
- **Process 5**: Output `confidence` and `predicted_magnitude`
- **Process 6**: Calculate `signal = confidence × magnitude_weight`

### After
- **Process 5**: Output `confidence`, `predicted_magnitude`, AND `signal`
- **Process 6**: Simply load `signal` from Process 5 data

## Migration Approach

Instead of re-running expensive LLM calls in Process 5, a one-time migration script added the `signal` column to all existing signal files:

```bash
python3 scripts/utilities/migrate-add-signal-column.py
```

**Results:**
- 15 files migrated
- 1,356 rows updated
- No LLM costs incurred

## Signal Calculation

```python
magnitude_multipliers = {
    'small': 0.4,
    'medium': 0.7,
    'large': 1.4
}
magnitude_weight = magnitude_multipliers.get(predicted_magnitude, 0.7)
signal = confidence × magnitude_weight
```

## Files Modified

1. **Process 5** (`generate-sentiment-signals.py`):
   - Added signal calculation to output

2. **Process 6** (`check-signal-realization.py`):
   - Removed signal calculation logic
   - Now loads signal from Process 5

3. **Schema** (`pipeline_steps.json`):
   - Added `signal` column to `process_5_signals` schema

4. **Migration** (`migrate-add-signal-column.py`):
   - One-time script to backfill signal column

## Testing

Tested Process 6 on 2026-03-10 - ✓ Works correctly with no downstream changes needed.

## Impact

- **Process 5**: Future runs will include signal calculation
- **Process 6**: Simplified - no longer calculates signal
- **Processes 7, 8, 9**: No changes needed (they use Process 6/7 outputs)
- **Cost**: Migration avoided re-running ~1,356 LLM calls across 15 dates

