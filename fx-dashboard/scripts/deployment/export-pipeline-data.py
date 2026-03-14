#!/usr/bin/env python3
"""
Pipeline Data Exporter (Config-Driven)

Exports data from each pipeline step to combined CSVs for dashboard visualization.
Now fully config-driven - reads paths and schemas from pipeline_steps.json.

Version 2.0: Refactored to use config instead of hardcoded paths.
"""

import json
import csv
import glob
import os
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.csv_helper import read_csv, load_schema
from utilities.pipeline_paths import PipelinePaths

BASE_DIR = Path('/workspace/group/fx-portfolio')
SITE_DATA_DIR = BASE_DIR / 'site_data'
CONFIG_PATH = BASE_DIR / 'config' / 'pipeline_steps.json'


def load_pipeline_config():
    """Load pipeline configuration"""
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def get_all_files_for_step(step_id):
    """
    Get all data files for a given step using config-driven paths.

    Args:
        step_id: Step ID (e.g., '1', '2', '3')

    Returns:
        List of file paths sorted by name
    """
    paths = PipelinePaths(step_id)
    patterns = paths.get_output_patterns()

    all_files = []
    for pattern in patterns:
        full_pattern = str(BASE_DIR / pattern)
        all_files.extend(glob.glob(full_pattern))

    return sorted(all_files)


def export_step_generic(step_id, step_name, process_schema_name=None):
    """
    Generic export function for most steps.

    Args:
        step_id: Step ID from config
        step_name: Display name for logging
        process_schema_name: Schema name for csv_helper (defaults to step_id)

    Returns:
        Number of records exported
    """
    if process_schema_name is None:
        process_schema_name = step_id

    output = []

    # Get all files using config-driven approach
    files = get_all_files_for_step(step_id)

    if not files:
        print(f"⚠️  Step {step_id}: No files found")
        return 0

    # Read all CSV files and combine
    for filepath in files:
        try:
            date = Path(filepath).stem
            rows = read_csv(process_schema_name, date=date, validate=False)
            output.extend(rows)
        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")

    # Write combined CSV using config-driven output path
    output_file = SITE_DATA_DIR / f'step{step_id}_{get_step_filename(step_id)}.csv'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='') as f:
        if output:
            # Get column order from schema (source of truth)
            schema = load_schema(step_id)
            fieldnames = [col['name'] for col in schema['columns']]

            # Write CSV with schema-defined columns
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step {step_id}: Exported {len(output)} {step_name.lower()} records")
    return len(output)


def get_step_filename(step_id):
    """
    Get the output filename for a step based on convention.

    Args:
        step_id: Step ID (e.g., '1', '2', '3')

    Returns:
        Filename (e.g., 'indices', 'news', 'signals')
    """
    filenames = {
        '1': 'exchange_rates_matrix',  # Special case - matrix format
        '2': 'indices',
        '3': 'news',
        '4': 'horizons',
        '4.1': 'currency_events',
        '5': 'signals',
        '6': 'realization',
        '7': 'aggregated_signals',
        '8': 'trades',
        '9': 'portfolios'
    }
    return filenames.get(step_id, 'data')


def export_step1_exchange_rates():
    """Step 1: Export exchange rates as matrix CSV (special format for dashboard)"""

    # Get all price CSV files using config
    price_files = get_all_files_for_step('1')

    if not price_files:
        print("⚠️  Step 1: No exchange rate files found")
        return 0

    # Get list of currencies from system config
    from utilities.config_loader import get_currencies
    currencies = get_currencies()

    # Build matrix format: one row per (date, base_currency) with all quote currencies as columns
    matrix_rows = []

    for filepath in price_files:
        try:
            date = Path(filepath).stem
            rows = read_csv('1', date=date, validate=False)

            # Group by base currency
            by_base = {}
            for row in rows:
                base = row['base_currency']
                quote = row['quote_currency']
                rate = float(row['rate'])

                if base not in by_base:
                    by_base[base] = {'date': date, 'base_currency': base}

                by_base[base][quote] = rate

            # Add to matrix rows
            for base_currency in currencies:
                if base_currency in by_base:
                    matrix_rows.append(by_base[base_currency])

        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")

    # Write matrix CSV
    output_file = SITE_DATA_DIR / 'step1_exchange_rates_matrix.csv'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='') as f:
        if matrix_rows:
            fieldnames = ['date', 'base_currency'] + currencies
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(matrix_rows)

    print(f"✓ Step 1: Exported {len(matrix_rows)} exchange rate matrix rows ({len(price_files)} dates × {len(currencies)} currencies)")
    return len(matrix_rows)


def export_step4_1_currency_events():
    """Step 4.1: Currency Events Reference"""

    # Get path from config
    paths = PipelinePaths('4.1')
    events_file = paths.get_output_path()

    if not events_file.exists():
        print("⚠️  Step 4.1: Currency events file not found")
        return 0

    with open(events_file, 'r') as f:
        events_data = json.load(f)

    # Flatten events array to CSV format
    output = []
    for event in events_data.get('events', []):
        output.append({
            'event_id': event['event_id'],
            'event_name': event['event_name'],
            'required_keywords': ','.join(event.get('required_keywords', [])),  # Optional field
            'keywords': ','.join(event['keywords']),  # Join keywords array into comma-separated string
            'signal': event['signal'],
            'description': event['description']
        })

    # Write CSV
    output_file = SITE_DATA_DIR / 'step4_1_currency_events.csv'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='') as f:
        if output:
            fieldnames = ['event_id', 'event_name', 'required_keywords', 'keywords', 'signal', 'description']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 4.1: Exported {len(output)} currency event definitions")
    return len(output)


def export_pipeline_config():
    """Export pipeline_steps.json to site_data for dashboard"""
    config_file = CONFIG_PATH
    output_file = SITE_DATA_DIR / 'pipeline_steps.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(config_file, 'r') as f_in:
        config = json.load(f_in)

    with open(output_file, 'w') as f_out:
        json.dump(config, f_out, indent=2)

    print(f"✓ Pipeline config: Exported to {output_file}")


def export_system_config():
    """Export system_config.json to site_data for dashboard"""
    config_file = BASE_DIR / 'config' / 'system_config.json'
    output_file = SITE_DATA_DIR / 'system_config.json'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(config_file, 'r') as f_in:
        config = json.load(f_in)

    with open(output_file, 'w') as f_out:
        json.dump(config, f_out, indent=2)

    print(f"✓ System config: Exported to {output_file}")


def main():
    """Main export function - now fully config-driven"""
    print("=" * 60)
    print("Pipeline Data Exporter (Config-Driven v2.0)")
    print("=" * 60)

    # Create output directory
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    total = 0

    # Load config to get all exportable steps
    config = load_pipeline_config()
    steps = config.get('steps', {})

    # Step 1: Special case (matrix format)
    total += export_step1_exchange_rates()

    # Steps 2-9: Use generic export (config-driven)
    exportable_steps = {
        '2': 'index records',
        '3': 'news articles',
        '4': 'horizon analyses',
        '5': 'signals',
        '6': 'realization checks',
        '7': 'aggregated signal records',
        '8': 'trade records',
        '9': 'strategy records'
    }

    for step_id, description in exportable_steps.items():
        if step_id in steps:
            step_name = steps[step_id].get('name', description)
            total += export_step_generic(step_id, description, process_schema_name=step_id)

    # Step 4.1: Special case (JSON to CSV)
    if '4.1' in steps:
        export_step4_1_currency_events()

    # Export configs
    export_pipeline_config()
    export_system_config()

    print()
    print("=" * 60)
    print("Export Complete")
    print("=" * 60)
    print(f"CSV files saved to: {SITE_DATA_DIR}")
    print()
    print(f"Total records exported: {total}")
    print("=" * 60)


if __name__ == '__main__':
    main()
