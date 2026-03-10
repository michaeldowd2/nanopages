#!/usr/bin/env python3
"""
Step 7: Signal Aggregator

Aggregates unrealized signals from Step 6 by grouping on:
- currency
- generator_id
- estimator_id

Calculates average predicted_direction and confidence for each group.

Reads from Process 6 CSV, writes to Process 7 CSV.

Input: data/signal-realization/{date}.csv (from Process 6)
Output: data/aggregated-signals/{date}.csv
"""

import os
import sys
import argparse
import math
from datetime import datetime
from collections import defaultdict

sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.pipeline_logger import PipelineLogger
from utilities.csv_helper import read_csv, write_csv
from utilities.config_loader import get_currencies

CURRENCIES = get_currencies()


def aggregate_signals(signals, date_str):
    """
    Aggregate signals by (currency, generator_id, estimator_id)

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
            signal.get('currency', ''),
            signal.get('generator_id', ''),
            signal.get('estimator_id', '')
        )
        groups[key].append(signal)

    # Aggregate each group
    aggregated = []

    for (currency, generator_id, estimator_id), group_signals in groups.items():
        # Calculate weighted average direction
        # bullish = +1, bearish = -1, neutral = 0
        direction_scores = []
        confidences = []

        for sig in group_signals:
            direction = sig.get('predicted_direction', 'neutral')
            signal_value = float(sig.get('signal', 0))  # confidence * magnitude

            if direction == 'bullish':
                direction_scores.append(signal_value)
            elif direction == 'bearish':
                direction_scores.append(-signal_value)
            else:
                direction_scores.append(0)

            confidences.append(signal_value)

        # Calculate aggregate metrics
        avg_score = sum(direction_scores) / len(direction_scores) if direction_scores else 0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        signal_count = len(group_signals)

        # Calculate penalty factor based on signal count
        # Idea: Fewer signals = less reliable, so reduce the signal strength
        # Formula: penalty = min(1.0, sqrt(signal_count / 4))
        # - 1 signal: penalty = 0.50
        # - 2 signals: penalty = 0.71
        # - 4 signals: penalty = 1.00 (no penalty)
        # - 8 signals: penalty = 1.00 (capped)
        penalty_factor = min(1.0, math.sqrt(signal_count / 4.0))

        # Base signal (before penalty)
        base_signal = avg_score

        # Apply penalty to get aggregate signal
        aggregate_signal = base_signal * penalty_factor

        # Determine net direction based on aggregate signal
        if aggregate_signal > 0.05:
            net_direction = 'bullish'
        elif aggregate_signal < -0.05:
            net_direction = 'bearish'
        else:
            net_direction = 'neutral'

        aggregated.append({
            'date': date_str,
            'currency': currency,
            'generator_id': generator_id,
            'estimator_id': estimator_id,
            'signal_count': signal_count,
            'penalty_factor': round(penalty_factor, 4),
            'base_signal': round(base_signal, 4),
            'aggregate_signal': round(aggregate_signal, 4),
            'avg_confidence': round(avg_confidence, 4),
            'net_direction': net_direction
        })

    # Sort by currency, generator_id, estimator_id
    aggregated.sort(key=lambda x: (x['currency'], x['generator_id'], x['estimator_id']))

    return aggregated


def main(date_str=None):
    """Main function - aggregate unrealized signals"""

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    logger = PipelineLogger('step7', 'Aggregate Signals')
    logger.start()

    try:
        print("="*60)
        print("Signal Aggregator - CSV Output")
        print("="*60)
        print(f"\nProcessing date: {date_str}")

        # Load unrealized signals from Process 6
        print(f"\n1. Loading unrealized signals from Process 6...")
        try:
            all_signals = read_csv('process_6_realization', date=date_str, validate=False)
            print(f"   ✓ Loaded {len(all_signals)} realization records")
        except FileNotFoundError:
            print(f"   ✗ No realization data found for {date_str}")
            print(f"   Step 6 (Signal Realization) must be run first")
            logger.error(f"Missing upstream data: process_6_realization for {date_str}")
            logger.fail()
            return

        # Filter for unrealized signals only
        unrealized = [s for s in all_signals if str(s.get('realized', '')).lower() == 'false']
        print(f"   ✓ Found {len(unrealized)} unrealized signals")
        logger.add_count('unrealized_signals', len(unrealized))

        if len(unrealized) == 0:
            print(f"\n   ⚠ No unrealized signals found for {date_str}")
            print("      This is normal if all signals have been realized or expired.")
            # Still write empty CSV
            csv_path = write_csv([], 'process_7_aggregated_signals', date=date_str)
            logger.add_info('output_file', str(csv_path))
            logger.add_count('aggregated_groups', 0)
            logger.success()
            return

        # Aggregate signals
        print(f"\n2. Aggregating signals...")
        aggregated = aggregate_signals(unrealized, date_str)
        print(f"   ✓ Created {len(aggregated)} aggregated signal groups")
        logger.add_count('aggregated_groups', len(aggregated))

        # Show summary by currency
        print(f"\n   Aggregated signals by currency:")
        currency_counts = defaultdict(int)
        for agg in aggregated:
            currency_counts[agg['currency']] += 1

        for currency in sorted(currency_counts.keys()):
            count = currency_counts[currency]
            print(f"      {currency}: {count} groups")

        # Write to CSV
        print(f"\n3. Saving to CSV...")
        csv_path = write_csv(aggregated, 'process_7_aggregated_signals', date=date_str)
        print(f"   ✓ Saved {len(aggregated)} aggregated signals to {csv_path}")
        logger.add_info('output_file', str(csv_path))

        # Summary
        print(f"\n{'='*60}")
        print(f"✓ Signal Aggregation Complete")
        print(f"{'='*60}")
        print(f"  Unrealized signals: {len(unrealized)}")
        print(f"  Aggregated groups: {len(aggregated)}")

        logger.success()

    except Exception as e:
        logger.error(f"Failed to aggregate signals: {e}")
        logger.fail()
        raise
    finally:
        logger.finish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Aggregate unrealized signals')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD), defaults to today')
    args = parser.parse_args()

    main(date_str=args.date)
