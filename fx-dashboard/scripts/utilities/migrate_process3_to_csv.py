#!/usr/bin/env python3
"""
Migrate Process 3 (News) from JSON to CSV format.

Converts: data/news/{currency}/{date}.json (multiple currencies)
To:       data/news/{date}.csv (single file with currency column)

Schema:
- date, source, url, currency, title, snippet
"""

import json
import csv
import sys
from pathlib import Path
from datetime import datetime
import argparse

BASE_DIR = Path(__file__).parent.parent.parent
NEWS_DIR = BASE_DIR / "data" / "news"


def load_json_file(json_path):
    """Load JSON data from file."""
    with open(json_path, 'r') as f:
        return json.load(f)


def convert_to_csv_rows(date, currency, json_data):
    """
    Convert JSON news data to CSV rows.

    Expected JSON format:
    {
      "articles": [
        {
          "title": "...",
          "snippet": "...",
          "url": "...",
          "source": "newsapi",
          ...
        }
      ]
    }

    Output CSV format:
    date, source, url, currency, title, snippet
    """
    rows = []

    articles = json_data.get('articles', [])

    for article in articles:
        rows.append({
            'date': date,
            'source': article.get('source', ''),
            'url': article.get('url', ''),
            'currency': currency,
            'title': article.get('title', ''),
            'snippet': article.get('snippet', '')
        })

    return rows


def write_csv_file(csv_path, rows):
    """Write rows to CSV file (append if exists)."""
    if not rows:
        print(f"Warning: No data to write")
        return

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if file exists to determine if we need to write header
    write_header = not csv_path.exists()

    with open(csv_path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['date', 'source', 'url', 'currency', 'title', 'snippet'])
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def migrate_currency_files_for_date(date_str, dry_run=False):
    """Migrate all currency files for a specific date."""
    # Find all currency subdirectories
    currency_dirs = [d for d in NEWS_DIR.iterdir() if d.is_dir()]

    if not currency_dirs:
        print(f"No currency directories found in {NEWS_DIR}")
        return False

    all_rows = []
    source_files = []

    for currency_dir in currency_dirs:
        currency = currency_dir.name
        json_path = currency_dir / f"{date_str}.json"

        if not json_path.exists():
            continue

        # Load JSON data
        try:
            json_data = load_json_file(json_path)
        except Exception as e:
            print(f"Error loading {json_path}: {e}")
            continue

        # Convert to CSV rows
        rows = convert_to_csv_rows(date_str, currency, json_data)
        all_rows.extend(rows)
        source_files.append(f"{currency}/{date_str}.json")

    if not all_rows:
        return False

    # Write consolidated CSV file
    csv_path = NEWS_DIR / f"{date_str}.csv"

    if dry_run:
        print(f"[DRY RUN] Would convert {len(source_files)} file(s) -> {csv_path.name} ({len(all_rows)} rows)")
        for source in source_files:
            print(f"  - {source}")
        return True
    else:
        write_csv_file(csv_path, all_rows)
        print(f"✓ Wrote {len(all_rows)} rows from {len(source_files)} file(s) to {csv_path}")
        return True


def find_all_dates():
    """Find all unique dates across all currency subdirectories."""
    dates = set()

    currency_dirs = [d for d in NEWS_DIR.iterdir() if d.is_dir()]

    for currency_dir in currency_dirs:
        json_files = currency_dir.glob('*.json')
        for json_file in json_files:
            # Extract date from filename
            date_str = json_file.stem
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
                dates.add(date_str)
            except ValueError:
                continue

    return sorted(dates)


def main():
    parser = argparse.ArgumentParser(
        description='Migrate Process 3 (News) from JSON to CSV'
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
    print("Process 3 Migration: News (JSON -> CSV)")
    print("=" * 60)

    if not NEWS_DIR.exists():
        print(f"Error: News directory not found: {NEWS_DIR}")
        sys.exit(1)

    # Find all dates
    if args.date:
        dates = [args.date]
    else:
        dates = find_all_dates()

    if not dates:
        print("No dates found to migrate")
        sys.exit(0)

    print(f"Found {len(dates)} date(s) to migrate")
    print()

    success_count = 0
    failure_count = 0

    for date_str in dates:
        if migrate_currency_files_for_date(date_str, dry_run=args.dry_run):
            success_count += 1
        else:
            print(f"No data found for {date_str}")
            failure_count += 1

    # Summary
    print()
    print("=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Successfully migrated: {success_count}")
    print(f"Failed/No data: {failure_count}")
    print(f"Total dates: {len(dates)}")

    if args.dry_run:
        print()
        print("DRY RUN - No files were modified")

    if failure_count > 0 and success_count == 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
