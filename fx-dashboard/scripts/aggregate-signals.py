#!/usr/bin/env python3
"""
Signal Aggregator (Step 7)

Aggregates unrealized signals from Step 6 by grouping on:
- date
- generator_id
- estimator_id
- currency

Calculates average predicted_direction and confidence for each group.

Usage:
    python3 scripts/aggregate-signals.py --date YYYY-MM-DD

Input: Step 6 realization data (data/signal-realization/YYYY-MM-DD.json)
Output: data/aggregated-signals/aggregated_signals.csv
"""

import json
import os
import glob
import sys
import argparse
import math
from datetime import datetime
from collections import defaultdict

sys.path.append('/workspace/group/fx-portfolio/scripts')
from pipeline_logger import PipelineLogger

CURRENCIES = ["EUR", "USD", "GBP", "JPY", "CHF", "AUD", "CAD", "NOK", "SEK", "CNY", "MXN"]

def load_unrealized_signals(date_str):
    """
    Load unrealized signals from Step 6 (signal-realization) for a specific date

    Returns: List of signal dicts
    """
    signals = []

    # Read from signal-realization directory (Step 6 output)
    realization_file = f'/workspace/group/fx-portfolio/data/signal-realization/{date_str}.json'

    if not os.path.exists(realization_file):
        return signals

    try:
        with open(realization_file, 'r') as f:
            data = json.load(f)

        # Filter for unrealized signals only
        for record in data.get('records', []):
            if record.get('realized') == False:
                # Add process_date as 'date' for aggregation grouping
                record['date'] = data.get('process_date', date_str)
                signals.append(record)
    except Exception as e:
        print(f"  ⚠️  Error reading {realization_file}: {e}")

    return signals

def aggregate_signals(signals):
    """
    Aggregate signals by (date, generator_id, estimator_id, currency)

    For each group:
    - Count number of signals
    - Calculate average confidence
    - Determine aggregate direction (based on weighted average)

    Returns: List of aggregated signal dicts
    """
    # Group signals by key
    groups = defaultdict(list)

    for signal in signals:
        key = (
            signal.get('date', ''),
            signal.get('generator_id', ''),
            signal.get('estimator_id', ''),
            signal.get('currency', '')
        )
        groups[key].append(signal)

    # Aggregate each group
    aggregated = []

    for (date, generator_id, estimator_id, currency), group_signals in groups.items():
        # Calculate weighted average direction
        # bullish = +1, bearish = -1, neutral = 0
        direction_scores = []
        confidences = []

        for sig in group_signals:
            direction = sig.get('predicted_direction', 'neutral')
            signal_value = sig.get('signal', 0)  # Step 6 now uses 'signal' (confidence * magnitude)

            if direction == 'bullish':
                direction_scores.append(signal_value)
            elif direction == 'bearish':
                direction_scores.append(-signal_value)
            else:
                direction_scores.append(0)

            confidences.append(signal_value)

        # Calculate aggregate metrics
        avg_score = sum(direction_scores) / len(direction_scores) if direction_scores else 0
        signal_count = len(group_signals)

        # Calculate penalty factor based on signal count (Option B: Smooth penalty curve)
        # Reaches ~0.9 at 4 articles, ~1.0 at 8 articles
        # Formula: min(log(count + 1) / log(5), 1.0)
        penalty_factor = min(math.log(signal_count + 1) / math.log(5), 1.0)

        # Apply penalty to reduce signal when there are few articles
        # This prevents single articles from generating high-confidence signals
        base_signal = avg_score
        adjusted_signal = base_signal * penalty_factor

        # Store SIGNED signal (after penalty applied)
        # Positive = bullish, Negative = bearish, Near-zero = neutral
        aggregate_signal = adjusted_signal

        aggregated.append({
            'date': date,
            'generator_id': generator_id,
            'estimator_id': estimator_id,
            'currency': currency,
            'signal_count': signal_count,
            'penalty_factor': round(penalty_factor, 4),  # Show penalty factor for visibility
            'base_signal': round(base_signal, 4),  # Signal before penalty
            'aggregate_signal': round(aggregate_signal, 4)  # Signed: positive=bullish, negative=bearish (after penalty)
        })

    # Sort by date, currency, generator_id
    aggregated.sort(key=lambda x: (x['date'], x['currency'], x['generator_id'], x['estimator_id']))

    return aggregated

def save_aggregated_signals(aggregated_signals, date_str):
    """
    Save aggregated signals to CSV, merging with existing data.
    Replaces rows for the current date, keeps other dates.
    """
    import csv

    output_dir = '/workspace/group/fx-portfolio/data/aggregated-signals'
    os.makedirs(output_dir, exist_ok=True)

    output_file = f'{output_dir}/aggregated_signals.csv'

    fieldnames = [
        'date', 'generator_id', 'estimator_id', 'currency',
        'signal_count', 'penalty_factor', 'base_signal', 'aggregate_signal'
    ]

    # Check if file exists and load existing data
    file_exists = os.path.exists(output_file)
    other_date_rows = []

    if file_exists:
        with open(output_file, 'r') as f:
            reader = csv.DictReader(f)
            # Keep rows from other dates
            other_date_rows = [row for row in reader if row.get('date') != date_str]

    # Write all data: other dates + current date
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        # Write other dates first
        writer.writerows(other_date_rows)
        # Write current date
        writer.writerows(aggregated_signals)

    return output_file

def main():
    parser = argparse.ArgumentParser(description='Aggregate unrealized signals (Step 7)')
    parser.add_argument('--date', required=True, help='Date to process (YYYY-MM-DD)')
    args = parser.parse_args()

    logger = PipelineLogger('step7', 'Aggregate Signals')
    logger.start()

    date_str = args.date

    print(f"Processing date: {date_str}")

    # Validate date format
    try:
        datetime.fromisoformat(date_str)
    except ValueError:
        logger.error(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")
        logger.fail()
        sys.exit(1)

    # Validate upstream data (Step 6: Signal Realization)
    print(f"\n{'='*60}")
    print("Validating Upstream Data (Step 6)")
    print(f"{'='*60}")

    realization_file = f'/workspace/group/fx-portfolio/data/signal-realization/{date_str}.json'

    if not os.path.exists(realization_file):
        logger.error(f"No realization file found for {date_str}. Run Step 6 first.")
        logger.fail()
        sys.exit(1)

    print(f"  ✓ Found realization file: {realization_file}")

    # Load unrealized signals
    print(f"\n{'='*60}")
    print("Loading Unrealized Signals")
    print(f"{'='*60}")

    signals = load_unrealized_signals(date_str)
    print(f"  ✓ Loaded {len(signals)} unrealized signals")

    if len(signals) == 0:
        print(f"\n⚠️  No unrealized signals found for {date_str}")
        print("  This is normal if all signals have been realized or expired.")

        # Still save (will remove this date's data if it existed)
        output_file = save_aggregated_signals([], date_str)
        logger.add_info('output_file', output_file)
        logger.add_count('unrealized_signals', 0)
        logger.add_count('aggregated_groups', 0)
        logger.success()
        logger.finish()
        return

    # Aggregate signals
    print(f"\n{'='*60}")
    print("Aggregating Signals")
    print(f"{'='*60}")

    aggregated = aggregate_signals(signals)
    print(f"  ✓ Created {len(aggregated)} aggregated signal groups")

    # Show summary by currency
    print(f"\nAggregated signals by currency:")
    currency_counts = defaultdict(int)
    for agg in aggregated:
        currency_counts[agg['currency']] += 1

    for currency in sorted(currency_counts.keys()):
        count = currency_counts[currency]
        print(f"  {currency}: {count} aggregated groups")

    # Save to CSV
    print(f"\n{'='*60}")
    print("Saving Aggregated Signals")
    print(f"{'='*60}")

    output_file = save_aggregated_signals(aggregated, date_str)
    print(f"  ✓ Saved to: {output_file}")

    # Log metrics
    logger.add_count('unrealized_signals', len(signals))
    logger.add_count('aggregated_groups', len(aggregated))
    logger.add_info('output_file', output_file)

    print(f"\n{'='*60}")
    print(f"✓ Signal Aggregation Complete")
    print(f"{'='*60}")
    print(f"  Unrealized signals: {len(signals)}")
    print(f"  Aggregated groups: {len(aggregated)}")
    print(f"  Output: {output_file}")

    logger.success()
    logger.finish()

if __name__ == '__main__':
    main()
