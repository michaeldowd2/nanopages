#!/usr/bin/env python3
"""
Process 10: Portfolio Valuation

Calculates multi-currency portfolio valuations to provide a currency-neutral
performance metric. By valuing the portfolio in all 11 currencies and averaging
the percentage changes, we reduce the EUR-centric bias in performance measurement.

Input:
- data/prices/{date}.csv - Exchange rates for the date
- data/portfolios/{date}.csv - Portfolio balances from Process 9
- data/valuations/{prev_date}.csv - Previous day's valuations (for % change)

Output:
- data/valuations/{date}.csv - Portfolio values and % changes in all currencies
"""

import sys
import csv
import os
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'scripts'))

from utilities.csv_helper import read_csv, write_csv

CURRENCIES = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NOK', 'SEK', 'CNY', 'MXN']


def load_exchange_rates(date_str):
    """Load exchange rates for the given date."""
    try:
        rows = read_csv('process_1_exchange_rates', date=date_str, validate=False)
    except Exception as e:
        print(f"❌ Failed to load exchange rates for {date_str}: {e}")
        return None

    rates = {}

    # Build rate lookup: rates[from_currency][to_currency] = rate
    for row in rows:
        base = row['base_currency']
        quote = row['quote_currency']
        rate = float(row['rate'])

        if base not in rates:
            rates[base] = {}
        rates[base][quote] = rate

    # Add identity rates (EUR/EUR = 1.0, etc.)
    for curr in CURRENCIES:
        if curr not in rates:
            rates[curr] = {}
        rates[curr][curr] = 1.0

    return rates


def calculate_value_in_currency(balances, rates, target_currency):
    """
    Calculate total portfolio value in the target currency.

    Args:
        balances: dict of {currency: amount}
        rates: dict of {from_currency: {to_currency: rate}}
        target_currency: currency to value the portfolio in

    Returns:
        float: total portfolio value in target currency
    """
    total = 0.0

    for currency, amount in balances.items():
        if amount == 0:
            continue

        # Convert from holding currency to target currency
        if currency == target_currency:
            total += amount
        elif currency in rates and target_currency in rates[currency]:
            # Direct rate available
            rate = rates[currency][target_currency]
            total += amount * rate
        elif target_currency in rates and currency in rates[target_currency]:
            # Inverse rate available
            rate = 1.0 / rates[target_currency][currency]
            total += amount * rate
        else:
            # Cross via EUR
            if currency in rates and 'EUR' in rates[currency]:
                eur_amount = amount * rates[currency]['EUR']
                if 'EUR' in rates and target_currency in rates['EUR']:
                    total += eur_amount * rates['EUR'][target_currency]

    return total


def load_previous_valuations(date_str):
    """Load previous day's valuations for calculating % changes."""
    try:
        current_date = datetime.strptime(date_str, '%Y-%m-%d')

        # Try to find the most recent previous valuation (might be more than 1 day ago)
        # Try up to 7 days back
        for days_back in range(1, 8):
            check_date = current_date - timedelta(days=days_back)
            check_date_str = check_date.strftime('%Y-%m-%d')

            try:
                prev_rows = read_csv('process_10_valuations', date=check_date_str, validate=False)
                # Build lookup: {strategy_id: {currency_value: value, value: cumulative_value}}
                prev_vals = {}
                for row in prev_rows:
                    strategy_id = row['strategy_id']
                    prev_vals[strategy_id] = {
                        curr.lower() + '_value': float(row[curr.lower() + '_value'])
                        for curr in CURRENCIES
                    }
                    # Also store cumulative value for compounding
                    prev_vals[strategy_id]['value'] = float(row.get('value', 1.0))
                return prev_vals
            except:
                # File doesn't exist, try next day
                continue

        return {}
    except Exception as e:
        print(f"⚠️  Could not load previous valuations: {e}")
        return {}


def calculate_percentage_change(current_value, previous_value):
    """Calculate percentage change between two values."""
    if previous_value == 0:
        return 0.0
    return ((current_value - previous_value) / previous_value) * 100


def main():
    parser = argparse.ArgumentParser(description='Calculate multi-currency portfolio valuations')
    parser.add_argument('--date', required=True, help='Date to process (YYYY-MM-DD)')
    args = parser.parse_args()

    date_str = args.date

    print("\n" + "=" * 60)
    print("Process 10: Portfolio Valuation")
    print("=" * 60)
    print(f"Processing date: {date_str}\n")

    # Load exchange rates
    print("1. Loading exchange rates...")
    rates = load_exchange_rates(date_str)
    if not rates:
        print("❌ Failed to load exchange rates")
        sys.exit(1)
    print(f"   ✓ Loaded rates for {len(rates)} currencies")

    # Load portfolio balances
    print("\n2. Loading portfolio balances...")
    try:
        portfolio_rows = read_csv('process_9_portfolio', date=date_str, validate=False)
        print(f"   ✓ Loaded {len(portfolio_rows)} portfolio records")
    except Exception as e:
        print(f"❌ Failed to load portfolio data for {date_str}: {e}")
        sys.exit(1)

    # Load previous valuations for % change calculation
    print("\n3. Loading previous valuations...")
    prev_valuations = load_previous_valuations(date_str)
    if prev_valuations:
        print(f"   ✓ Loaded previous valuations for {len(prev_valuations)} strategies")
    else:
        print("   ℹ️  No previous valuations found (first day or gap in data)")

    # Calculate valuations
    print("\n4. Calculating multi-currency valuations...")
    output_rows = []

    for portfolio in portfolio_rows:
        strategy_id = portfolio['strategy_id']

        # Extract currency balances
        balances = {
            curr: float(portfolio.get(curr, 0))
            for curr in CURRENCIES
        }

        # Calculate portfolio value in each currency
        values = {}
        for target_curr in CURRENCIES:
            values[target_curr.lower() + '_value'] = calculate_value_in_currency(
                balances, rates, target_curr
            )

        # Calculate percentage changes
        pct_changes = {}
        if strategy_id in prev_valuations:
            for curr in CURRENCIES:
                curr_lower = curr.lower()
                current_val = values[curr_lower + '_value']
                prev_val = prev_valuations[strategy_id][curr_lower + '_value']
                pct_changes[curr_lower + '_pct_change'] = calculate_percentage_change(
                    current_val, prev_val
                )
        else:
            # No previous data - set all % changes to 0
            for curr in CURRENCIES:
                pct_changes[curr.lower() + '_pct_change'] = 0.0

        # Calculate average % change (currency-neutral performance metric)
        avg_pct_change = sum(pct_changes.values()) / len(pct_changes)

        # Calculate cumulative value (performance index starting at 1.0)
        if strategy_id in prev_valuations:
            prev_value = prev_valuations[strategy_id]['value']
            # Compound: new_value = prev_value × (1 + pct_change/100)
            cumulative_value = prev_value * (1 + avg_pct_change / 100)
        else:
            # First day - start at 1.0
            cumulative_value = 1.0

        # Build output row
        output_row = {
            'date': date_str,
            'strategy_id': strategy_id,
            **values,
            **pct_changes,
            'avg_pct_change': avg_pct_change,
            'value': cumulative_value
        }

        output_rows.append(output_row)

    print(f"   ✓ Calculated valuations for {len(output_rows)} strategies")

    # Write output
    print("\n5. Writing valuations...")
    output_file = write_csv(output_rows, '10', date=date_str, validate=False)
    print(f"   ✓ Wrote {len(output_rows)} records to {output_file}")

    # Display summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    if output_rows:
        # Show sample valuation (first strategy)
        sample = output_rows[0]
        print(f"\nSample: {sample['strategy_id']}")
        print("\nValues:")
        for curr in CURRENCIES:
            key = curr.lower() + '_value'
            print(f"  {curr}: {sample[key]:,.2f}")

        print("\nPercentage Changes:")
        for curr in CURRENCIES:
            key = curr.lower() + '_pct_change'
            pct = sample[key]
            print(f"  {curr}: {pct:+.2f}%")

        print(f"\nAverage % Change (Currency-Neutral): {sample['avg_pct_change']:+.2f}%")
        print(f"Cumulative Value (Performance Index): {sample['value']:.6f}")

    print("\n" + "=" * 60)
    print("✓ Portfolio valuation complete")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
