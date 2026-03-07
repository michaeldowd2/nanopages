#!/usr/bin/env python3
"""
Export step counts by data date

Creates a summary showing how many records exist for each step for each date.
This helps track data completeness across the pipeline.
"""

import json
import csv
import glob
from collections import defaultdict
from pathlib import Path

def count_records_by_date(csv_file, date_column='date'):
    """Count records per date in a CSV file"""
    counts = defaultdict(int)

    if not Path(csv_file).exists():
        return counts

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row.get(date_column, '')
            if date and date != 'date':  # Skip header if present
                counts[date] += 1

    return dict(counts)

def count_json_analyses_by_date(analysis_dir):
    """Count analyses in date-specific JSON files"""
    counts = {}

    analysis_path = Path(analysis_dir)
    if not analysis_path.exists():
        return counts

    for filepath in analysis_path.glob('*.json'):
        # Skip non-date files
        if filepath.name == 'analyzed_urls.json':
            continue

        # Date-based files are named YYYY-MM-DD.json
        if len(filepath.stem) == 10 and filepath.stem.count('-') == 2:
            try:
                with open(filepath) as f:
                    data = json.load(f)
                    date = data.get('date', filepath.stem)
                    count = len(data.get('analyses', []))
                    counts[date] = count
            except Exception:
                continue

    return counts

def export_step_counts():
    """Export counts for all steps by data date"""

    # Collect counts from each step
    step_counts = {}

    # Step 1: Exchange Rates (no date column, just file count)
    prices_dir = Path('/workspace/group/fx-portfolio/data/prices')
    if prices_dir.exists():
        step_counts['step1'] = {
            'name': 'Exchange Rates',
            'counts': {filepath.stem: 1 for filepath in prices_dir.glob('*.json')}
        }

    # Step 2: Currency Indices
    step_counts['step2'] = {
        'name': 'Currency Indices',
        'counts': count_records_by_date('/workspace/group/fx-portfolio/data/exports/step2_indices.csv')
    }

    # Step 3: News Articles
    step_counts['step3'] = {
        'name': 'News Articles',
        'counts': count_records_by_date('/workspace/group/fx-portfolio/data/exports/step3_news.csv')
    }

    # Step 4: Time Horizon Analysis (from date-specific JSON files)
    step_counts['step4'] = {
        'name': 'Time Horizon Analysis',
        'counts': count_json_analyses_by_date('/workspace/group/fx-portfolio/data/article-analysis')
    }

    # Step 5: Sentiment Signals
    step_counts['step5'] = {
        'name': 'Sentiment Signals',
        'counts': count_records_by_date('/workspace/group/fx-portfolio/data/exports/step5_signals.csv')
    }

    # Step 6: Signal Realization
    step_counts['step6'] = {
        'name': 'Signal Realization',
        'counts': count_records_by_date('/workspace/group/fx-portfolio/data/exports/step6_realization.csv')
    }

    # Step 7: Trades
    trades_file = '/workspace/group/fx-portfolio/data/exports/step7_trades.csv'
    if Path(trades_file).exists():
        with open(trades_file, 'r') as f:
            reader = csv.DictReader(f)
            # date is 2nd column for trades
            trades_counts = defaultdict(int)
            for row in reader:
                date = row.get('date', '')
                if date:
                    trades_counts[date] += 1
            step_counts['step7'] = {
                'name': 'Trades',
                'counts': dict(trades_counts)
            }

    # Step 8: Strategies
    step_counts['step8'] = {
        'name': 'Portfolio Strategies',
        'counts': count_records_by_date('/workspace/group/fx-portfolio/data/exports/step8_strategies.csv')
    }

    # Get all unique dates
    all_dates = set()
    for step_data in step_counts.values():
        all_dates.update(step_data['counts'].keys())

    all_dates = sorted(all_dates)

    # Build output structure
    output = {
        'last_updated': Path('/workspace/group/fx-portfolio/data/exports/tracking_dates.json').stat().st_mtime if Path('/workspace/group/fx-portfolio/data/exports/tracking_dates.json').exists() else None,
        'dates': list(all_dates),
        'steps': []
    }

    # Add each step's counts
    for step_id in ['step1', 'step2', 'step3', 'step4', 'step5', 'step6', 'step7', 'step8']:
        if step_id in step_counts:
            step_data = step_counts[step_id]
            output['steps'].append({
                'step_id': step_id,
                'step_name': step_data['name'],
                'counts_by_date': {date: step_data['counts'].get(date, 0) for date in all_dates}
            })

    # Save to JSON
    output_file = '/workspace/group/fx-portfolio/data/exports/step_counts_by_date.json'
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"✓ Exported step counts by date to {output_file}")
    print(f"  Dates: {', '.join(all_dates)}")
    print(f"  Steps: {len(output['steps'])}")

    return len(all_dates)

if __name__ == '__main__':
    export_step_counts()
