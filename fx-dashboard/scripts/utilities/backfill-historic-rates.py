#!/usr/bin/env python3
"""
Backfill Historic Exchange Rates

Downloads historical exchange rate data for a date range.
Uses Frankfurter API (free, no signup) as primary source.

Use cases:
- Fill gaps in historical data
- Correct stale data from previous runs
- Initialize new date ranges
- Recover from data loss

Example:
    python3 backfill-historic-rates.py --start 2026-03-01 --end 2026-03-12
    python3 backfill-historic-rates.py --date 2026-03-12  # Single date
"""

import sys
import argparse
from datetime import datetime, timedelta
import urllib.request
import json
import time

# Add utilities to path
sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.config_loader import get_currencies
from utilities.csv_helper import write_csv

CURRENCIES = get_currencies()

# Data sources (in priority order)
DATA_SOURCES = [
    {
        'name': 'Frankfurter',
        'url_pattern': 'https://api.frankfurter.dev/v1/{date}?base=EUR',
        'parse': lambda data: data.get('rates', {}),
        'get_date': lambda data: data.get('date')
    },
    {
        'name': 'GitHub Currency API (date-specific)',
        'url_pattern': 'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/eur.json',
        'parse': lambda data: data.get('eur', {}),
        'get_date': lambda data: data.get('date')
    },
    {
        'name': 'GitHub Currency API (fallback)',
        'url_pattern': 'https://{date}.currency-api.pages.dev/v1/currencies/eur.json',
        'parse': lambda data: data.get('eur', {}),
        'get_date': lambda data: data.get('date')
    }
]


def fetch_rates_for_date(date_str, source_index=0):
    """
    Fetch EUR-based rates for a specific date

    Args:
        date_str: Date in YYYY-MM-DD format
        source_index: Which data source to try (0=Frankfurter, 1=GitHub primary, 2=GitHub fallback)

    Returns:
        dict: {currency: rate} or None if failed
    """
    if source_index >= len(DATA_SOURCES):
        return None, None

    source = DATA_SOURCES[source_index]
    url = source['url_pattern'].format(date=date_str)

    try:
        print(f"   Trying {source['name']}...", end=' ')
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())

        rates_data = source['parse'](data)
        api_date = source['get_date'](data)

        if not rates_data:
            print("✗ No data")
            return fetch_rates_for_date(date_str, source_index + 1)

        # Normalize to uppercase keys
        normalized_rates = {'EUR': 1.0}
        for currency_code, rate in rates_data.items():
            currency_upper = currency_code.upper()
            if currency_upper in CURRENCIES:
                normalized_rates[currency_upper] = float(rate)

        print(f"✓ ({len(normalized_rates)} currencies)")
        return normalized_rates, source['name']

    except Exception as e:
        print(f"✗ {e}")
        # Try next source
        return fetch_rates_for_date(date_str, source_index + 1)


def calculate_all_pairs(eur_rates):
    """
    Calculate all currency pair rates from EUR-based rates

    Returns: Dict[str, Dict[str, float]]
    """
    all_pairs = {}

    for base in CURRENCIES:
        all_pairs[base] = {}

        for quote in CURRENCIES:
            if base == quote:
                all_pairs[base][quote] = 1.0
            else:
                eur_base = eur_rates.get(base, 1.0)
                eur_quote = eur_rates.get(quote, 1.0)
                rate = eur_quote / eur_base
                all_pairs[base][quote] = round(rate, 6)

    return all_pairs


def save_rates_csv(all_pairs, date_str, overwrite=False):
    """Save exchange rates to CSV file"""
    rows = []
    for base_currency, quote_rates in all_pairs.items():
        for quote_currency, rate in quote_rates.items():
            rows.append({
                'date': date_str,
                'base_currency': base_currency,
                'quote_currency': quote_currency,
                'rate': rate
            })

    # Check if file exists
    from pathlib import Path
    csv_path = Path(f'/workspace/group/fx-portfolio/data/prices/{date_str}.csv')

    if csv_path.exists() and not overwrite:
        print(f"   ⚠️  File exists (use --overwrite to replace)")
        return None

    # Write to CSV
    csv_path = write_csv(rows, 'process_1_exchange_rates', date=date_str)
    print(f"   ✓ Saved: {csv_path} ({len(rows)} rows)")

    return csv_path


def generate_date_range(start_date, end_date):
    """Generate list of dates between start and end (inclusive)"""
    current = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    dates = []
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    return dates


def main():
    parser = argparse.ArgumentParser(
        description='Backfill historical exchange rate data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download single date
  python3 backfill-historic-rates.py --date 2026-03-12

  # Download date range
  python3 backfill-historic-rates.py --start 2026-03-01 --end 2026-03-12

  # Overwrite existing data
  python3 backfill-historic-rates.py --date 2026-03-12 --overwrite

  # Skip weekends (forex markets closed)
  python3 backfill-historic-rates.py --start 2026-03-01 --end 2026-03-12 --skip-weekends
        """
    )

    parser.add_argument('--date', type=str, help='Single date to download (YYYY-MM-DD)')
    parser.add_argument('--start', type=str, help='Start date for range (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date for range (YYYY-MM-DD)')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files')
    parser.add_argument('--skip-weekends', action='store_true', help='Skip Saturday/Sunday')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests (seconds)')

    args = parser.parse_args()

    # Determine dates to process
    if args.date:
        dates = [args.date]
    elif args.start and args.end:
        dates = generate_date_range(args.start, args.end)
    else:
        parser.error("Specify --date for single date or --start/--end for range")

    # Filter weekends if requested
    if args.skip_weekends:
        dates = [d for d in dates if datetime.strptime(d, '%Y-%m-%d').weekday() < 5]

    print("=" * 60)
    print("Backfill Historic Exchange Rates")
    print("=" * 60)
    print(f"Dates to process: {len(dates)}")
    print(f"Currencies: {len(CURRENCIES)}")
    print(f"Overwrite existing: {args.overwrite}")
    print()

    # Process each date
    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, date_str in enumerate(dates, 1):
        print(f"[{i}/{len(dates)}] {date_str}")

        # Fetch rates
        eur_rates, source = fetch_rates_for_date(date_str)

        if not eur_rates:
            print(f"   ✗ Failed: All data sources exhausted")
            fail_count += 1
            continue

        print(f"   Source: {source}")

        # Calculate all pairs
        all_pairs = calculate_all_pairs(eur_rates)

        # Save to CSV
        result = save_rates_csv(all_pairs, date_str, overwrite=args.overwrite)

        if result:
            success_count += 1
        else:
            skip_count += 1

        # Rate limiting
        if i < len(dates):
            time.sleep(args.delay)

        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✓ Downloaded: {success_count}")
    print(f"⚠️  Skipped: {skip_count}")
    print(f"✗ Failed: {fail_count}")
    print("=" * 60)

    if fail_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
