# Export Pipeline Data - Safety Analysis

## Purpose
The `export-pipeline-data.py` script exports all pipeline data to CSV format for dashboard visualization. This is a **read-only export operation** that should be run before publishing the dashboard.

## Safety Guarantees

### ✅ Source Data is NEVER Modified
- All export functions use **read-only operations** on source data
- Source files are located in:
  - `data/prices/` (exchange rates)
  - `data/indices/` (currency indices)
  - `data/news/` (news articles)
  - `data/article-analysis/` (horizon analyses)
  - `data/signals/` (sentiment signals)
  - `data/signal-realization/` (signal realization checks)
  - `config/` (configuration files)

### ✅ Only Export Directory is Written
- All exports write ONLY to `data/exports/` directory
- Export files:
  - `step1_exchange_rates_matrix.csv`
  - `step2_indices.csv`
  - `step3_news.csv`
  - `step4_horizons.csv`
  - `step5_signals.csv`
  - `step6_realization.csv`
  - `step7_aggregated_signals.csv` (exported by step 7 script)
  - `step8_trades.csv` (exported by step 8 script)
  - `step9_strategies.csv` (exported by step 9 script)
  - `pipeline_steps.json`
  - `system_config.json`
  - `step_counts_by_date.json`

### ✅ No Deletions
- The script never deletes any files
- Exports overwrite previous exports (which is safe)
- Source data remains untouched

### ✅ Configuration Files
- Config files are **copied** (not moved) using `shutil.copy()`
- Original config files remain in `config/` directory

## Usage

### Standard Export (before dashboard publish)
```bash
cd /workspace/group/fx-portfolio
python3 scripts/export-pipeline-data.py
```

### What Gets Exported
1. **Step 1**: Exchange rate matrix (all dates, all currency pairs)
2. **Step 2**: Currency indices (synthetic index values)
3. **Step 3**: News articles (scraped articles with metadata)
4. **Step 4**: Horizon analyses (time horizon predictions)
5. **Step 5**: Sentiment signals (directional predictions)
6. **Step 6**: Signal realization (signal performance tracking)
7. **Pipeline config**: Step definitions and dependencies
8. **System config**: Strategies, traders, generators, estimators

Note: Steps 7, 8, 9 export their own CSVs when they run.

## Integration with Pipeline

The export script should be run:
1. After running the full pipeline for a date
2. Before publishing the dashboard

Example workflow:
```bash
# Run daily pipeline
./run-full-pipeline.sh 2026-03-03

# Export all data for dashboard
python3 scripts/export-pipeline-data.py

# Copy to dashboard and publish
cp data/exports/*.csv sites/fx-dashboard/data/
cp data/exports/*.json sites/fx-dashboard/data/
# ... then deploy dashboard
```

## Legacy Script

The standalone `export-exchange-rates.py` script is now integrated into the main export. It can still be used independently if needed, but `export-pipeline-data.py` now includes Step 1 exchange rates.
