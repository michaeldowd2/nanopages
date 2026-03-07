#!/usr/bin/env python3
"""
Signal Realization Checker - Refactored

Joins horizon analysis and sentiment signals for all articles still within their validity window.
For a given processing date, includes articles from up to 30 days prior that have valid_to_date >= processing_date.

Process:
1. Load all horizon estimator outputs from past 30 days
2. Filter to records with valid_to_date >= current processing date (exclude expired articles)
3. Load sentiment generator outputs from past 30 days
4. Filter to exclude neutral signals (only bullish/bearish signals are included)
5. Join on article URL and date
6. Track article_download_date (when article was first seen)
7. Get starting index value (currency index on article_download_date)
8. Get current index value (currency index on processing_date)
9. Calculate % change from start to current
10. Compare predicted sentiment to actual movement to determine realization
11. Save all results with the current processing_date
"""

import json
import os
import glob
import sys
from datetime import datetime, timedelta

sys.path.append('/workspace/group/fx-portfolio/scripts')
from pipeline_logger import PipelineLogger

CURRENCIES = ["EUR", "USD", "GBP", "JPY", "CHF", "AUD", "CAD", "NOK", "SEK", "CNY", "MXN"]


def load_currency_index(currency):
    """Load currency index data"""
    index_file = f'/workspace/group/fx-portfolio/data/indices/{currency}_index.json'

    if not os.path.exists(index_file):
        return None

    with open(index_file, 'r') as f:
        data = json.load(f)
        # Convert to dict keyed by date for easy lookup
        return {item['date']: item for item in data['data']}


def load_horizon_analyses_in_window(process_date_str):
    """
    Load all horizon analyses from the past 30 days that are still valid
    (valid_to_date >= process_date)

    Returns: dict keyed by (url, estimator_id, article_download_date) -> horizon_data
    """
    analysis_dir = '/workspace/group/fx-portfolio/data/article-analysis'
    process_date = datetime.fromisoformat(process_date_str)
    lookback_date = process_date - timedelta(days=30)

    horizon_analyses = {}

    if not os.path.exists(analysis_dir):
        return horizon_analyses

    print(f"\nLoading horizon analyses from {lookback_date.strftime('%Y-%m-%d')} to {process_date_str}...")

    for filename in sorted(os.listdir(analysis_dir)):
        if not filename.endswith('.json'):
            continue

        # Extract date from filename
        try:
            file_date_str = filename.replace('.json', '')
            file_date = datetime.fromisoformat(file_date_str)
        except:
            continue  # Skip non-date files

        # Skip files outside lookback window
        if file_date < lookback_date or file_date > process_date:
            continue

        filepath = os.path.join(analysis_dir, filename)

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            if 'analyses' not in data:
                continue

            article_download_date = data.get('date', file_date_str)
            estimator_id = data.get('estimator_id', '')

            for analysis in data.get('analyses', []):
                valid_to_date_str = analysis.get('valid_to_date', '')

                if not valid_to_date_str:
                    continue

                # Check if still valid for the processing date
                valid_to_date = datetime.fromisoformat(valid_to_date_str)
                if valid_to_date < process_date:
                    continue  # Expired

                url = analysis.get('url', '')
                key = (url, estimator_id, article_download_date)

                # Store with article download date
                horizon_analyses[key] = {
                    'url': url,
                    'estimator_id': estimator_id,
                    'currency': analysis.get('currency', ''),
                    'article_download_date': article_download_date,
                    'time_horizon': analysis.get('time_horizon', ''),
                    'horizon_days': analysis.get('horizon_days', 0),
                    'valid_to_date': valid_to_date_str,
                    'horizon_confidence': analysis.get('confidence', 0)
                }

        except Exception as e:
            print(f"  Error reading {filepath}: {e}")

    print(f"  ✓ Loaded {len(horizon_analyses)} valid horizon analyses")
    return horizon_analyses


def load_signals_from_all_dates(process_date_str):
    """
    Load all signals from the past 30 days

    Returns: dict keyed by (url, generator_id, signal_download_date) -> signal_data
    """
    process_date = datetime.fromisoformat(process_date_str)
    lookback_date = process_date - timedelta(days=30)

    signals = {}

    print(f"\nLoading signals from {lookback_date.strftime('%Y-%m-%d')} to {process_date_str}...")

    for currency in CURRENCIES:
        signal_dir = f'/workspace/group/fx-portfolio/data/signals/{currency}'

        if not os.path.exists(signal_dir):
            continue

        for filename in os.listdir(signal_dir):
            if not filename.endswith('.json'):
                continue

            # Extract date from filename
            try:
                file_date_str = filename.replace('.json', '')
                file_date = datetime.fromisoformat(file_date_str)
            except:
                continue

            # Skip files outside lookback window
            if file_date < lookback_date or file_date > process_date:
                continue

            filepath = os.path.join(signal_dir, filename)

            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)

                signal_download_date = data.get('date', file_date_str)

                for signal in data.get('signals', []):
                    url = signal.get('article_url', '')
                    generator_id = signal.get('generator_id', '')
                    predicted_direction = signal.get('predicted_direction', '')

                    if not url or not generator_id:
                        continue

                    # Skip neutral signals - we only care about bullish/bearish
                    if predicted_direction == 'neutral':
                        continue

                    key = (url, generator_id, signal_download_date)

                    # Store with signal download date
                    signals[key] = {
                        'url': url,
                        'generator_id': generator_id,
                        'currency': data.get('currency', ''),
                        'article_download_date': signal_download_date,
                        'predicted_direction': signal.get('predicted_direction', ''),
                        'predicted_magnitude': signal.get('predicted_magnitude', ''),
                        'confidence': signal.get('confidence', 0),
                        'article_title': signal.get('article_title', ''),
                        'reasoning': signal.get('reasoning', '')
                    }

            except Exception as e:
                print(f"  Error reading {filepath}: {e}")

    print(f"  ✓ Loaded {len(signals)} signals")
    return signals


def calculate_index_movement(currency, start_date_str, end_date_str, index_data):
    """
    Calculate currency index movement from start_date to end_date

    Returns: {
        'start_index': float,
        'end_index': float,
        'pct_change': float,
        'direction': str  # bullish/bearish/neutral
    }
    """
    if not index_data:
        return None

    if start_date_str not in index_data or end_date_str not in index_data:
        return None

    start_index = index_data[start_date_str]['index']
    end_index = index_data[end_date_str]['index']

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
    if predicted_magnitude and predicted_magnitude != 'unclear':
        try:
            # Extract number from string like "0.5%" or "small"
            if '%' in predicted_magnitude:
                predicted_mag = float(predicted_magnitude.replace('%', '').replace('+', '').replace('-', ''))
                actual_mag = abs(actual_pct_change)
                # Actual should be at least 50% of predicted
                magnitude_sufficient = actual_mag >= (predicted_mag * 0.5)
        except:
            pass  # If parsing fails, ignore magnitude check

    # Determine status
    if direction_matches and magnitude_sufficient:
        return True, 'realized'
    elif direction_matches and not magnitude_sufficient:
        return False, 'partially_realized'
    elif actual_direction == 'neutral':
        return False, 'unrealized'
    else:
        return False, 'contradicted'


def main():
    """Main function - refactored signal realization"""
    import argparse

    parser = argparse.ArgumentParser(description='Check signal realization')
    parser.add_argument('--date', help='Date to process (YYYY-MM-DD). Required.')
    args = parser.parse_args()

    if not args.date:
        print("❌ Error: --date parameter is required")
        print("   Usage: python3 check-signal-realization.py --date 2026-02-24")
        sys.exit(1)

    process_date_str = args.date

    logger = PipelineLogger('step6', 'Check Signal Realization')
    logger.start()

    try:
        print("="*60)
        print("Signal Realization Checker - Refactored")
        print("="*60)
        print(f"Processing date: {process_date_str}")

        # Load currency indices
        print(f"\n{'='*60}")
        print("Loading Currency Indices")
        print(f"{'='*60}")

        indices = {}
        for currency in CURRENCIES:
            index_data = load_currency_index(currency)
            if index_data:
                indices[currency] = index_data
                print(f"  ✓ {currency}: {len(index_data)} days")
            else:
                print(f"  ✗ {currency}: No index data")

        # Load horizon analyses (valid for this date)
        horizon_analyses = load_horizon_analyses_in_window(process_date_str)

        # Load signals (from past 30 days)
        signals = load_signals_from_all_dates(process_date_str)

        # Join horizon and signals on (URL, estimator_id, generator_id)
        print(f"\n{'='*60}")
        print("Joining Horizons and Signals")
        print(f"{'='*60}")

        joined_records = []

        for (url, generator_id, signal_date), signal in signals.items():
            # Try to find matching horizon analysis
            # We need to match on URL and date (the date both were generated)
            matching_horizons = [
                (key, horizon) for key, horizon in horizon_analyses.items()
                if key[0] == url and key[2] == signal_date  # Match on URL and date
            ]

            if not matching_horizons:
                continue  # No horizon data for this signal

            # Use the first matching horizon (there should only be one per URL/estimator/date)
            (horizon_url, estimator_id, horizon_date), horizon = matching_horizons[0]

            # Verify currency matches
            if signal['currency'] != horizon['currency']:
                continue

            # Use the article_download_date from the signal (they should match)
            article_download_date = signal['article_download_date']
            currency = signal['currency']

            # Get index movement from download_date to process_date
            if currency not in indices:
                continue

            movement = calculate_index_movement(
                currency,
                article_download_date,
                process_date_str,
                indices[currency]
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

            # Calculate magnitude-weighted signal
            magnitude_multipliers = {
                'small': 0.4,
                'medium': 0.7,
                'large': 1.4
            }
            magnitude = signal['predicted_magnitude']
            confidence = signal['confidence']
            magnitude_weight = magnitude_multipliers.get(magnitude, 0.7)

            # Signal = confidence * magnitude_weight
            signal_value = confidence * magnitude_weight

            # Build joined record
            record = {
                'process_date': process_date_str,
                'article_download_date': article_download_date,
                'url': url,
                'currency': currency,
                'title': signal['article_title'],
                'generator_id': generator_id,
                'estimator_id': estimator_id,
                'time_horizon': horizon['time_horizon'],
                'horizon_days': horizon['horizon_days'],
                'valid_to_date': horizon['valid_to_date'],
                'predicted_direction': signal['predicted_direction'],
                'predicted_magnitude': signal['predicted_magnitude'],
                'confidence': signal['confidence'],
                'signal': signal_value,
                'horizon_confidence': horizon['horizon_confidence'],
                'start_index': movement['start_index'],
                'end_index': movement['end_index'],
                'actual_pct_change': movement['pct_change'],
                'actual_direction': movement['direction'],
                'realized': realized,
                'realization_status': status
            }

            joined_records.append(record)

        print(f"  ✓ Joined {len(joined_records)} records")

        # Save to output file for this process date
        print(f"\n{'='*60}")
        print("Saving Results")
        print(f"{'='*60}")

        output_dir = '/workspace/group/fx-portfolio/data/signal-realization'
        os.makedirs(output_dir, exist_ok=True)

        output_file = f'{output_dir}/{process_date_str}.json'

        output_data = {
            'process_date': process_date_str,
            'generated_at': datetime.now().isoformat(),
            'total_records': len(joined_records),
            'records': joined_records
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"  ✓ Saved {len(joined_records)} records to {output_file}")

        # Print summary statistics
        print(f"\n{'='*60}")
        print("Summary Statistics")
        print(f"{'='*60}")

        status_counts = {}
        for record in joined_records:
            status = record['realization_status']
            status_counts[status] = status_counts.get(status, 0) + 1

        print(f"Total records: {len(joined_records)}")
        print(f"\nRealization Status:")
        for status, count in sorted(status_counts.items()):
            pct = (count / len(joined_records) * 100) if joined_records else 0
            print(f"  {status:20s}: {count:4d} ({pct:5.1f}%)")

        logger.add_count('total_records', len(joined_records))
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
    main()
