#!/usr/bin/env python3
"""
Step 1: Fetch Exchange Rates (All Pairs)

Downloads exchange rates for all currency pairs (10x10 matrix).
Uses EUR as intermediary since most FX APIs provide EUR pairs.

For each pair X/Y, we calculate:
X/Y = (EUR/Y) / (EUR/X)

Example: USD/JPY = EUR/JPY ÷ EUR/USD

API Source: GitHub Currency API (fawazahmed0/exchange-api)
- Free, no API key required
- 200+ currencies
- Daily updates
- CDN-backed for reliability

Output: CSV with columns: date, base_currency, quote_currency, rate
"""

import sys
import argparse
from datetime import datetime
import urllib.request
import urllib.error
import json

# Add utilities to path
sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.config_loader import get_currencies
from utilities.pipeline_logger import PipelineLogger
from utilities.csv_helper import write_csv

CURRENCIES = get_currencies()

# GitHub Currency API endpoints (free, no API key needed)
CURRENCY_API_PRIMARY = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/eur.json"
CURRENCY_API_FALLBACK = "https://latest.currency-api.pages.dev/v1/currencies/eur.json"


def fetch_eur_rates_from_api():
    """
    Fetch EUR-based rates from GitHub Currency API

    Returns rates in format: {"eur": {"usd": 1.18, "gbp": 0.874, ...}}
    Tries primary CDN first, then fallback URL if that fails.
    """
    # Try primary endpoint first
    try:
        print("   Trying primary endpoint (cdn.jsdelivr.net)...")
        with urllib.request.urlopen(CURRENCY_API_PRIMARY, timeout=10) as response:
            data = json.loads(response.read().decode())

        if "eur" in data:
            print("   ✓ Primary endpoint successful")
            return data["eur"], data.get("date", "unknown")
        else:
            raise Exception("Unexpected API response format")

    except Exception as e:
        print(f"   ⚠️ Primary endpoint failed: {e}")
        print("   Trying fallback endpoint (currency-api.pages.dev)...")

        # Try fallback endpoint
        try:
            with urllib.request.urlopen(CURRENCY_API_FALLBACK, timeout=10) as response:
                data = json.loads(response.read().decode())

            if "eur" in data:
                print("   ✓ Fallback endpoint successful")
                return data["eur"], data.get("date", "unknown")
            else:
                raise Exception("Unexpected API response format")

        except Exception as fallback_error:
            print(f"   ✗ Fallback endpoint also failed: {fallback_error}")
            raise Exception(f"Both API endpoints failed. Primary: {e}, Fallback: {fallback_error}")


def fetch_eur_rates():
    """
    Fetch EUR-based rates from GitHub Currency API

    Falls back to mock data only if API is completely unavailable.
    """
    # Mock rates (only used as last resort fallback)
    mock_rates = {
        "EUR": 1.0,
        "USD": 1.18,
        "GBP": 0.874,
        "JPY": 182.44,
        "CHF": 0.912,
        "AUD": 1.67,
        "CAD": 1.61,
        "NOK": 11.25,
        "SEK": 10.68,
        "CNY": 8.14,
        "MXN": 20.31
    }

    # Try to fetch real data from API
    try:
        rates_data, api_date = fetch_eur_rates_from_api()

        # Convert to uppercase keys and normalize format
        normalized_rates = {"EUR": 1.0}  # EUR base is always 1.0

        for currency_code, rate in rates_data.items():
            # API returns lowercase codes (e.g., "usd"), convert to uppercase
            currency_upper = currency_code.upper()
            if currency_upper in CURRENCIES:
                normalized_rates[currency_upper] = rate

        print(f"   ✓ Fetched rates from API (date: {api_date})")
        print(f"   ✓ Found {len(normalized_rates)} currencies from our list")

        return normalized_rates, "github-currency-api"

    except Exception as e:
        print(f"⚠️ API request failed: {e}")
        print("   Falling back to mock data")
        return mock_rates, "mock-data-fallback"


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

        # Fetch EUR-based rates
        print("\n1. Fetching EUR-based rates from GitHub Currency API...")
        eur_rates, data_source = fetch_eur_rates()
        print(f"   ✓ Got rates for {len(eur_rates)} currencies")

        logger.add_count('eur_rates_fetched', len(eur_rates))
        logger.add_info('data_source', data_source)

        # Warn if using mock data
        if "mock" in data_source:
            logger.warning(f'Using mock data: {data_source}')

        # Calculate all pairs
        print("\n2. Calculating all currency pairs...")
        all_pairs = calculate_all_pairs(eur_rates)
        total_calculated = sum(len(v) for v in all_pairs.values())
        print(f"   ✓ Calculated {total_calculated} exchange rates")

        logger.add_count('pairs_calculated', total_calculated)

        # Save to CSV file
        print("\n3. Saving to CSV...")
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
