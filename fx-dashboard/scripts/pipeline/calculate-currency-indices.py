#!/usr/bin/env python3
"""
Currency Index Calculator - Percent Change Method

Generates synthetic currency strength indices using percent changes from previous day.
This properly isolates each currency's movement and gives equal weight to all pairs
regardless of magnitude.

Method: For each currency, calculate percent changes of all pairs (vs previous day),
average them, and apply to previous index value.

Example for USD on 2026-03-08:
1. Load previous rates (2026-03-07): EUR/USD=1.08, JPY/USD=0.0067, GBP/USD=0.85
2. Load today's rates (2026-03-08): EUR/USD=1.085, JPY/USD=0.0066, GBP/USD=0.853
3. Calculate percent changes:
   - EUR/USD: (1.085 / 1.08 - 1) × 100 = +0.46%
   - JPY/USD: (0.0066 / 0.0067 - 1) × 100 = -1.49%
   - GBP/USD: (0.853 / 0.85 - 1) × 100 = +0.35%
4. Average: (+0.46 - 1.49 + 0.35) / 3 = -0.23%
5. Apply to previous index: 100 × (1 - 0.0023) = 99.77

If exchange rates are identical between two dates, all percent changes = 0%,
so the index remains unchanged (as expected).

Output: CSV with columns: date, currency, index
"""

import sys
import argparse
from datetime import datetime, timedelta

sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.config_loader import get_currencies
from utilities.pipeline_logger import PipelineLogger
from utilities.csv_helper import read_csv, write_csv, csv_exists, get_previous_date

CURRENCIES = get_currencies()
BASE_DATE = "2026-02-24"  # First date in our system


def get_rate_for_pair(base_currency, quote_currency, rates_rows):
    """
    Get exchange rate for a specific currency pair from rates data.

    Parameters:
    - base_currency: Base currency (e.g., 'EUR')
    - quote_currency: Quote currency (e.g., 'USD')
    - rates_rows: List of dicts with keys: date, base_currency, quote_currency, rate

    Returns:
    - Rate as float, or None if not found
    """
    # First try to find exact match
    for row in rates_rows:
        if row['base_currency'] == base_currency and row['quote_currency'] == quote_currency:
            return float(row['rate'])

    # If not found, try inverse
    for row in rates_rows:
        if row['base_currency'] == quote_currency and row['quote_currency'] == base_currency:
            return 1.0 / float(row['rate'])

    return None


def calculate_currency_index(currency, today_rates, prev_rates, prev_index):
    """
    Calculate currency index using percent-change method.

    Parameters:
    - currency: Target currency (e.g., 'USD')
    - today_rates: Today's exchange rates (list of dicts)
    - prev_rates: Previous day's exchange rates (list of dicts)
    - prev_index: Previous day's index value (or 100.0 for base date)

    Returns:
    - Index value (float)
    """
    percent_changes = []

    # For each other currency, calculate percent change in OTHER/CURRENCY pair
    for other_currency in CURRENCIES:
        if other_currency == currency:
            continue

        # Get OTHER/CURRENCY rates (other currency in numerator, target in denominator)
        prev_rate = get_rate_for_pair(other_currency, currency, prev_rates)
        today_rate = get_rate_for_pair(other_currency, currency, today_rates)

        if prev_rate is None or today_rate is None:
            continue

        # Calculate percent change from PREVIOUS DAY (not base date)
        pct_change = ((today_rate / prev_rate) - 1) * 100
        percent_changes.append(pct_change)

    if not percent_changes:
        return None

    # Average all percent changes (equal weight)
    avg_change_pct = sum(percent_changes) / len(percent_changes)

    # Apply to previous index
    new_index = prev_index * (1 + avg_change_pct / 100)

    return new_index


def calculate_all_indices(date_str):
    """Calculate percent-change-based indices for all currencies for a specific date"""

    logger = PipelineLogger('step2', 'Calculate Currency Indices (Percent Change Method)')
    logger.start()

    try:
        print("="*60)
        print("Currency Index Calculator - Percent Change Method")
        print("="*60)
        print(f"\nProcessing date: {date_str}")

        # Read today's exchange rates from Process 1
        print(f"\n1. Loading exchange rates for {date_str}...")
        try:
            today_rates = read_csv('process_1_exchange_rates', date=date_str)
            print(f"   ✓ Loaded {len(today_rates)} exchange rates")
            logger.add_count('rates_loaded', len(today_rates))
        except FileNotFoundError:
            print(f"   ✗ No exchange rate data found for {date_str}")
            logger.error(f"Missing exchange rate data for {date_str}")
            logger.fail()
            return

        # Check if this IS the base date
        is_base_date = (date_str == BASE_DATE)

        # Get previous date
        prev_date = get_previous_date(date_str)

        # Load previous day's exchange rates (needed for percent change calculation)
        print(f"\n2. Loading previous day exchange rates...")
        prev_rates = None

        if is_base_date:
            print(f"   ℹ This is the base date - all indices will be set to 100")
            prev_rates = today_rates  # Use today's rates (no change on base date)
        else:
            if csv_exists('process_1_exchange_rates', date=prev_date):
                prev_rates = read_csv('process_1_exchange_rates', date=prev_date)
                print(f"   ✓ Loaded {len(prev_rates)} exchange rates from {prev_date}")
                logger.add_count('prev_rates_loaded', len(prev_rates))
            else:
                print(f"   ✗ Previous day rates not found for {prev_date}!")
                logger.error(f"Missing exchange rates for {prev_date}")
                logger.fail()
                return

        # Load previous day's indices (needed to apply percent changes)
        print(f"\n3. Loading previous day indices...")
        prev_indices = {}

        if is_base_date:
            # Base date: all start at 100
            for currency in CURRENCIES:
                prev_indices[currency] = 100.0
            print(f"   ℹ Base date - initializing all indices to 100")
        elif csv_exists('process_2_indices', date=prev_date):
            try:
                prev_rows = read_csv('process_2_indices', date=prev_date)
                # Build dict: currency -> index
                for row in prev_rows:
                    prev_indices[row['currency']] = float(row['index'])
                print(f"   ✓ Loaded previous indices from {prev_date}")
                logger.add_count('prev_indices_loaded', len(prev_indices))
            except Exception as e:
                print(f"   ⚠ Could not load previous indices: {e}")
                logger.warning(f"Could not load previous indices: {e}")
        else:
            print(f"   ⚠ No previous indices found - will use 100 as starting point")
            logger.warning(f"Missing previous indices for {prev_date}")
            # Default to 100 if no previous data
            for currency in CURRENCIES:
                prev_indices[currency] = 100.0

        # Calculate indices for all currencies
        print(f"\n4. Calculating indices for {len(CURRENCIES)} currencies...")
        results = []

        for currency in CURRENCIES:
            prev_index = prev_indices.get(currency, 100.0)

            if is_base_date:
                # Base date: set to 100
                index = 100.0
            else:
                # Calculate using percent change method
                index = calculate_currency_index(currency, today_rates, prev_rates, prev_index)

                if index is None:
                    print(f"   ⚠ Could not calculate index for {currency}")
                    logger.warning(f"Failed to calculate index for {currency}")
                    continue

            results.append({
                'date': date_str,
                'currency': currency,
                'index': round(index, 6)
            })

            # Calculate daily change for display
            daily_change_pct = ((index / prev_index) - 1) * 100 if not is_base_date else 0.0
            change_str = f"{daily_change_pct:+.2f}%" if not is_base_date else "BASE"
            print(f"   {currency}: {index:.4f} ({change_str})")

        if not results:
            print("   ✗ No indices calculated!")
            logger.error("Failed to calculate any indices")
            logger.fail()
            return

        logger.add_count('indices_calculated', len(results))

        # Calculate 30-day max diff for each currency
        print(f"\n5. Calculating 30-day max-min differences...")
        process_date = datetime.fromisoformat(date_str)
        lookback_date = process_date - timedelta(days=30)

        # Load all indices from past 30 days
        historical_indices = {}  # {currency: [index_values]}

        current_date = lookback_date
        while current_date <= process_date:
            check_date_str = current_date.strftime('%Y-%m-%d')
            try:
                historical_rows = read_csv('process_2_indices', date=check_date_str, validate=False)
                for row in historical_rows:
                    curr = row['currency']
                    idx_val = float(row['index'])
                    if curr not in historical_indices:
                        historical_indices[curr] = []
                    historical_indices[curr].append(idx_val)
            except FileNotFoundError:
                pass  # Date doesn't exist yet

            current_date += timedelta(days=1)

        # Calculate max-min diff for each currency and add to results
        for result in results:
            currency = result['currency']
            if currency in historical_indices and len(historical_indices[currency]) > 0:
                indices = historical_indices[currency]
                max_diff = max(indices) - min(indices)
                result['30d_max_diff'] = round(max_diff, 4)
            else:
                result['30d_max_diff'] = 0.0

        print(f"   ✓ Calculated 30-day ranges for {len(results)} currencies")

        # Write to CSV
        print(f"\n6. Saving indices to CSV...")
        csv_path = write_csv(results, 'process_2_indices', date=date_str)

        print(f"   ✓ Saved {len(results)} indices to {csv_path}")
        logger.add_info('output_file', str(csv_path))

        logger.success()

    except Exception as e:
        logger.error(f"Failed to calculate indices: {e}")
        logger.fail()
        raise
    finally:
        logger.finish()


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Calculate currency strength indices')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD), defaults to today')
    args = parser.parse_args()

    # Determine date
    date_str = args.date if args.date else datetime.now().strftime('%Y-%m-%d')

    calculate_all_indices(date_str)


if __name__ == '__main__':
    main()
