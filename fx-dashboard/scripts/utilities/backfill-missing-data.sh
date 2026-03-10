#!/bin/bash
# Backfill Missing Data - Safe Historic Reruns
#
# This script backfills missing data for processes 2-9 by running them
# for historic dates where source data (P1 and P3) already exists.
#
# SAFE: Only runs processes that read from existing data (P2, P4-9)
# NEVER runs processes that fetch live data (P1, P3) - these are protected by guardrails

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$BASE_DIR"

echo "============================================================"
echo "FX Portfolio Pipeline - Backfill Missing Data"
echo "============================================================"
echo ""
echo "This script will backfill missing data for processes 2-9."
echo "Source data (P1 and P3) must exist for each date."
echo ""

# Define missing dates for each process based on analysis
# P2 missing: 2026-02-25 through 2026-03-06
DATES_P2="2026-02-25 2026-02-26 2026-02-27 2026-02-28 2026-03-01 2026-03-02 2026-03-03 2026-03-04 2026-03-05 2026-03-06"

# P5 missing: 2026-03-09
DATES_P5="2026-03-09"

# P6-P9 missing: All dates except 2026-03-10
DATES_P6_TO_P9="2026-02-24 2026-02-25 2026-02-26 2026-02-27 2026-02-28 2026-03-01 2026-03-02 2026-03-03 2026-03-04 2026-03-05 2026-03-06 2026-03-07 2026-03-08 2026-03-09"

echo "Summary of backfill needed:"
echo "  - Process 2 (Indices): 10 missing dates"
echo "  - Process 5 (Signals): 1 missing date"
echo "  - Process 6 (Realization): 14 missing dates"
echo "  - Process 7 (Aggregation): 14 missing dates"
echo "  - Process 8 (Trades): 14 missing dates"
echo "  - Process 9 (Portfolios): 14 missing dates"
echo ""
echo "Total: 67 process runs needed"
echo ""

# Confirmation
read -p "Do you want to proceed with backfill? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Backfill cancelled."
    exit 0
fi

echo ""
echo "============================================================"
echo "Starting backfill process..."
echo "============================================================"
echo ""

# Track success/failure
TOTAL_RUNS=0
SUCCESS_RUNS=0
FAILED_RUNS=0

# Function to run process and track results
run_process() {
    local date=$1
    local process_id=$2
    local process_name=$3

    TOTAL_RUNS=$((TOTAL_RUNS + 1))

    echo "[$(date +%H:%M:%S)] Running Process $process_id ($process_name) for $date..."

    if python3 scripts/utilities/run-system.py --date "$date" --process-ids "$process_id" > /dev/null 2>&1; then
        SUCCESS_RUNS=$((SUCCESS_RUNS + 1))
        echo "  ✓ Success"
    else
        FAILED_RUNS=$((FAILED_RUNS + 1))
        echo "  ✗ Failed"
        # Don't exit - continue with other dates
    fi
}

# Phase 1: Backfill Process 2 (Currency Indices)
# This must run before P6 since P6 depends on P2
echo ""
echo "=== Phase 1: Backfilling Process 2 (Currency Indices) ==="
echo ""
for date in $DATES_P2; do
    run_process "$date" "2" "Currency Indices"
done

# Phase 2: Backfill Process 5 (Sentiment Signals)
# This must run before P6 since P6 depends on P5
echo ""
echo "=== Phase 2: Backfilling Process 5 (Sentiment Signals) ==="
echo ""
for date in $DATES_P5; do
    run_process "$date" "5" "Sentiment Signals"
done

# Phase 3: Backfill Processes 6-9 (Signal Realization through Portfolio Execution)
# These must run in order due to dependencies
echo ""
echo "=== Phase 3: Backfilling Processes 6-9 (Sequential) ==="
echo ""

for date in $DATES_P6_TO_P9; do
    echo ""
    echo "--- Processing date: $date ---"

    # P6 depends on P2, P4, P5
    run_process "$date" "6" "Signal Realization"

    # P7 depends on P6
    run_process "$date" "7" "Signal Aggregation"

    # P8 depends on P7
    run_process "$date" "8" "Trade Calculation"

    # P9 depends on P1, P8
    run_process "$date" "9" "Portfolio Execution"
done

# Summary
echo ""
echo "============================================================"
echo "Backfill Complete"
echo "============================================================"
echo ""
echo "Results:"
echo "  Total runs: $TOTAL_RUNS"
echo "  Successful: $SUCCESS_RUNS"
echo "  Failed: $FAILED_RUNS"
echo ""

if [ $FAILED_RUNS -gt 0 ]; then
    echo "⚠️  Some processes failed. Check logs for details."
    exit 1
else
    echo "✓ All processes completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Verify data: ls -lh data/indices/ data/signals/ data/portfolios/"
    echo "  2. Export for dashboard: python3 scripts/deployment/export-pipeline-data.py"
    echo "  3. Deploy: Follow deployment instructions in docs/DEPLOYMENT.md"
fi
