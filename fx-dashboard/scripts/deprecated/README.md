# Deprecated Scripts

This folder contains scripts that have been replaced as part of the pipeline refactoring.

## Deprecated Scripts

### extract-executed-trades.py (OLD Process 8.1)
**Replaced by:** `scripts/pipeline/execute-trades.py` (Process 9)
**Deprecated:** 2026-03-22
**Reason:** Duplicate trade execution logic. Process 9 now handles trade amount calculations directly.

### execute-strategies.py (OLD Process 9)
**Replaced by:** `scripts/pipeline/calculate-account-balances.py` (Process 10)
**Deprecated:** 2026-03-22
**Reason:** Refactored to separate trade execution (P9) from balance updates (P10).

### calculate-portfolio-valuations.py (OLD Process 10)
**Replaced by:** `scripts/pipeline/calculate-portfolio-performance.py` (Process 11)
**Deprecated:** 2026-03-22
**Reason:** Renumbered to Process 11 after insertion of new processes.

## Migration Notes

See `/workspace/group/fx-portfolio/docs/PROCESS_REFACTORING.md` for full details on the refactoring.

**Key Changes:**
- Process 8.1 → Process 9 (Execute Trades)
- Old Process 9 → Process 10 (Account Balances)
- Old Process 10 → Process 11 (Portfolio Performance)

These scripts are kept for reference but should not be used. They may be deleted in a future cleanup.
