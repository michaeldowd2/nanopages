#!/usr/bin/env python3
"""
Migrate Process 4 (Time Horizon Analysis) from JSON to CSV format.

Converts: data/article-analysis/{date}.json
To:       data/article-analysis/{date}.csv

Schema:
- date, source, url, currency, title, snippet, time_horizon, confidence, reasoning
"""

import json
import csv
import sys
from pathlib import Path
from datetime import datetime
import argparse

BASE_DIR = Path(__file__).parent.parent.parent
ANALYSIS_DIR = BASE_DIR / "data" / "article-analysis"


def load_json_file(json_path):
    """Load JSON data from file."""
    with open(json_path, 'r') as f:
        return json.load(f)


def convert_to_csv_rows(date, json_data):
    """
    Convert JSON time horizon analysis data to CSV rows.

    Expected JSON format:
    {
      "analyses": [
        {
          "article_url": "...",
          "article_title": "...",
          "snippet": "...",
          "currency": "EUR",
          "source": "newsapi",
          "time_horizon": "short",
          "confidence": 0.85,
          "reasoning": "..."
        }
      ]
    }

    Output CSV format:
    date, source, url, currency, title, snippet, time_horizon, confidence, reasoning
    """
    rows = []

    analyses = json_data.get('analyses', [])

    for analysis in analyses:
        rows.append({
            'date': date,
            'source': analysis.get('source', ''),
            'url': analysis.get('article_url', ''),
            'currency': analysis.get('currency', ''),
            'title': analysis.get('article_title', ''),
            'snippet': analysis.get('snippet', ''),
            'time_horizon': analysis.get('time_horizon', ''),
            'confidence': analysis.get('confidence', ''),
            'reasoning': analysis.get('reasoning', '')
        })

    return rows


def write_csv_file(csv_path, rows):
    """Write rows to CSV file."""
    if not rows:
        print(f"Warning: No data to write for {csv_path}")
        return

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'date', 'source', 'url', 'currency', 'title', 'snippet',
            'time_horizon', 'confidence', 'reasoning'
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Wrote {len(rows)} rows to {csv_path}")


def migrate_file(json_path, dry_run=False):
    """Migrate a single JSON file to CSV format."""
    # Extract date from filename
    date_str = json_path.stem

    # Validate date format
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        print(f"Skipping {json_path.name} (invalid date format)")
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
    csv_path = ANALYSIS_DIR / f"{date_str}.csv"

    if dry_run:
        print(f"[DRY RUN] Would convert {json_path.name} -> {csv_path.name} ({len(rows)} rows)")
        return True
    else:
        write_csv_file(csv_path, rows)
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Migrate Process 4 (Time Horizon Analysis) from JSON to CSV'
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
    print("Process 4 Migration: Time Horizon Analysis (JSON -> CSV)")
    print("=" * 60)

    if not ANALYSIS_DIR.exists():
        print(f"Error: Analysis directory not found: {ANALYSIS_DIR}")
        sys.exit(1)

    # Find all JSON files
    json_files = sorted(ANALYSIS_DIR.glob('*.json'))

    if not json_files:
        print("No JSON files found to migrate")
        sys.exit(0)

    # Filter by date if specified
    if args.date:
        json_files = [f for f in json_files if f.stem == args.date]
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
