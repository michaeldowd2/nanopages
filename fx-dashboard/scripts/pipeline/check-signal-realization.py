#!/usr/bin/env python3
"""
Step 6: Signal Realization Checker

Joins horizon analysis and sentiment signals for all articles still within their validity window.
For a given processing date, includes articles from up to 30 days prior that have valid_to_date >= processing_date.

Reads from CSV outputs of Processes 2, 4, and 5. Writes to Process 6 CSV output.

Input:
- data/indices/{date}.csv (from Process 2)
- data/article-analysis/{date}.csv (from Process 4, past 30 days)
- data/signals/{date}.csv (from Process 5, past 30 days)

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
    Load currency indices for multiple dates

    Returns: dict keyed by (currency, date) -> index_value
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
                indices[(currency, date_str)] = index_value
        except FileNotFoundError:
            pass  # Skip missing dates

        current_date += timedelta(days=1)

    return indices


def load_horizon_analyses_in_window(process_date_str):
    """
    Load all horizon analyses from the past 30 days that are still valid
    (valid_to_date >= process_date)

    Returns: dict keyed by (url, estimator_id, article_download_date) -> horizon_data
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

                url = row.get('url', '')
                estimator_id = row.get('estimator_id', '')
                key = (url, estimator_id, date_str)

                horizon_analyses[key] = {
                    'url': url,
                    'estimator_id': estimator_id,
                    'currency': row.get('currency', ''),
                    'title': row.get('title', ''),
                    'source': row.get('source', ''),
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

    Returns: dict keyed by (url, generator_id, signal_download_date) -> signal_data
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
                url = row.get('url', '')
                generator_id = row.get('generator_id', '')
                predicted_direction = row.get('predicted_direction', '')

                if not url or not generator_id:
                    continue

                # Skip neutral signals - we only care about bullish/bearish
                if predicted_direction == 'neutral':
                    continue

                key = (url, generator_id, date_str)

                signals[key] = {
                    'url': url,
                    'generator_id': generator_id,
                    'currency': row.get('currency', ''),
                    'article_download_date': date_str,
                    'title': row.get('title', ''),
                    'source': row.get('source', ''),
                    'predicted_direction': predicted_direction,
                    'predicted_magnitude': row.get('predicted_magnitude'),
                    'confidence': float(row.get('confidence', 0)),
                    'signal': float(row.get('signal', 0)),  # Load signal from Process 5
                    'reasoning': row.get('reasoning', '')
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

    Returns: dict with start_index, end_index, pct_change, direction
    """
    start_key = (currency, start_date_str)
    end_key = (currency, end_date_str)

    if start_key not in indices or end_key not in indices:
        return None

    start_index = indices[start_key]
    end_index = indices[end_key]

    # Calculate percentage change
    pct_change = ((end_index - start_index) / start_index) * 100

    # Determine direction (using 0.1% threshold)
    if pct_change > 0.1:
        direction = "bullish"
    elif pct_change < -0.1:
        direction = "bearish"
    else:
        direction = "neutral"

    return {
        'start_index': round(start_index, 4),
        'end_index': round(end_index, 4),
        'pct_change': round(pct_change, 2),
        'direction': direction
    }


def check_realization(predicted_direction, actual_direction, predicted_magnitude, actual_pct_change):
    """
    Determine if a signal has been realized

    Returns: (realized: bool, status: str)
    """
    # Check direction match
    direction_matches = (predicted_direction == actual_direction)

    # Check magnitude if specified
    magnitude_sufficient = True
    if predicted_magnitude and predicted_magnitude not in ['unclear', None]:
        try:
            # For magnitude keywords (small/medium/large), just check direction
            # We could add thresholds here if needed
            pass
        except:
            pass

    # Determine status
    if direction_matches and magnitude_sufficient:
        return True, 'realized'
    elif direction_matches and not magnitude_sufficient:
        return False, 'partially_realized'
    elif actual_direction == 'neutral':
        return False, 'unrealized'
    else:
        return False, 'contradicted'


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

        # Load horizon analyses (valid for this date)
        horizon_analyses = load_horizon_analyses_in_window(date_str)
        logger.add_count('horizons_loaded', len(horizon_analyses))

        # Load signals (from past 30 days, excluding neutral)
        signals = load_signals_from_all_dates(date_str)
        logger.add_count('signals_loaded', len(signals))

        # Join horizon and signals
        print(f"\n{'='*60}")
        print("Joining Horizons and Signals")
        print(f"{'='*60}")

        csv_rows = []

        for (url, generator_id, signal_date), signal in signals.items():
            # Try to find matching horizon analysis (same URL and date)
            matching_horizons = [
                (key, horizon) for key, horizon in horizon_analyses.items()
                if key[0] == url and key[2] == signal_date  # Match on URL and date
            ]

            if not matching_horizons:
                continue  # No horizon data for this signal

            # Use the first matching horizon
            (horizon_url, estimator_id, horizon_date), horizon = matching_horizons[0]

            # Verify currency matches
            if signal['currency'] != horizon['currency']:
                continue

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

            # Check realization
            realized, status = check_realization(
                signal['predicted_direction'],
                movement['direction'],
                signal['predicted_magnitude'],
                movement['pct_change']
            )

            # Build CSV row (signal is now loaded from Process 5)
            csv_rows.append({
                'date': date_str,
                'article_id': signal.get('article_id', ''),
                'source': signal['source'],
                'url': url,
                'currency': currency,
                'title': signal['title'],
                'article_download_date': article_download_date,
                'generator_id': generator_id,
                'estimator_id': estimator_id,
                'time_horizon': horizon['time_horizon'],
                'horizon_days': horizon['horizon_days'],
                'valid_to_date': horizon['valid_to_date'],
                'predicted_direction': signal['predicted_direction'],
                'predicted_magnitude': signal['predicted_magnitude'] if signal['predicted_magnitude'] else None,
                'confidence': signal['confidence'],
                'signal': signal['signal'],  # Simply use signal from Process 5
                'start_index': movement['start_index'],
                'end_index': movement['end_index'],
                'actual_pct_change': movement['pct_change'],
                'actual_direction': movement['direction'],
                'realized': realized,
                'realization_status': status
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

        status_counts = {}
        for row in csv_rows:
            status = row['realization_status']
            status_counts[status] = status_counts.get(status, 0) + 1

        print(f"Total records: {len(csv_rows)}")
        if csv_rows:
            print(f"\nRealization Status:")
            for status, count in sorted(status_counts.items()):
                pct = (count / len(csv_rows) * 100)
                print(f"  {status:20s}: {count:4d} ({pct:5.1f}%)")

        logger.add_count('realized', status_counts.get('realized', 0))
        logger.add_count('unrealized', status_counts.get('unrealized', 0))
        logger.add_count('contradicted', status_counts.get('contradicted', 0))

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
