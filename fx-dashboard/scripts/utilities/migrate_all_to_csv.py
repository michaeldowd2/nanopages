#!/usr/bin/env python3
"""
Master migration script to convert all JSON data to CSV format.

Runs migration for processes 1, 3, 4, and 5 in sequence.
"""

import sys
import subprocess
from pathlib import Path
import argparse

BASE_DIR = Path(__file__).parent.parent.parent
UTILITIES_DIR = BASE_DIR / "scripts" / "utilities"


def run_migration(script_name, dry_run=False, date=None):
    """Run a migration script and return success status."""
    script_path = UTILITIES_DIR / script_name

    if not script_path.exists():
        print(f"Error: Migration script not found: {script_path}")
        return False

    cmd = ['python3', str(script_path)]

    if dry_run:
        cmd.append('--dry-run')

    if date:
        cmd.extend(['--date', date])

    print(f"\nRunning: {script_name}")
    print("=" * 60)

    try:
        result = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            check=False
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {script_name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Migrate all processes from JSON to CSV format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script runs migration for:
  - Process 1: Exchange Rates (data/prices/)
  - Process 3: News (data/news/)
  - Process 4: Time Horizon Analysis (data/article-analysis/)
  - Process 5: Sentiment Signals (data/signals/)

Examples:
  # Dry run to preview changes
  %(prog)s --dry-run

  # Migrate all data
  %(prog)s

  # Migrate specific date only
  %(prog)s --date 2024-01-15
        """
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
    parser.add_argument(
        '--process',
        type=str,
        choices=['1', '3', '4', '5'],
        help='Migrate only specific process'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Master Migration: JSON to CSV")
    print("=" * 60)

    if args.dry_run:
        print("\n*** DRY RUN MODE - No files will be modified ***\n")

    if args.date:
        print(f"Migrating date: {args.date}")
    else:
        print("Migrating all dates")

    print()

    # Define migrations
    migrations = [
        ('1', 'migrate_process1_to_csv.py', 'Exchange Rates'),
        ('3', 'migrate_process3_to_csv.py', 'News'),
        ('4', 'migrate_process4_to_csv.py', 'Time Horizon Analysis'),
        ('5', 'migrate_process5_to_csv.py', 'Sentiment Signals')
    ]

    # Filter by process if specified
    if args.process:
        migrations = [m for m in migrations if m[0] == args.process]

    results = {}

    for process_id, script_name, process_name in migrations:
        print(f"\n{'='*60}")
        print(f"Process {process_id}: {process_name}")
        print('='*60)

        success = run_migration(script_name, dry_run=args.dry_run, date=args.date)
        results[process_id] = success

        if not success and not args.dry_run:
            print(f"\n⚠ Warning: Process {process_id} migration failed")
            response = input("Continue with remaining migrations? (y/n): ")
            if response.lower() != 'y':
                print("\nMigration aborted")
                sys.exit(1)

    # Summary
    print("\n" + "=" * 60)
    print("Migration Summary")
    print("=" * 60)

    for process_id, script_name, process_name in migrations:
        status = "✓ Success" if results[process_id] else "✗ Failed"
        print(f"Process {process_id} ({process_name}): {status}")

    if args.dry_run:
        print("\n*** DRY RUN MODE - No files were modified ***")

    # Exit with error if any migration failed
    if not all(results.values()):
        print("\n⚠ Some migrations failed")
        sys.exit(1)
    else:
        print("\n✓ All migrations completed successfully")


if __name__ == '__main__':
    main()
