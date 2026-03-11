#!/usr/bin/env python3
"""
Pipeline Data Exporter (CSV-based)
Exports data from each pipeline step CSV to combined CSVs for dashboard visualization
Includes pipeline configuration (steps and dependencies)
"""

import json
import csv
import glob
import os
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.csv_helper import read_csv

def export_step1_exchange_rates():
    """Step 1: Export exchange rates as matrix CSV (dashboard format)"""

    # Find all price CSV files
    price_files = sorted(glob.glob('/workspace/group/fx-portfolio/data/prices/*.csv'))

    if not price_files:
        print("⚠️  Step 1: No exchange rate files found")
        return 0

    # Get list of currencies from system config
    sys.path.append('/workspace/group/fx-portfolio/scripts')
    from utilities.config_loader import get_currencies
    currencies = get_currencies()

    # Build matrix format: one row per (date, base_currency) with all quote currencies as columns
    matrix_rows = []

    for filepath in price_files:
        try:
            date = Path(filepath).stem  # Extract date from filename
            rows = read_csv('process_1_exchange_rates', date=date, validate=False)

            # Group by base currency
            by_base = {}
            for row in rows:
                base = row['base_currency']
                quote = row['quote_currency']
                rate = float(row['rate'])

                if base not in by_base:
                    by_base[base] = {'date': date, 'base_currency': base}

                by_base[base][quote] = rate

            # Add to matrix rows
            for base_currency in currencies:
                if base_currency in by_base:
                    matrix_rows.append(by_base[base_currency])

        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")

    # Write matrix CSV
    output_file = '/workspace/group/fx-portfolio/site_data/step1_exchange_rates_matrix.csv'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w', newline='') as f:
        if matrix_rows:
            fieldnames = ['date', 'base_currency'] + currencies
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(matrix_rows)

    print(f"✓ Step 1: Exported {len(matrix_rows)} exchange rate matrix rows ({len(price_files)} dates × {len(currencies)} currencies)")
    return len(matrix_rows)


def export_step2_indices():
    """Step 2: Synthetic Currency Indices"""
    output = []

    # Find all indices CSV files
    index_files = sorted(glob.glob('/workspace/group/fx-portfolio/data/indices/*.csv'))

    if not index_files:
        print("⚠️  Step 2: No index files found")
        return 0

    # Read all CSV files and combine
    for filepath in index_files:
        try:
            date = Path(filepath).stem
            rows = read_csv('process_2_indices', date=date, validate=False)
            output.extend(rows)
        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")

    # Write combined CSV
    output_file = '/workspace/group/fx-portfolio/site_data/step2_indices.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            fieldnames = ['date', 'currency', 'index']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 2: Exported {len(output)} index records")
    return len(output)


def export_step3_news():
    """Step 3: News Articles"""
    output = []

    # Find all news CSV files
    news_files = sorted(glob.glob('/workspace/group/fx-portfolio/data/news/*.csv'))

    if not news_files:
        print("⚠️  Step 3: No news files found")
        return 0

    # Read all CSV files and combine
    for filepath in news_files:
        try:
            date = Path(filepath).stem
            rows = read_csv('process_3_news', date=date, validate=False)
            output.extend(rows)
        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")

    # Write combined CSV
    output_file = '/workspace/group/fx-portfolio/site_data/step3_news.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            fieldnames = ['date', 'source', 'url', 'currency', 'title', 'snippet']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 3: Exported {len(output)} news articles")
    return len(output)


def export_step4_horizons():
    """Step 4: Time Horizon Analysis"""
    output = []

    # Find all horizon analysis CSV files
    horizon_files = sorted(glob.glob('/workspace/group/fx-portfolio/data/article-analysis/*.csv'))

    if not horizon_files:
        print("⚠️  Step 4: No horizon analysis files found")
        return 0

    # Read all CSV files and combine
    for filepath in horizon_files:
        try:
            date = Path(filepath).stem
            rows = read_csv('process_4_horizons', date=date, validate=False)
            output.extend(rows)
        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")

    # Write combined CSV
    output_file = '/workspace/group/fx-portfolio/site_data/step4_horizons.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            fieldnames = ['date', 'source', 'url', 'currency', 'title', 'estimator_id',
                         'time_horizon', 'horizon_days', 'valid_to_date', 'confidence', 'reasoning']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 4: Exported {len(output)} horizon analyses")
    return len(output)




def export_step4_1_currency_events():
    """Step 4.1: Currency Events Reference"""
    # Read currency events JSON
    events_file = '/workspace/group/fx-portfolio/data/events/currency_events.json'

    if not os.path.exists(events_file):
        print("⚠️  Step 4.1: Currency events file not found")
        return 0

    with open(events_file, 'r') as f:
        events_data = json.load(f)

    # Flatten events array to CSV format
    output = []
    for event in events_data.get('events', []):
        output.append({
            'event_id': event['event_id'],
            'event_name': event['event_name'],
            'category': event['category'],
            'signal_direction': event['signal_direction'],
            'signal_strength': event['signal_strength'],
            'time_horizon': event['time_horizon'],
            'confidence_impact': event['confidence_impact'],
            'description': event['description']
        })

    # Write combined CSV
    output_file = '/workspace/group/fx-portfolio/site_data/step4_1_currency_events.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            fieldnames = ['event_id', 'event_name', 'category', 'signal_direction',
                         'signal_strength', 'time_horizon', 'confidence_impact', 'description']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 4.1: Exported {len(output)} currency event definitions")
    return len(output)


def export_step5_signals():
    """Step 5: Sentiment Signals"""
    output = []

    # Find all signal CSV files
    signal_files = sorted(glob.glob('/workspace/group/fx-portfolio/data/signals/*.csv'))

    if not signal_files:
        print("⚠️  Step 5: No signal files found")
        return 0

    # Read all CSV files and combine
    for filepath in signal_files:
        try:
            date = Path(filepath).stem
            rows = read_csv('process_5_signals', date=date, validate=False)
            output.extend(rows)
        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")

    # Write combined CSV
    output_file = '/workspace/group/fx-portfolio/site_data/step5_signals.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            # Use fieldnames from first row to ensure all columns are included
            fieldnames = list(output[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 5: Exported {len(output)} signals")
    return len(output)


def export_step6_realization():
    """Step 6: Signal Realization Checks"""
    output = []

    # Find all realization CSV files
    realization_files = sorted(glob.glob('/workspace/group/fx-portfolio/data/signal-realization/*.csv'))

    if not realization_files:
        print("⚠️  Step 6: No realization files found")
        return 0

    # Read all CSV files and combine
    for filepath in realization_files:
        try:
            date = Path(filepath).stem
            rows = read_csv('process_6_realization', date=date, validate=False)
            output.extend(rows)
        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")

    # Write combined CSV
    output_file = '/workspace/group/fx-portfolio/site_data/step6_realization.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            # Use fieldnames from first row to ensure all columns are included
            fieldnames = list(output[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 6: Exported {len(output)} realization checks")
    return len(output)


def export_step7_aggregated_signals():
    """Step 7: Aggregated Signals"""
    output = []

    # Find all aggregated signals CSV files (only date-named files YYYY-MM-DD.csv)
    import re
    all_files = glob.glob('/workspace/group/fx-portfolio/data/aggregated-signals/*.csv')
    agg_files = sorted([f for f in all_files if re.match(r'.*\d{4}-\d{2}-\d{2}\.csv$', f)])

    if not agg_files:
        print("⚠️  Step 7: No aggregated signals files found")
        return 0

    # Read all CSV files and combine
    for filepath in agg_files:
        try:
            date = Path(filepath).stem
            rows = read_csv('process_7_aggregated_signals', date=date, validate=False)
            output.extend(rows)
        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")

    # Write combined CSV
    output_file = '/workspace/group/fx-portfolio/site_data/step7_aggregated_signals.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            # Use fieldnames from first row to ensure all columns are included
            fieldnames = list(output[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 7: Exported {len(output)} aggregated signal records")
    return len(output)


def export_step8_trades():
    """Step 8: Trade Recommendations"""
    output = []

    # Find all trades CSV files (only date-named files YYYY-MM-DD.csv)
    import re
    all_files = glob.glob('/workspace/group/fx-portfolio/data/trades/*.csv')
    trade_files = sorted([f for f in all_files if re.match(r'.*\d{4}-\d{2}-\d{2}\.csv$', f)])

    if not trade_files:
        print("⚠️  Step 8: No trade files found")
        return 0

    # Read all CSV files and combine
    for filepath in trade_files:
        try:
            date = Path(filepath).stem
            rows = read_csv('process_8_trades', date=date, validate=False)
            output.extend(rows)
        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")

    # Write combined CSV
    output_file = '/workspace/group/fx-portfolio/site_data/step8_trades.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            fieldnames = ['date', 'trader_id', 'buy_currency', 'sell_currency',
                         'buy_signal', 'sell_signal', 'trade_signal']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 8: Exported {len(output)} trade records")
    return len(output)


def export_step9_portfolios():
    """Step 9: Portfolio Execution"""
    output = []

    # Find all portfolio CSV files (only date-named files YYYY-MM-DD.csv)
    import re
    all_files = glob.glob('/workspace/group/fx-portfolio/data/portfolios/*.csv')
    portfolio_files = sorted([f for f in all_files if re.match(r'.*\d{4}-\d{2}-\d{2}\.csv$', f)])

    if not portfolio_files:
        print("⚠️  Execute Strategies: No portfolio files found")
        return 0

    # Read all CSV files and combine
    for filepath in portfolio_files:
        try:
            date = Path(filepath).stem
            rows = read_csv('process_9_portfolio', date=date, validate=False)
            output.extend(rows)
        except Exception as e:
            print(f"⚠️  Error reading {filepath}: {e}")

    # Write combined CSV
    output_file = '/workspace/group/fx-portfolio/site_data/step9_portfolios.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            # Get fieldnames from first row
            if output:
                fieldnames = list(output[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(output)

    print(f"✓ Execute Strategies: Exported {len(output)} strategy records")
    return len(output)


def export_pipeline_config():
    """Export pipeline_steps.json for dashboard"""
    config_src = '/workspace/group/fx-portfolio/config/pipeline_steps.json'
    config_dst = '/workspace/group/fx-portfolio/site_data/pipeline_steps.json'

    if os.path.exists(config_src):
        with open(config_src, 'r') as f:
            config = json.load(f)
        with open(config_dst, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✓ Pipeline config: Exported to {config_dst}")
    else:
        print("⚠️  Pipeline config not found")


def export_system_config():
    """Export system configuration for dashboard"""
    config_files = {
        'traders': '/workspace/group/fx-portfolio/config/traders.json',
        'strategies': '/workspace/group/fx-portfolio/config/strategies.json',
        'generators': '/workspace/group/fx-portfolio/config/generators.json',
        'estimators': '/workspace/group/fx-portfolio/config/estimators.json'
    }

    system_config = {}

    for key, filepath in config_files.items():
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                system_config[key] = json.load(f)

    output_file = '/workspace/group/fx-portfolio/site_data/system_config.json'
    with open(output_file, 'w') as f:
        json.dump(system_config, f, indent=2)

    print(f"✓ System config: Exported to {output_file}")


def main():
    print("="*60)
    print("Pipeline Data Exporter")
    print("="*60)

    total = 0

    total += export_step1_exchange_rates()
    total += export_step2_indices()
    total += export_step3_news()
    total += export_step4_horizons()
    export_step4_1_currency_events()  # Reference data, not counted in total
    total += export_step5_signals()
    total += export_step6_realization()
    total += export_step7_aggregated_signals()
    total += export_step8_trades()
    total += export_step9_portfolios()

    export_pipeline_config()
    export_system_config()

    print("\n" + "="*60)
    print("Export Complete")
    print("="*60)
    print(f"CSV files saved to: /workspace/group/fx-portfolio/site_data/")
    print(f"\nTotal records exported: {total}")
    print("="*60)


if __name__ == '__main__':
    main()
