#!/usr/bin/env python3
"""
Export exchange rates to CSV for dashboard display

Exports latest all-pairs exchange rates in a format suitable for the dashboard.
"""

import json
import glob
import csv
import os

def export_exchange_rates():
    """Export exchange rates matrix CSV"""

    # Find all price files
    price_files = sorted(glob.glob('/workspace/group/fx-portfolio/data/prices/fx-rates-*.json'))

    if not price_files:
        print("⚠️ No exchange rate files found")
        return

    # Create output directory
    output_dir = '/workspace/group/fx-portfolio/data/exports'
    os.makedirs(output_dir, exist_ok=True)

    # Export matrix CSV (dates as rows, currencies as columns)
    matrix_csv_file = f'{output_dir}/step1_exchange_rates_matrix.csv'
    currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NOK', 'SEK', 'CNY', 'MXN']

    with open(matrix_csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        # Header: date, then all currencies
        writer.writerow(['date', 'base_currency'] + currencies)

        for price_file in price_files:
            with open(price_file, 'r') as pf:
                data = json.load(pf)

            date = data.get('date', '')
            all_pairs = data.get('all_pairs', {})

            if not all_pairs:
                continue

            # Write one row per base currency
            for base_curr in currencies:
                if base_curr not in all_pairs:
                    continue

                row = [date, base_curr]
                for quote_curr in currencies:
                    rate = all_pairs.get(base_curr, {}).get(quote_curr, '')
                    row.append(f'{rate:.6f}' if rate else '')

                writer.writerow(row)

    print(f"✓ Exported exchange rates matrix: {matrix_csv_file}")
    print(f"  Total files: {len(price_files)}")

if __name__ == '__main__':
    export_exchange_rates()
