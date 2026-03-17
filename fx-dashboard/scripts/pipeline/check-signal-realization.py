#!/usr/bin/env python3
"""
Step 6: Signal Realization Checker

Checks realization status for all signals still within their validity window.
For a given processing date, includes signals from up to 30 days prior that have valid_to_date >= processing_date.

Reads from CSV outputs of Processes 2 and 5. Writes to Process 6 CSV output.

Input:
- data/indices/{date}.csv (from Process 2)
- data/signals/{date}.csv (from Process 5, past 30 days - includes horizon data)

Output: data/signal-realization/{date}.csv
"""

import json
import os
import sys
import argparse
import glob
from datetime import datetime, timedelta

sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.pipeline_logger import PipelineLogger
from utilities.csv_helper import read_csv, write_csv, csv_exists
from utilities.config_loader import get_currencies

CURRENCIES = get_currencies()


def load_currency_indices_multi_date(start_date, end_date):
    """
    Load currency indices and 30d_max_diff for multiple dates

    Returns: dict keyed by (currency, date) -> {'index': value, '30d_max_diff': value}
    """
    indices = {}
    current_date = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    while current_date <= end:
        date_str = current_date.strftime('%Y-%m-%d')

        try:
            rows = read_csv('process_2_indices', date=date_str, validate=False)
            for row in rows:
                currency = row['currency']
                index_value = float(row['index'])
                max_diff_value = float(row.get('30d_max_diff', 0))
                indices[(currency, date_str)] = {
                    'index': index_value,
                    '30d_max_diff': max_diff_value
                }
        except FileNotFoundError:
            pass  # Skip missing dates

        current_date += timedelta(days=1)

    return indices


def load_horizon_analyses_in_window(process_date_str):
    """
    Load all horizon analyses from the past 30 days that are still valid
    (valid_to_date >= process_date)

    Returns: dict keyed by (article_id, estimator_id, article_download_date) -> horizon_data
    """
    process_date = datetime.fromisoformat(process_date_str)
    lookback_date = process_date - timedelta(days=30)

    horizon_analyses = {}

    print(f"\n1. Loading horizon analyses from {lookback_date.strftime('%Y-%m-%d')} to {process_date_str}...")

    current_date = lookback_date
    total_loaded = 0

    while current_date <= process_date:
        date_str = current_date.strftime('%Y-%m-%d')

        try:
            rows = read_csv('process_4_horizons', date=date_str, validate=False)

            for row in rows:
                valid_to_date_str = row.get('valid_to_date', '')

                if not valid_to_date_str:
                    continue

                # Check if still valid for the processing date
                valid_to_date = datetime.fromisoformat(valid_to_date_str)
                if valid_to_date < process_date:
                    continue  # Expired

                article_id = row.get('article_id', '')
                estimator_id = row.get('estimator_id', '')
                key = (article_id, estimator_id, date_str)

                horizon_analyses[key] = {
                    'article_id': article_id,
                    'estimator_id': estimator_id,
                    'currency': row.get('currency', ''),
                    'article_download_date': date_str,
                    'time_horizon': row.get('time_horizon', ''),
                    'horizon_days': int(row.get('horizon_days', 0)),
                    'valid_to_date': valid_to_date_str,
                    'horizon_confidence': float(row.get('confidence', 0))
                }
                total_loaded += 1

        except FileNotFoundError:
            pass  # Skip missing dates

        current_date += timedelta(days=1)

    print(f"   ✓ Loaded {total_loaded} valid horizon analyses from {len(horizon_analyses)} unique articles")
    return horizon_analyses


def load_signals_from_all_dates(process_date_str):
    """
    Load all signals from the past 30 days (excluding neutral signals)

    Returns: dict keyed by (article_id, generator_id, signal_download_date) -> signal_data
    """
    process_date = datetime.fromisoformat(process_date_str)
    lookback_date = process_date - timedelta(days=30)

    signals = {}

    print(f"\n2. Loading signals from {lookback_date.strftime('%Y-%m-%d')} to {process_date_str}...")

    current_date = lookback_date
    total_loaded = 0

    while current_date <= process_date:
        date_str = current_date.strftime('%Y-%m-%d')

        try:
            rows = read_csv('process_5_signals', date=date_str, validate=False)

            for row in rows:
                article_id = row.get('article_id', '')
                generator_id = row.get('generator_id', '')
                predicted_direction = row.get('predicted_direction', '')

                if not article_id or not generator_id:
                    continue

                # Skip neutral signals - we only care about bullish/bearish
                if predicted_direction == 'neutral':
                    continue

                key = (article_id, generator_id, date_str)

                signals[key] = {
                    'article_id': article_id,
                    'generator_id': generator_id,
                    'currency': row.get('currency', ''),
                    'article_download_date': date_str,
                    'predicted_direction': predicted_direction,
                    'predicted_magnitude': row.get('predicted_magnitude'),
                    'confidence': float(row.get('confidence', 0)),
                    'signal': float(row.get('signal', 0)),
                    'reasoning': row.get('reasoning', ''),
                    'estimator_id': row.get('estimator_id', ''),
                    'valid_to_date': row.get('valid_to_date', '')
                }
                total_loaded += 1

        except FileNotFoundError:
            pass  # Skip missing dates

        current_date += timedelta(days=1)

    print(f"   ✓ Loaded {total_loaded} signals (excluding neutral)")
    return signals


def calculate_index_movement(currency, start_date_str, end_date_str, indices):
    """
    Calculate currency index movement from start_date to end_date

    Returns: dict with start_index, end_index, start_30d_max_diff, actual_diff
    """
    start_key = (currency, start_date_str)
    end_key = (currency, end_date_str)

    if start_key not in indices or end_key not in indices:
        return None

    start_data = indices[start_key]
    end_data = indices[end_key]

    start_index = start_data['index']
    end_index = end_data['index']
    start_30d_max_diff = start_data['30d_max_diff']

    # Calculate simple difference (not percentage)
    actual_diff = end_index - start_index

    return {
        'start_index': round(start_index, 4),
        'end_index': round(end_index, 4),
        'start_30d_max_diff': round(start_30d_max_diff, 4),
        'actual_diff': round(actual_diff, 4)
    }


def check_realization(estimated_diff, actual_diff):
    """
    Determine if a signal has been realized based on estimated vs actual movement

    Returns: bool

    Logic:
    - If estimated_diff is negative: realized if actual_diff < estimated_diff (more negative)
    - If estimated_diff is positive: realized if actual_diff > estimated_diff (more positive)
    - If estimated_diff is zero: not realized
    """
    if estimated_diff < 0:
        # Bearish signal - realized if actual movement is more negative than estimated
        return actual_diff < estimated_diff
    elif estimated_diff > 0:
        # Bullish signal - realized if actual movement is more positive than estimated
        return actual_diff > estimated_diff
    else:
        # Zero signal - not realized
        return False


def main(date_str=None):
    """Main function - signal realization checker"""

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    logger = PipelineLogger('step6', 'Check Signal Realization')
    logger.start()

    try:
        print("="*60)
        print("Signal Realization Checker - CSV Output")
        print("="*60)
        print(f"\nProcessing date: {date_str}")

        # Calculate date range for loading indices (30 days back)
        process_date = datetime.fromisoformat(date_str)
        lookback_date = process_date - timedelta(days=30)
        lookback_str = lookback_date.strftime('%Y-%m-%d')

        # Load currency indices for the full window
        print(f"\n{'='*60}")
        print("Loading Currency Indices")
        print(f"{'='*60}")
        print(f"   Loading indices from {lookback_str} to {date_str}...")

        indices = load_currency_indices_multi_date(lookback_str, date_str)
        print(f"   ✓ Loaded {len(indices)} index data points")
        logger.add_count('indices_loaded', len(indices))

        # Load signals (from past 30 days, excluding neutral, includes horizon data)
        print(f"\n1. Loading signals from {lookback_str} to {date_str}...")
        signals = load_signals_from_all_dates(date_str)
        logger.add_count('signals_loaded', len(signals))

        # Process signals and check realization
        print(f"\n{'='*60}")
        print("Processing Signals")
        print(f"{'='*60}")

        csv_rows = []

        for (article_id, generator_id, signal_date), signal in signals.items():
            # Get horizon data from signal (now included in Process 5 output)
            estimator_id = signal.get('estimator_id', 'unknown')
            valid_to_date_str = signal.get('valid_to_date', '')

            if not valid_to_date_str:
                continue  # Signal missing horizon data

            # Check if signal is still valid for the processing date
            valid_to_date = datetime.fromisoformat(valid_to_date_str)
            process_date = datetime.fromisoformat(date_str)
            if valid_to_date < process_date:
                continue  # Signal has expired

            article_download_date = signal['article_download_date']
            currency = signal['currency']

            # Get index movement from download_date to process_date
            movement = calculate_index_movement(
                currency,
                article_download_date,
                date_str,
                indices
            )

            if not movement:
                continue  # Can't calculate movement

            # Calculate estimated_diff = signal × start_30d_max_diff
            estimated_diff = round(signal['signal'] * movement['start_30d_max_diff'], 4)

            # Check realization
            realized = check_realization(estimated_diff, movement['actual_diff'])

            # Build CSV row (signal includes horizon data from Process 5)
            # Column order: date, article_id, currency, article_download_date, estimator_id, generator_id, event_id, ...
            csv_rows.append({
                'date': date_str,
                'article_id': signal.get('article_id', ''),
                'currency': currency,
                'article_download_date': article_download_date,
                'estimator_id': estimator_id,
                'generator_id': generator_id,
                'event_id': signal.get('event_id', 'none'),  # Get from signal or default to 'none'
                'valid_to_date': valid_to_date_str,
                'signal': signal['signal'],
                'start_30d_max_diff': movement['start_30d_max_diff'],
                'estimated_diff': estimated_diff,
                'start_index': movement['start_index'],
                'index': movement['end_index'],
                'actual_diff': movement['actual_diff'],
                'realized': realized
            })

        print(f"   ✓ Joined {len(csv_rows)} records")
        logger.add_count('joined_records', len(csv_rows))

        # Write to CSV
        print(f"\n3. Saving to CSV...")
        if csv_rows:
            csv_path = write_csv(csv_rows, 'process_6_realization', date=date_str)
            print(f"   ✓ Saved {len(csv_rows)} records to {csv_path}")
            logger.add_info('output_file', str(csv_path))
        else:
            print(f"   ⚠ No records to save")
            logger.warning("No realization records generated")

        # Print summary statistics
        print(f"\n{'='*60}")
        print("Summary Statistics")
        print(f"{'='*60}")

        realized_count = sum(1 for row in csv_rows if row['realized'])
        unrealized_count = len(csv_rows) - realized_count

        print(f"Total records: {len(csv_rows)}")
        if csv_rows:
            print(f"\nRealization Status:")
            realized_pct = (realized_count / len(csv_rows) * 100)
            unrealized_pct = (unrealized_count / len(csv_rows) * 100)
            print(f"  Realized:   {realized_count:4d} ({realized_pct:5.1f}%)")
            print(f"  Unrealized: {unrealized_count:4d} ({unrealized_pct:5.1f}%)")

        logger.add_count('realized', realized_count)
        logger.add_count('unrealized', unrealized_count)

        logger.success()

    except Exception as e:
        logger.error(f"Failed to check realization: {e}")
        logger.fail()
        raise
    finally:
        logger.finish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check signal realization')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD), defaults to today')
    args = parser.parse_args()

    main(date_str=args.date)
