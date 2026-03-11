#!/usr/bin/env python3
"""
Backfill Article IDs to Existing CSV Files

Adds article_id column to existing news, horizons, signals, and realization CSV files
without re-running expensive LLM processes.

The article_id is deterministically generated from the URL, so it will always be
the same for the same article across all pipeline steps.
"""

import glob
import sys
import csv as csv_module
from pathlib import Path

sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.csv_helper import read_csv, write_csv, load_schema
from utilities.article_id import generate_article_id
from utilities.pipeline_paths import PipelinePaths


def backfill_step(step_id, step_name, date_pattern='*'):
    """
    Backfill article_id for a specific pipeline step.

    Args:
        step_id: Pipeline step ID (e.g., '3', '4', '5', '6')
        step_name: Display name for logging
        date_pattern: Glob pattern for dates (default: '*' for all dates)

    Returns:
        (files_updated, rows_updated) tuple
    """
    print(f"\n{step_name} (Step {step_id}):")
    print("-" * 60)

    # Find all CSV files for this step
    pattern = f'/workspace/group/fx-portfolio/data/*/{date_pattern}.csv'
    if step_id == '3':
        pattern = '/workspace/group/fx-portfolio/data/news/*.csv'
    elif step_id == '4':
        pattern = '/workspace/group/fx-portfolio/data/article-analysis/*.csv'
    elif step_id == '5':
        pattern = '/workspace/group/fx-portfolio/data/signals/*.csv'
    elif step_id == '6':
        pattern = '/workspace/group/fx-portfolio/data/signal-realization/*.csv'

    files = sorted(glob.glob(pattern))

    if not files:
        print(f"  No files found for step {step_id}")
        return 0, 0

    files_updated = 0
    rows_updated = 0

    for filepath in files:
        # Extract date from filename
        filename = Path(filepath).stem
        date_str = filename

        try:
            # Read existing data
            rows = read_csv(step_id, date=date_str, validate=False)

            if not rows:
                print(f"  {date_str}: No rows (skipped)")
                continue

            # Check if article_id already exists
            if rows and 'article_id' in rows[0]:
                print(f"  {date_str}: Already has article_id (skipped)")
                continue

            # Add article_id to each row
            for row in rows:
                url = row.get('url', '')
                if url:
                    # Insert article_id as second column (after date)
                    article_id = generate_article_id(url)
                    row['article_id'] = article_id
                else:
                    row['article_id'] = ''

            # Write back to CSV (with validation disabled to allow column reordering)
            paths = PipelinePaths(step_id)
            output_file = paths.get_output_path(date=date_str)

            # Write with correct column order (from schema)
            schema = load_schema(step_id)
            fieldnames = [col['name'] for col in schema['columns']]

            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', newline='') as f:
                writer = csv_module.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            files_updated += 1
            rows_updated += len(rows)
            print(f"  ✓ {date_str}: Added article_id to {len(rows)} rows")

        except Exception as e:
            print(f"  ✗ {date_str}: Error - {e}")

    return files_updated, rows_updated


def main():
    """Backfill article IDs for all relevant pipeline steps"""
    print("=" * 70)
    print("Backfill Article IDs to Existing CSV Files")
    print("=" * 70)
    print("\nThis will add article_id column to existing pipeline data files")
    print("without re-running expensive LLM processes.\n")

    total_files = 0
    total_rows = 0

    # Step 3: News
    files, rows = backfill_step('3', 'News Articles')
    total_files += files
    total_rows += rows

    # Step 4: Time Horizon Analysis
    files, rows = backfill_step('4', 'Time Horizon Analysis')
    total_files += files
    total_rows += rows

    # Step 5: Sentiment Signals
    files, rows = backfill_step('5', 'Sentiment Signals')
    total_files += files
    total_rows += rows

    # Step 6: Signal Realization
    files, rows = backfill_step('6', 'Signal Realization')
    total_files += files
    total_rows += rows

    # Summary
    print("\n" + "=" * 70)
    print("Backfill Summary")
    print("=" * 70)
    print(f"Files updated: {total_files}")
    print(f"Rows updated: {total_rows}")
    print("=" * 70)

    if total_files > 0:
        print(f"\n✓ Backfill complete! Added article_id to {total_rows} rows across {total_files} files.")
    else:
        print("\n✓ No files needed updating - all files already have article_id column.")


if __name__ == '__main__':
    main()
