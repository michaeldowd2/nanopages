#!/bin/bash
# Clear All Generated Data
# Removes pipeline output files while preserving configuration
# Usage: ./scripts/clear-all-data.sh [--exports-only|--latest|--all]

set -e

echo "================================================================"
echo "Clear Generated Data"
echo "================================================================"
echo ""
echo "This script can clear generated data in three modes:"
echo ""
echo "  --exports-only   Clear only exported site data (CSVs, JSONs)"
echo "  --latest         Clear exports + source data for latest date only"
echo "  --all            Clear all exports + all source data (complete reset)"
echo ""
echo "Always preserved:"
echo "  - Config files (config/*.json)"
echo "  - Scripts (scripts/*.py)"
echo "  - Documentation (docs/*.md)"
echo ""

MODE="${1}"

if [ -z "$MODE" ]; then
  echo "Error: Mode is required"
  echo "Usage: ./scripts/clear-all-data.sh [--exports-only|--latest|--all]"
  exit 1
fi

# Get today's date for latest mode
TODAY=$(date +%Y-%m-%d)

case "$MODE" in
  --exports-only)
    echo "Mode: Exports only (dashboard data + export CSVs/JSONs)"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "Cancelled."
      exit 0
    fi

    cd /workspace/group/fx-portfolio

    echo ""
    echo "1. Clearing CSV exports..."
    rm -f data/exports/*.csv
    echo "   ✓ Removed step CSVs"

    echo "2. Clearing generated JSON exports..."
    rm -f data/exports/step*_matrix.json
    rm -f data/exports/step*_validation.json
    rm -f data/exports/step*_detail.json
    rm -f data/exports/tracking_*.json
    echo "   ✓ Removed validation/detail/tracking JSON"

    echo "3. Clearing logs..."
    rm -f data/logs/*.json
    echo "   ✓ Removed log files"

    echo "4. Clearing dashboard data..."
    cd /workspace/group/sites/fx-dashboard/data
    find . -name "*.csv" -delete
    find . -name "*.json" ! -name "system_config.json" -delete
    echo "   ✓ Removed dashboard data (kept system_config.json)"

    echo ""
    echo "================================================================"
    echo "✓ Exports cleared"
    echo "================================================================"
    echo ""
    echo "Cleared:"
    echo "  • All step CSV exports"
    echo "  • All validation/detail JSON files"
    echo "  • All log files"
    echo "  • All dashboard data files"
    echo ""
    echo "Preserved:"
    echo "  • All source data (prices, news, signals, indices)"
    echo "  • Config files"
    echo ""
    ;;

  --latest)
    echo "Mode: Latest data (exports + source data for $TODAY)"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "Cancelled."
      exit 0
    fi

    cd /workspace/group/fx-portfolio

    echo ""
    echo "1. Clearing CSV exports..."
    rm -f data/exports/*.csv
    echo "   ✓ Removed step CSVs"

    echo "2. Clearing generated JSON exports..."
    rm -f data/exports/step*_matrix.json
    rm -f data/exports/step*_validation.json
    rm -f data/exports/step*_detail.json
    rm -f data/exports/tracking_*.json
    echo "   ✓ Removed validation/detail/tracking JSON"

    echo "3. Clearing logs for $TODAY..."
    rm -f data/logs/${TODAY}.json
    echo "   ✓ Removed log file for $TODAY"

    echo "4. Clearing source data for $TODAY..."

    # Clear today's price data
    rm -f data/prices/fx-rates-${TODAY}.json
    echo "   ✓ Removed prices for $TODAY"

    # Clear today's news articles
    for currency_dir in data/news/*/; do
      if [ -d "$currency_dir" ]; then
        rm -f "${currency_dir}${TODAY}.json"
      fi
    done
    echo "   ✓ Removed news articles for $TODAY"

    # Clear today's signals
    for currency_dir in data/signals/*/; do
      if [ -d "$currency_dir" ]; then
        rm -f "${currency_dir}${TODAY}.json"
      fi
    done
    echo "   ✓ Removed signals for $TODAY"

    # Update indices to remove today's data point
    for index_file in data/indices/*.json; do
      if [ -f "$index_file" ]; then
        # Use jq to filter out today's entries (if jq is available)
        if command -v jq &> /dev/null; then
          jq --arg date "$TODAY" 'del(.[$date])' "$index_file" > "${index_file}.tmp" && mv "${index_file}.tmp" "$index_file"
        else
          # If jq not available, just note it
          echo "   ⚠️  Cannot filter indices (jq not available), consider using --all mode"
        fi
      fi
    done
    echo "   ✓ Updated indices (removed $TODAY entries)"

    echo "5. Clearing dashboard data..."
    cd /workspace/group/sites/fx-dashboard/data
    find . -name "*.csv" -delete
    find . -name "*.json" ! -name "system_config.json" -delete
    echo "   ✓ Removed dashboard data (kept system_config.json)"

    echo ""
    echo "================================================================"
    echo "✓ Latest data cleared ($TODAY)"
    echo "================================================================"
    echo ""
    echo "Cleared:"
    echo "  • All exports"
    echo "  • Source data for $TODAY (prices, news, signals, indices)"
    echo "  • Log file for $TODAY"
    echo "  • All dashboard data"
    echo ""
    echo "Preserved:"
    echo "  • Historical source data (before $TODAY)"
    echo "  • Config files"
    echo ""
    ;;

  --all)
    echo "Mode: Complete reset (all exports + all source data)"
    echo ""
    echo "⚠️  WARNING: This will delete ALL historical data!"
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo "Cancelled."
      exit 0
    fi

    cd /workspace/group/fx-portfolio

    echo ""
    echo "1. Clearing CSV exports..."
    rm -f data/exports/*.csv
    echo "   ✓ Removed step CSVs"

    echo "2. Clearing generated JSON exports..."
    rm -f data/exports/step*_matrix.json
    rm -f data/exports/step*_validation.json
    rm -f data/exports/step*_detail.json
    rm -f data/exports/tracking_*.json
    echo "   ✓ Removed validation/detail/tracking JSON"

    echo "3. Clearing all logs..."
    rm -f data/logs/*.json
    echo "   ✓ Removed all log files"

    echo "4. Clearing all source data..."
    rm -f data/prices/*.json
    echo "   ✓ Removed all prices"

    rm -f data/news/url_index.json
    rm -rf data/news/*/
    echo "   ✓ Removed all news articles and URL index"

    rm -rf data/signals/*/
    echo "   ✓ Removed all signals"

    rm -f data/indices/*.json
    echo "   ✓ Removed all indices"

    rm -f data/article-analysis/*.json
    echo "   ✓ Removed all article analysis"

    echo "5. Clearing dashboard data..."
    cd /workspace/group/sites/fx-dashboard/data
    find . -name "*.csv" -delete
    find . -name "*.json" ! -name "system_config.json" -delete
    echo "   ✓ Removed dashboard data (kept system_config.json)"

    echo ""
    echo "================================================================"
    echo "✓ Complete reset performed"
    echo "================================================================"
    echo ""
    echo "Cleared:"
    echo "  • All exports (CSVs, JSONs, logs)"
    echo "  • All source data (prices, news, signals, indices, analysis)"
    echo "  • All dashboard data"
    echo ""
    echo "Preserved:"
    echo "  • Config files: fx-portfolio/config/*.json"
    echo "  • System config: fx-dashboard/data/system_config.json"
    echo "  • Scripts and documentation"
    echo ""
    echo "Next steps:"
    echo "  • Run pipeline to generate fresh data"
    echo "  • Deploy dashboard: publish-github-pages fx-dashboard"
    echo ""
    ;;

  *)
    echo "Error: Invalid mode '$MODE'"
    echo ""
    echo "Usage: ./scripts/clear-all-data.sh [--exports-only|--latest|--all]"
    echo ""
    echo "Modes:"
    echo "  --exports-only   Clear only exported site data"
    echo "  --latest         Clear exports + source data for today ($TODAY)"
    echo "  --all            Clear all exports + all source data"
    exit 1
    ;;
esac

echo "================================================================"
