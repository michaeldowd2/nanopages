#!/usr/bin/env python3
"""
Migration: Add signal column to existing Process 5 (signals) files

Calculates signal = confidence × magnitude_weight for all existing signals
without re-running the expensive LLM generation.

Magnitude weights:
- small: 0.4
- medium: 0.7
- large: 1.4
- null/None: 0.7 (default)
"""

import csv
import glob
from pathlib import Path

# Magnitude weight mapping (same as used in Process 6)
MAGNITUDE_MULTIPLIERS = {
    'small': 0.4,
    'medium': 0.7,
    'large': 1.4
}

def calculate_signal(confidence, magnitude):
    """Calculate signal value from confidence and magnitude"""
    magnitude_weight = MAGNITUDE_MULTIPLIERS.get(magnitude, 0.7) if magnitude else 0.7
    return round(confidence * magnitude_weight, 4)

def migrate_signal_file(filepath):
    """Add signal column to a single signals CSV file"""
    # Read existing data
    with open(filepath, 'r', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print(f"  ⚠ Empty file, skipping")
        return 0

    # Check if signal column already exists
    if 'signal' in rows[0]:
        print(f"  ℹ Signal column already exists, skipping")
        return 0

    # Calculate signal for each row
    for row in rows:
        confidence = float(row.get('confidence', 0))
        magnitude = row.get('predicted_magnitude')
        row['signal'] = calculate_signal(confidence, magnitude)

    # Write back with new column
    fieldnames = list(rows[0].keys())

    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)

def main():
    print("="*60)
    print("Migration: Add signal column to Process 5 files")
    print("="*60)

    # Find all signal files
    signal_files = sorted(glob.glob('/workspace/group/fx-portfolio/data/signals/????-??-??.csv'))

    print(f"\nFound {len(signal_files)} signal files to migrate\n")

    total_rows = 0
    migrated_files = 0

    for filepath in signal_files:
        date = Path(filepath).stem
        print(f"{date}...", end=' ')

        try:
            rows_migrated = migrate_signal_file(filepath)
            if rows_migrated > 0:
                print(f"✓ Added signal to {rows_migrated} rows")
                migrated_files += 1
                total_rows += rows_migrated
            else:
                print()
        except Exception as e:
            print(f"✗ Error: {e}")

    print("\n" + "="*60)
    print(f"Migration complete:")
    print(f"  Files migrated: {migrated_files}")
    print(f"  Total rows updated: {total_rows}")
    print("="*60)

if __name__ == '__main__':
    main()
