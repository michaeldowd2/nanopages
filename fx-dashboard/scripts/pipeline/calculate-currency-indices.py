#!/usr/bin/env python3
"""
Currency Index Calculator - Enhanced Geometric Mean Method

Generates synthetic currency strength indices using geometric mean of all currency pairs.
This properly isolates each currency's movement independent of trading pairs.

Method: For each currency, calculate geometric mean of all pairs where that currency
is in the denominator. This cancels out individual currency effects, leaving only
the target currency's isolated movement.

Example for USD:
- Normalize all pairs so USD is denominator: EUR/USD, GBP/USD, JPY/USD, etc.
- Geometric mean = (EUR/USD × GBP/USD × JPY/USD × ...)^(1/n)
- Result: Isolated USD movement (EUR, GBP, JPY effects cancel out)
"""

import json
import os
from datetime import datetime, timedelta
import glob
import sys

sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.pipeline_logger import PipelineLogger

CURRENCIES = ["EUR", "USD", "GBP", "JPY", "CHF", "AUD", "CAD", "NOK", "SEK", "CNY", "MXN"]

def load_historical_prices(days=30):
    """Load historical FX prices with all pairs"""
    prices_by_date = {}

    # Find all price files
    price_files = glob.glob('/workspace/group/fx-portfolio/data/prices/fx-rates-*.json')

    for filepath in sorted(price_files)[-days:]:  # Last N days
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                date_str = filepath.split('fx-rates-')[1].replace('.json', '')
                prices_by_date[date_str] = data
        except Exception as e:
            print(f"Error loading {filepath}: {e}")

    return prices_by_date

def calculate_geometric_mean(values):
    """Calculate geometric mean of a list of values"""
    if not values or len(values) == 0:
        return None

    # Geometric mean = (v1 × v2 × ... × vn)^(1/n)
    product = 1.0
    for v in values:
        product *= v

    return product ** (1.0 / len(values))

def calculate_currency_index_geometric(currency, all_pairs, base_all_pairs=None):
    """
    Calculate geometric mean index for a currency

    Parameters:
    - currency: Target currency (e.g., 'USD')
    - all_pairs: Dict of all currency pairs for current date
    - base_all_pairs: Dict of all currency pairs for base date (for normalization)

    Returns:
    - Raw index if base_all_pairs is None
    - Normalized index (base=100) if base_all_pairs provided
    """
    if not all_pairs:
        return None

    rates = []
    pairs_used = []

    # Get all pairs with target currency
    for other_currency in CURRENCIES:
        if other_currency == currency:
            continue

        # We want currency in denominator (OTHER/CURRENCY format)
        # Check if we have CURRENCY → OTHER (need to invert)
        if currency in all_pairs and other_currency in all_pairs[currency]:
            # We have CURRENCY/OTHER, invert to get OTHER/CURRENCY
            rate = all_pairs[currency][other_currency]
            normalized_rate = 1.0 / rate  # OTHER/CURRENCY
            rates.append(normalized_rate)
            pairs_used.append({
                'pair': f'{other_currency}/{currency}',
                'original_rate': rate,
                'normalized_rate': normalized_rate,
                'inverted': True
            })

        # Check if we have OTHER → CURRENCY (already correct)
        elif other_currency in all_pairs and currency in all_pairs[other_currency]:
            # We have OTHER/CURRENCY, use directly
            rate = all_pairs[other_currency][currency]
            rates.append(rate)
            pairs_used.append({
                'pair': f'{other_currency}/{currency}',
                'original_rate': rate,
                'normalized_rate': rate,
                'inverted': False
            })

    if not rates:
        return None, []

    # Calculate geometric mean
    index = calculate_geometric_mean(rates)

    if index is None:
        return None, []

    # Normalize to base date if provided
    if base_all_pairs:
        base_index, _ = calculate_currency_index_geometric(currency, base_all_pairs, base_all_pairs=None)
        if base_index:
            index = (index / base_index) * 100

    return index, pairs_used

def calculate_all_indices(days=30):
    """Calculate geometric mean indices for all currencies"""

    logger = PipelineLogger('step2', 'Calculate Currency Indices (Geometric Mean)')
    logger.start()

    try:
        print("="*60)
        print("Currency Index Calculator - Geometric Mean Method")
        print("="*60)

        # Load historical prices
        print(f"\nLoading {days} days of historical prices...")
        prices_by_date = load_historical_prices(days)

        if not prices_by_date:
            print("❌ No historical price data found!")
            logger.error("No historical price data found")
            logger.fail()
            return

        print(f"✓ Loaded {len(prices_by_date)} days of data")
        logger.add_count('days_loaded', len(prices_by_date))

        # Find base date (oldest date with all_pairs structure)
        base_date = None
        for date_str in sorted(prices_by_date.keys()):
            if prices_by_date[date_str].get('all_pairs'):
                base_date = date_str
                break

        if not base_date:
            print("❌ No price files with all_pairs structure found!")
            logger.error("Missing all_pairs data structure in all files")
            logger.fail()
            return

        latest_date = max(prices_by_date.keys())

        print(f"Base date: {base_date}")
        print(f"Latest date: {latest_date}")

        logger.add_info('base_date', base_date)
        logger.add_info('latest_date', latest_date)

        # Get base date all_pairs for normalization
        base_all_pairs = prices_by_date[base_date].get('all_pairs', {})

        print(f"\nCalculating geometric mean indices for {len(CURRENCIES)} currencies...")

        # Calculate indices for all dates
        all_indices = {currency: {} for currency in CURRENCIES}

        for date_str in sorted(prices_by_date.keys()):
            current_all_pairs = prices_by_date[date_str].get('all_pairs', {})

            if not current_all_pairs:
                continue

            for currency in CURRENCIES:
                index, pairs_used = calculate_currency_index_geometric(
                    currency,
                    current_all_pairs,
                    base_all_pairs
                )

                if index is not None:
                    # Calculate previous day's index for daily change
                    prev_index = None
                    dates_list = sorted(all_indices[currency].keys())
                    if dates_list:
                        prev_date = dates_list[-1]
                        prev_index = all_indices[currency][prev_date]['index']

                    daily_change = None
                    if prev_index:
                        daily_change = ((index / prev_index) - 1) * 100

                    all_indices[currency][date_str] = {
                        'date': date_str,
                        'currency': currency,
                        'index': round(index, 4),
                        'prev_index': round(prev_index, 4) if prev_index else None,
                        'daily_change_pct': round(daily_change, 4) if daily_change else None,
                        'base_date': base_date,
                        'pairs_count': len(pairs_used),
                        'calculation_method': 'geometric_mean'
                    }

        # Save indices
        output_dir = '/workspace/group/fx-portfolio/data/indices'
        os.makedirs(output_dir, exist_ok=True)

        # Save per-currency index files
        for currency in CURRENCIES:
            if not all_indices[currency]:
                continue

            output_file = f'{output_dir}/{currency}_index.json'

            with open(output_file, 'w') as f:
                json.dump({
                    'currency': currency,
                    'calculation_method': 'geometric_mean',
                    'note': 'Index isolates currency movement using geometric mean of all pairs',
                    'base_date': base_date,
                    'data': list(all_indices[currency].values())
                }, f, indent=2)

            print(f"  ✓ {currency}: {len(all_indices[currency])} days")

        logger.add_count('currencies_calculated', len(CURRENCIES))
        logger.add_count('total_index_points', sum(len(v) for v in all_indices.values()))

        # Export for dashboard (CSV format)
        export_dir = '/workspace/group/fx-portfolio/data/exports'
        os.makedirs(export_dir, exist_ok=True)

        import csv
        with open(f'{export_dir}/step2_indices.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'date', 'currency', 'index', 'prev_index', 'daily_change_pct',
                'base_date', 'pairs_count', 'calculation_method'
            ])
            writer.writeheader()

            for currency in CURRENCIES:
                for date_str in sorted(all_indices[currency].keys()):
                    writer.writerow(all_indices[currency][date_str])

        logger.add_info('output_csv', f'{export_dir}/step2_indices.csv')

        # Export validation data (detailed calculation breakdown for latest date)
        validation_data = []
        latest_all_pairs = prices_by_date[latest_date].get('all_pairs', {})

        for currency in CURRENCIES:
            index, pairs_used = calculate_currency_index_geometric(
                currency,
                latest_all_pairs,
                base_all_pairs
            )

            validation_data.append({
                'currency': currency,
                'date': latest_date,
                'index': round(index, 4) if index else None,
                'pairs_used': pairs_used,
                'pairs_count': len(pairs_used),
                'geometric_mean_inputs': [p['normalized_rate'] for p in pairs_used]
            })

        with open(f'{export_dir}/step2_indices_validation.json', 'w') as f:
            json.dump(validation_data, f, indent=2)

        logger.add_info('output_validation', f'{export_dir}/step2_indices_validation.json')

        # Print summary for latest date
        print(f"\n{'='*60}")
        print(f"Latest Indices ({latest_date}):")
        print(f"{'='*60}")
        print(f"{'Currency':<10} {'Index':>10} {'Daily Δ%':>10} {'Pairs':>8}")
        print("-" * 60)

        for currency in CURRENCIES:
            if currency not in all_indices or latest_date not in all_indices[currency]:
                continue

            latest_data = all_indices[currency][latest_date]
            daily_change = latest_data.get('daily_change_pct', 0) or 0

            print(f"{currency:<10} {latest_data['index']:>10.4f} {daily_change:>9.2f}% {latest_data['pairs_count']:>8}")

        print(f"{'='*60}")
        print(f"✓ Indices saved to {output_dir}/")
        print(f"✓ CSV export: {export_dir}/step2_indices.csv")
        print(f"✓ Validation: {export_dir}/step2_indices_validation.json")
        print(f"{'='*60}")

        logger.success()

    except Exception as e:
        logger.error(f"Failed to calculate indices: {e}")
        logger.fail()
        raise
    finally:
        logger.finish()

if __name__ == '__main__':
    calculate_all_indices(days=30)
