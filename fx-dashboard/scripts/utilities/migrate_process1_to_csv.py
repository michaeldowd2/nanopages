#!/usr/bin/env python3
"""
Migrate Process 1 (Exchange Rates) from JSON to CSV format.

Converts: data/prices/fx-rates-{date}.json
To:       data/prices/{date}.csv

Schema:
- date, base_currency, quote_currency, rate
"""

import json
import csv
import sys
from pathlib import Path
from datetime import datetime
import argparse

BASE_DIR = Path(__file__).parent.parent.parent
PRICES_DIR = BASE_DIR / "data" / "prices"


def load_json_file(json_path):
    """Load JSON data from file."""
    with open(json_path, 'r') as f:
        return json.load(f)


def convert_to_csv_rows(date, json_data):
    """
    Convert JSON exchange rate data to CSV rows.

    Expected JSON format:
    {
      "date": "2024-01-15",
      "all_pairs": {
        "EUR": {"USD": 1.09, "GBP": 0.85, ...},
        "USD": {"EUR": 0.92, "GBP": 0.78, ...},
        ...
      }
    }

    Output CSV format:
    date, base_currency, quote_currency, rate
    """
    rows = []

    # Try 'all_pairs' first (current format), fall back to 'rates' (legacy)
    rates = json_data.get('all_pairs', json_data.get('rates', {}))

    for base_currency, quote_rates in rates.items():
        for quote_currency, rate in quote_rates.items():
            rows.append({
                'date': date,
                'base_currency': base_currency,
                'quote_currency': quote_currency,
                'rate': rate
            })

    return rows


def write_csv_file(csv_path, rows):
    """Write rows to CSV file."""
    if not rows:
        print(f"Warning: No data to write for {csv_path}")
        return

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'base_currency', 'quote_currency', 'rate'])
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Wrote {len(rows)} rows to {csv_path}")


def migrate_file(json_path, dry_run=False):
    """Migrate a single JSON file to CSV format."""
    # Extract date from filename: fx-rates-2024-01-15.json
    filename = json_path.name
    if not filename.startswith('fx-rates-'):
        print(f"Skipping {filename} (unexpected format)")
        return False

    date_str = filename.replace('fx-rates-', '').replace('.json', '')

    # Validate date format
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        print(f"Skipping {filename} (invalid date format)")
        return False

    # Load JSON data
    try:
        json_data = load_json_file(json_path)
    except Exception as e:
        print(f"Error loading {json_path}: {e}")
        return False

    # Convert to CSV rows
    rows = convert_to_csv_rows(date_str, json_data)

    if not rows:
        print(f"Warning: No data found in {json_path}")
        return False

    # Write CSV file
    csv_path = PRICES_DIR / f"{date_str}.csv"

    if dry_run:
        print(f"[DRY RUN] Would convert {json_path.name} -> {csv_path.name} ({len(rows)} rows)")
        return True
    else:
        write_csv_file(csv_path, rows)
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Migrate Process 1 (Exchange Rates) from JSON to CSV'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--date',
        type=str,
        help='Migrate only specific date (YYYY-MM-DD format)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Process 1 Migration: Exchange Rates (JSON -> CSV)")
    print("=" * 60)

    if not PRICES_DIR.exists():
        print(f"Error: Prices directory not found: {PRICES_DIR}")
        sys.exit(1)

    # Find all JSON files
    json_files = sorted(PRICES_DIR.glob('fx-rates-*.json'))

    if not json_files:
        print("No JSON files found to migrate")
        sys.exit(0)

    # Filter by date if specified
    if args.date:
        json_files = [f for f in json_files if args.date in f.name]
        if not json_files:
            print(f"No files found for date: {args.date}")
            sys.exit(0)

    print(f"Found {len(json_files)} file(s) to migrate")
    print()

    success_count = 0
    failure_count = 0

    for json_path in json_files:
        if migrate_file(json_path, dry_run=args.dry_run):
            success_count += 1
        else:
            failure_count += 1

    # Summary
    print()
    print("=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Successfully migrated: {success_count}")
    print(f"Failed: {failure_count}")
    print(f"Total: {len(json_files)}")

    if args.dry_run:
        print()
        print("DRY RUN - No files were modified")

    if failure_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
