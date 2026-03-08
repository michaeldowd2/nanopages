#!/usr/bin/env python3
"""
Pipeline Data Exporter
Exports data from each pipeline step to CSV for dashboard visualization
Includes pipeline configuration (steps and dependencies)
"""

import json
import csv
import glob
import os
import shutil
from datetime import datetime

def export_step2_indices():
    """Step 2: Synthetic Currency Indices"""
    output = []

    for filepath in glob.glob('/workspace/group/fx-portfolio/data/indices/*_index.json'):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                currency = data.get('currency')

                for item in data.get('data', []):
                    output.append({
                        'date': item.get('date'),
                        'currency': currency,
                        'index': item.get('index'),
                        'pct_change': item.get('daily_change_pct'),
                        'base_date': item.get('base_date')
                    })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    output_file = '/workspace/group/fx-portfolio/site_data/step2_indices.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            writer = csv.DictWriter(f, fieldnames=['date', 'currency', 'index', 'pct_change', 'base_date'])
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 2: Exported {len(output)} index records")
    return len(output)

def export_step3_news():
    """Step 3: News Articles"""
    output = []

    for filepath in glob.glob('/workspace/group/fx-portfolio/data/news/*/*.json'):
        if 'url_index' in filepath or 'sources' in filepath:
            continue

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                currency = data.get('currency')
                date = data.get('date')

                for article in data.get('articles', []):
                    output.append({
                        'date': date,
                        'currency': currency,
                        'source': article.get('source', 'Unknown'),
                        'title': article.get('title', ''),
                        'url': article.get('url', ''),
                        'relevance_score': article.get('relevance_score', 0),
                        'snippet': article.get('snippet', '')[:100]  # First 100 chars
                    })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    output_file = '/workspace/group/fx-portfolio/site_data/step3_news.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            writer = csv.DictWriter(f, fieldnames=['date', 'currency', 'source', 'title', 'url', 'relevance_score', 'snippet'])
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 3: Exported {len(output)} news articles")
    return len(output)

def export_step4_horizons():
    """Step 4: Time Horizon Analysis"""
    output = []

    # New format: date-specific JSON files (YYYY-MM-DD.json)
    for filepath in glob.glob('/workspace/group/fx-portfolio/data/article-analysis/*.json'):
        # Skip old analyzed_urls.json file
        if 'analyzed_urls' in filepath or not filepath.endswith('.json'):
            continue

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Check if this is new format (has 'analyses' array) or old format
            if 'analyses' in data:
                # New format: date-specific file with multiple analyses
                date_str = data.get('date', '')
                analyzed_at = data.get('analyzed_at', '')
                estimator_id = data.get('estimator_id', '')
                estimator_type = data.get('estimator_type', '')
                estimator_params = data.get('estimator_params', {})
                est_params_str = json.dumps(estimator_params) if estimator_params else ''

                # Process each analysis in the file
                for analysis in data.get('analyses', []):
                    output.append({
                        'date': date_str,
                        'estimator_id': estimator_id,
                        'url': analysis.get('url', ''),
                        'currency': analysis.get('currency', ''),
                        'title': analysis.get('title', ''),
                        'analyzed_at': analyzed_at,
                        'time_horizon': analysis.get('time_horizon', ''),
                        'horizon_days': analysis.get('horizon_days', ''),
                        'valid_to_date': analysis.get('valid_to_date', ''),
                        'confidence': analysis.get('confidence') if analysis.get('confidence') is not None else '',
                        'reasoning': analysis.get('reasoning', '')
                    })
            else:
                # Old format: single analysis per file (hash-based filenames)
                # Extract date from analyzed_at
                analyzed_at = data.get('analyzed_at', '')
                date_str = analyzed_at.split('T')[0] if analyzed_at else ''

                output.append({
                    'date': date_str,
                    'estimator_id': data.get('estimator_id', ''),
                    'url': data.get('url', ''),
                    'currency': data.get('currency', ''),
                    'title': data.get('title', ''),
                    'analyzed_at': analyzed_at,
                    'time_horizon': data.get('time_horizon', ''),
                    'horizon_days': data.get('horizon_days', ''),
                    'valid_to_date': data.get('valid_to_date', ''),
                    'confidence': data.get('confidence') if data.get('confidence') is not None else '',
                    'reasoning': data.get('reasoning', '')
                })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    output_file = '/workspace/group/fx-portfolio/site_data/step4_horizons.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            writer = csv.DictWriter(f, fieldnames=[
                'date', 'estimator_id', 'url', 'currency', 'title', 'analyzed_at',
                'time_horizon', 'horizon_days', 'valid_to_date', 'confidence', 'reasoning'
            ])
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 4: Exported {len(output)} horizon analyses")
    return len(output)

def export_step5_signals():
    """Step 5: Sentiment Signals"""
    output = []

    for filepath in glob.glob('/workspace/group/fx-portfolio/data/signals/*/*.json'):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                currency = data.get('currency')
                date = data.get('date')

                for signal in data.get('signals', []):
                    # Calculate magnitude-weighted signal
                    magnitude_multipliers = {
                        'small': 0.4,
                        'medium': 0.7,
                        'large': 1.4
                    }
                    magnitude = signal.get('predicted_magnitude', 'medium')
                    confidence = signal.get('confidence', 0) if signal.get('confidence') is not None else 0
                    magnitude_weight = magnitude_multipliers.get(magnitude, 0.7)
                    signal_value = confidence * magnitude_weight if confidence else ''

                    output.append({
                        'date': signal.get('date') or date,
                        'generator_id': signal.get('generator_id', ''),
                        'currency': currency,
                        'signal_type': signal.get('signal_type', ''),
                        'article_title': signal.get('article_title', ''),
                        'article_url': signal.get('article_url', ''),
                        'predicted_direction': signal.get('predicted_direction', ''),
                        'predicted_magnitude': signal.get('predicted_magnitude') or '',
                        'confidence': confidence,
                        'signal': signal_value
                    })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    output_file = '/workspace/group/fx-portfolio/site_data/step5_signals.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            writer = csv.DictWriter(f, fieldnames=[
                'date', 'generator_id', 'currency', 'signal_type', 'article_title', 'article_url',
                'predicted_direction', 'predicted_magnitude', 'confidence', 'signal'
            ])
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 5: Exported {len(output)} signals")
    return len(output)

def export_step6_realization():
    """Step 6: Signal Realization Status - reads from signal-realization directory"""
    output = []

    realization_dir = '/workspace/group/fx-portfolio/data/signal-realization'

    if not os.path.exists(realization_dir):
        print(f"⚠️  Step 6: No realization data found at {realization_dir}")
        return 0

    for filepath in glob.glob(f'{realization_dir}/*.json'):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            process_date = data.get('process_date', '')

            for record in data.get('records', []):
                output.append({
                    'process_date': process_date,
                    'article_download_date': record.get('article_download_date', ''),
                    'valid_to_date': record.get('valid_to_date', ''),
                    'currency': record.get('currency', ''),
                    'url': record.get('url', ''),
                    'title': record.get('title', ''),
                    'generator_id': record.get('generator_id', ''),
                    'estimator_id': record.get('estimator_id', ''),
                    'horizon_days': record.get('horizon_days', ''),
                    'start_index': record.get('start_index', ''),
                    'end_index': record.get('end_index', ''),
                    'actual_pct_change': record.get('actual_pct_change', ''),
                    'actual_direction': record.get('actual_direction', ''),
                    'realized': record.get('realized', False),
                    'predicted_direction': record.get('predicted_direction', ''),
                    'predicted_magnitude': record.get('predicted_magnitude', ''),
                    'confidence': record.get('confidence', ''),
                    'signal': record.get('signal', '')
                })
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    output_file = '/workspace/group/fx-portfolio/site_data/step6_realization.csv'

    with open(output_file, 'w', newline='') as f:
        if output:
            writer = csv.DictWriter(f, fieldnames=[
                'process_date', 'article_download_date', 'valid_to_date', 'currency', 'url', 'title',
                'generator_id', 'estimator_id', 'horizon_days',
                'start_index', 'end_index', 'actual_pct_change', 'actual_direction',
                'realized', 'predicted_direction', 'predicted_magnitude', 'confidence', 'signal'
            ])
            writer.writeheader()
            writer.writerows(output)

    print(f"✓ Step 6: Exported {len(output)} realization checks")
    return len(output)

def export_pipeline_config():
    """Export pipeline configuration (steps and dependencies)"""
    config_file = '/workspace/group/fx-portfolio/config/pipeline_steps.json'
    output_file = '/workspace/group/fx-portfolio/site_data/pipeline_steps.json'

    if os.path.exists(config_file):
        shutil.copy(config_file, output_file)
        print(f"✓ Pipeline config: Exported to {output_file}")
        return 1
    else:
        print(f"⚠️  Pipeline config not found: {config_file}")
        return 0

def export_system_config():
    """Export system configuration (strategies, generators, estimators)"""
    config_file = '/workspace/group/fx-portfolio/config/system_config.json'
    output_file = '/workspace/group/fx-portfolio/site_data/system_config.json'

    if os.path.exists(config_file):
        shutil.copy(config_file, output_file)
        print(f"✓ System config: Exported to {output_file}")
        return 1
    else:
        print(f"⚠️  System config not found: {config_file}")
        return 0

def export_step4_1_currency_events():
    """Step 4.1: Currency Events Taxonomy"""
    events_file = '/workspace/group/fx-portfolio/data/events/currency_events.json'

    if not os.path.exists(events_file):
        print("⚠️  Step 4.1: No currency events file found")
        return 0

    try:
        with open(events_file, 'r') as f:
            data = json.load(f)

        events = data.get('events', [])

        # Export to CSV for dashboard table view
        output_file = '/workspace/group/fx-portfolio/site_data/step4_1_currency_events.csv'

        with open(output_file, 'w', newline='') as f:
            if events:
                # Flatten keywords array for CSV
                rows = []
                for event in events:
                    rows.append({
                        'event_id': event.get('event_id', ''),
                        'event_name': event.get('event_name', ''),
                        'category': event.get('category', ''),
                        'signal_direction': event.get('signal_direction', ''),
                        'signal_strength': event.get('signal_strength', ''),
                        'time_horizon': event.get('time_horizon', ''),
                        'confidence_impact': event.get('confidence_impact', ''),
                        'keywords': ', '.join(event.get('keywords', [])),
                        'description': event.get('description', '')
                    })

                writer = csv.DictWriter(f, fieldnames=[
                    'event_id', 'event_name', 'category', 'signal_direction',
                    'signal_strength', 'time_horizon', 'confidence_impact',
                    'keywords', 'description'
                ])
                writer.writeheader()
                writer.writerows(rows)

        # Also copy the JSON file for full data access
        output_json = '/workspace/group/fx-portfolio/site_data/step4_1_currency_events.json'
        shutil.copy(events_file, output_json)

        print(f"✓ Step 4.1: Exported {len(events)} currency event types")
        return len(events)

    except Exception as e:
        print(f"⚠️  Step 4.1: Error exporting currency events: {e}")
        return 0

def export_step1_exchange_rates():
    """Step 1: Export exchange rates matrix CSV"""

    # Find all price files
    price_files = sorted(glob.glob('/workspace/group/fx-portfolio/data/prices/fx-rates-*.json'))

    if not price_files:
        print("⚠️  Step 1: No exchange rate files found")
        return 0

    # Create output directory
    output_dir = '/workspace/group/fx-portfolio/site_data'
    os.makedirs(output_dir, exist_ok=True)

    # Export matrix CSV (dates as rows, currencies as columns)
    matrix_csv_file = f'{output_dir}/step1_exchange_rates_matrix.csv'
    currencies = ['EUR', 'USD', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD', 'NOK', 'SEK', 'CNY', 'MXN']

    row_count = 0
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
                row_count += 1

    print(f"✓ Step 1: Exported {row_count} exchange rate rows ({len(price_files)} dates)")
    return row_count

def export_step7_aggregated_signals():
    """Step 7: Aggregated Signals"""
    src = '/workspace/group/fx-portfolio/data/aggregated-signals/aggregated_signals.csv'
    dst = '/workspace/group/fx-portfolio/site_data/step7_aggregated_signals.csv'

    if not os.path.exists(src):
        print("⚠️  Step 7: No aggregated signals file found")
        return 0

    shutil.copy2(src, dst)

    # Count rows
    with open(src, 'r') as f:
        row_count = sum(1 for line in f) - 1  # Subtract header

    print(f"✓ Step 7: Exported {row_count} aggregated signal records")
    return row_count

def export_step8_trades():
    """Step 8: Trade Recommendations"""
    src = '/workspace/group/fx-portfolio/data/trades/trades.csv'
    dst = '/workspace/group/fx-portfolio/site_data/step8_trades.csv'

    if not os.path.exists(src):
        print("⚠️  Step 8: No trades file found")
        return 0

    shutil.copy2(src, dst)

    # Count rows
    with open(src, 'r') as f:
        row_count = sum(1 for line in f) - 1  # Subtract header

    print(f"✓ Step 8: Exported {row_count} trade records")
    return row_count

def export_step9_strategies():
    """Step 9: Portfolio Strategies"""
    src_csv = '/workspace/group/fx-portfolio/data/portfolios/strategies.csv'
    dst_csv = '/workspace/group/fx-portfolio/site_data/step9_strategies.csv'

    src_json = '/workspace/group/fx-portfolio/data/portfolios/strategies_detail.json'
    dst_json = '/workspace/group/fx-portfolio/site_data/step9_strategies_detail.json'

    count = 0

    if os.path.exists(src_csv):
        shutil.copy2(src_csv, dst_csv)
        with open(src_csv, 'r') as f:
            count = sum(1 for line in f) - 1  # Subtract header
    else:
        print("⚠️  Step 9: No strategies CSV file found")

    if os.path.exists(src_json):
        shutil.copy2(src_json, dst_json)

    if count > 0:
        print(f"✓ Step 9: Exported {count} strategy records")

    return count

def main():
    """Export all pipeline data to CSVs"""
    print("="*60)
    print("Pipeline Data Exporter")
    print("="*60)

    stats = {}
    stats['step1'] = export_step1_exchange_rates()
    stats['step2'] = export_step2_indices()
    stats['step3'] = export_step3_news()
    stats['step4'] = export_step4_horizons()
    stats['step4.1'] = export_step4_1_currency_events()
    stats['step5'] = export_step5_signals()
    stats['step6'] = export_step6_realization()
    stats['step7'] = export_step7_aggregated_signals()
    stats['step8'] = export_step8_trades()
    stats['step9'] = export_step9_strategies()
    stats['pipeline_config'] = export_pipeline_config()
    stats['system_config'] = export_system_config()

    print(f"\n{'='*60}")
    print("Export Complete")
    print(f"{'='*60}")
    print(f"CSV files saved to: /workspace/group/fx-portfolio/site_data/")
    print(f"\nTotal records exported: {sum(stats.values())}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()

    # Export step counts by date
    import subprocess
    subprocess.run(['python3', 'scripts/export-step-counts.py'], check=True)
