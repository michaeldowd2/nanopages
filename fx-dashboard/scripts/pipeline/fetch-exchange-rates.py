#!/usr/bin/env python3
"""
Step 1: Fetch Exchange Rates (All Pairs)

Downloads exchange rates for all currency pairs (11x11 matrix).
Uses EUR as intermediary since most FX APIs provide EUR pairs.

For each pair X/Y, we calculate:
X/Y = (EUR/Y) / (EUR/X)

Example: USD/JPY = EUR/JPY ÷ EUR/USD

API Sources (in order):
1. GitHub Currency API (date-specific, avoids CDN cache)
2. Frankfurter API (fallback, free, no signup)

Built-in validation:
- Compares rates to previous day
- Auto-detects stale data
- Falls back to alternate source if needed

Output: CSV with columns: date, base_currency, quote_currency, rate
"""

import sys
import argparse
from datetime import datetime, timedelta
import urllib.request
import urllib.error
import json
from pathlib import Path

# Add utilities to path
sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.config_loader import get_currencies
from utilities.pipeline_logger import PipelineLogger
from utilities.csv_helper import write_csv, read_csv

CURRENCIES = get_currencies()


def fetch_github_api_rates(date_str):
    """
    Fetch EUR-based rates from GitHub Currency API (date-specific endpoint)

    Uses date in URL to bypass CDN cache and ensure fresh data.
    Format: @YYYY-MM-DD instead of @latest

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        tuple: (rates_dict, api_date) or (None, None) if failed
    """
    # Date-specific endpoints (bypasses CDN cache)
    primary_url = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date_str}/v1/currencies/eur.json"
    fallback_url = f"https://{date_str}.currency-api.pages.dev/v1/currencies/eur.json"

    # Try primary endpoint
    try:
        print(f"   Trying GitHub API (cdn.jsdelivr.net) for {date_str}...")
        with urllib.request.urlopen(primary_url, timeout=10) as response:
            data = json.loads(response.read().decode())

        if "eur" in data:
            print("   ✓ GitHub API primary successful")
            return data["eur"], data.get("date", date_str)
        else:
            raise Exception("Unexpected API response format")

    except Exception as e:
        print(f"   ⚠️  GitHub API primary failed: {e}")
        print(f"   Trying GitHub API fallback (currency-api.pages.dev)...")

        # Try fallback endpoint
        try:
            with urllib.request.urlopen(fallback_url, timeout=10) as response:
                data = json.loads(response.read().decode())

            if "eur" in data:
                print("   ✓ GitHub API fallback successful")
                return data["eur"], data.get("date", date_str)
            else:
                raise Exception("Unexpected API response format")

        except Exception as fallback_error:
            print(f"   ✗ GitHub API fallback also failed: {fallback_error}")
            return None, None


def fetch_frankfurter_rates(date_str):
    """
    Fetch EUR-based rates from Frankfurter API

    Frankfurter is a free, open-source API with no signup or API key required.
    - URL: https://frankfurter.dev/
    - Historical data: 1999 to present
    - No rate limits

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        tuple: (rates_dict, api_date) or (None, None) if failed
    """
    url = f"https://api.frankfurter.dev/v1/{date_str}?base=EUR"

    try:
        print(f"   Trying Frankfurter API for {date_str}...")
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())

        if "rates" in data:
            print("   ✓ Frankfurter API successful")
            return data["rates"], data.get("date", date_str)
        else:
            raise Exception("Unexpected API response format")

    except Exception as e:
        print(f"   ✗ Frankfurter API failed: {e}")
        return None, None


def normalize_rates(rates_data):
    """
    Normalize API rates to our format

    Converts to uppercase keys and filters to our currency list.
    Always includes EUR=1.0 as base.

    Returns:
        dict: {currency_code: rate}
    """
    normalized_rates = {"EUR": 1.0}

    for currency_code, rate in rates_data.items():
        currency_upper = currency_code.upper()
        if currency_upper in CURRENCIES:
            normalized_rates[currency_upper] = float(rate)

    return normalized_rates


def load_previous_day_rates(date_str):
    """
    Load exchange rates from previous day for comparison

    Args:
        date_str: Current date in YYYY-MM-DD format

    Returns:
        dict: {(base, quote): rate} or None if not available
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        prev_date = date_obj - timedelta(days=1)
        prev_date_str = prev_date.strftime('%Y-%m-%d')

        prev_rates = read_csv('1', date=prev_date_str, validate=False)

        # Build lookup dict
        lookup = {}
        for row in prev_rates:
            key = (row['base_currency'], row['quote_currency'])
            lookup[key] = float(row['rate'])

        return lookup

    except Exception as e:
        print(f"   ℹ️  No previous day data available ({e})")
        return None


def check_for_duplicates(eur_rates, date_str):
    """
    Check if current rates are identical to previous day (stale data detection)

    Args:
        eur_rates: Current EUR-based rates
        date_str: Current date

    Returns:
        bool: True if rates are fresh (different), False if stale (identical)
    """
    print("\n2. Checking for stale data...")

    # Load previous day rates
    prev_lookup = load_previous_day_rates(date_str)

    if not prev_lookup:
        print("   ℹ️  No previous data to compare - assuming fresh")
        return True

    # Calculate all pairs for comparison
    current_pairs = calculate_all_pairs(eur_rates)

    # Compare rates
    identical_count = 0
    total_pairs = 0

    for base in CURRENCIES:
        for quote in CURRENCIES:
            key = (base, quote)
            if key in prev_lookup:
                total_pairs += 1
                current_rate = current_pairs[base][quote]
                prev_rate = prev_lookup[key]

                # Check if essentially identical (within 0.0001)
                if abs(current_rate - prev_rate) < 0.0001:
                    identical_count += 1

    if total_pairs == 0:
        print("   ℹ️  No overlapping pairs - assuming fresh")
        return True

    identical_pct = (identical_count / total_pairs) * 100

    # Critical: >95% identical means stale data
    if identical_pct >= 95:
        print(f"   ⚠️  WARNING: {identical_pct:.1f}% rates unchanged - likely stale data")
        print(f"   Sample: EUR/USD = {eur_rates.get('USD', 0):.6f}")
        return False
    else:
        print(f"   ✓ Fresh data: {100-identical_pct:.1f}% rates changed from previous day")
        return True


def calculate_all_pairs(eur_rates):
    """
    Calculate all currency pair rates from EUR-based rates

    For pair BASE/QUOTE:
    BASE/QUOTE = (EUR/QUOTE) / (EUR/BASE)

    Example:
    USD/JPY = EUR/JPY ÷ EUR/USD = 182.44 ÷ 1.18 = 154.61

    This means 1 USD = 154.61 JPY

    Returns: Dict[str, Dict[str, float]]
        Format: {"USD": {"JPY": 154.61, "GBP": 0.74, ...}, ...}
    """
    all_pairs = {}

    for base in CURRENCIES:
        all_pairs[base] = {}

        for quote in CURRENCIES:
            if base == quote:
                # Same currency = 1.0
                all_pairs[base][quote] = 1.0
            else:
                # Calculate cross rate via EUR
                eur_base = eur_rates.get(base, 1.0)
                eur_quote = eur_rates.get(quote, 1.0)

                # BASE/QUOTE = (EUR/QUOTE) / (EUR/BASE)
                rate = eur_quote / eur_base
                all_pairs[base][quote] = round(rate, 6)

    return all_pairs


def save_rates_csv(all_pairs, date_str):
    """
    Save exchange rates to CSV file

    Schema: date, base_currency, quote_currency, rate
    """
    # Convert all_pairs dict to rows
    rows = []
    for base_currency, quote_rates in all_pairs.items():
        for quote_currency, rate in quote_rates.items():
            rows.append({
                'date': date_str,
                'base_currency': base_currency,
                'quote_currency': quote_currency,
                'rate': rate
            })

    # Write to CSV using helper
    csv_path = write_csv(rows, 'process_1_exchange_rates', date=date_str)

    print(f"✓ Saved exchange rates: {csv_path}")
    print(f"  Total rows: {len(rows)}")

    return csv_path


def print_sample_rates(all_pairs):
    """Print sample rates for verification"""
    print("\n" + "="*60)
    print("Sample Exchange Rates (All Pairs)")
    print("="*60)

    # Show a few interesting pairs
    sample_pairs = [
        ("USD", "JPY"),
        ("GBP", "USD"),
        ("EUR", "USD"),
        ("AUD", "CAD"),
        ("CHF", "NOK")
    ]

    for base, quote in sample_pairs:
        rate = all_pairs.get(base, {}).get(quote, 0)
        print(f"{base}/{quote}: {rate:.4f}  (1 {base} = {rate:.4f} {quote})")

    print("="*60)


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(description='Fetch exchange rates for all currency pairs')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD), defaults to today')
    args = parser.parse_args()

    # Determine date
    date_str = args.date if args.date else datetime.now().strftime('%Y-%m-%d')

    logger = PipelineLogger('step1', 'Fetch Exchange Rates (All Pairs)')
    logger.start()

    try:
        print(f"\nProcessing date: {date_str}")
        print(f"Currencies: {len(CURRENCIES)}")
        print(f"Total pairs: {len(CURRENCIES)} × {len(CURRENCIES)} = {len(CURRENCIES)**2}")

        logger.add_count('currencies', len(CURRENCIES))
        logger.add_count('total_pairs', len(CURRENCIES) ** 2)

        # Step 1: Fetch EUR-based rates from GitHub API (date-specific)
        print("\n1. Fetching EUR-based rates from GitHub Currency API...")
        rates_data, api_date = fetch_github_api_rates(date_str)

        if rates_data:
            eur_rates = normalize_rates(rates_data)
            print(f"   ✓ Got rates for {len(eur_rates)} currencies (API date: {api_date})")
            data_source = "github-currency-api"
        else:
            eur_rates = None
            data_source = None

        # Step 2: Check for duplicate rates (stale data)
        if eur_rates and not check_for_duplicates(eur_rates, date_str):
            print("\n   🔄 Stale data detected, trying Frankfurter API...")

            # Try Frankfurter as fallback
            rates_data, api_date = fetch_frankfurter_rates(date_str)

            if rates_data:
                eur_rates_fallback = normalize_rates(rates_data)
                print(f"   ✓ Got rates from Frankfurter ({len(eur_rates_fallback)} currencies)")

                # Check if Frankfurter data is also stale
                if not check_for_duplicates(eur_rates_fallback, date_str):
                    raise Exception(
                        "Both GitHub and Frankfurter APIs returned stale data. "
                        "This may indicate markets are closed (weekend) or no rate changes occurred."
                    )

                # Use Frankfurter data
                eur_rates = eur_rates_fallback
                data_source = "frankfurter-api"
                logger.add_info('fallback_reason', 'github_api_stale_data')
            else:
                raise Exception("Frankfurter fallback also failed")

        if not eur_rates:
            raise Exception("All data sources failed")

        logger.add_count('eur_rates_fetched', len(eur_rates))
        logger.add_info('data_source', data_source)

        # Step 3: Calculate all pairs
        print("\n3. Calculating all currency pairs...")
        all_pairs = calculate_all_pairs(eur_rates)
        total_calculated = sum(len(v) for v in all_pairs.values())
        print(f"   ✓ Calculated {total_calculated} exchange rates")

        logger.add_count('pairs_calculated', total_calculated)

        # Step 4: Save to CSV file
        print("\n4. Saving to CSV...")
        csv_path = save_rates_csv(all_pairs, date_str)

        logger.add_info('output_file', str(csv_path))

        # Print samples
        print_sample_rates(all_pairs)

        logger.success()

    except Exception as e:
        logger.error(f"Failed to fetch exchange rates: {e}")
        logger.fail()
        raise
    finally:
        logger.finish()


if __name__ == '__main__':
    main()
