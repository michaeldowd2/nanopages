#!/usr/bin/env python3
"""
Trade Calculator (Step 8)

Generates trade recommendations based on trader configurations.
Traders define HOW to generate trades from aggregated signals (inputs, weighting, pairing logic).

Trader Types:
- "combinator": Generates ALL combinations of bullish/bearish currency pairs
- "cascading": Pairs strongest bull with strongest bear, 2nd with 2nd, etc. (not currently used)

Input: data/aggregated-signals/aggregated_signals.csv
Output: data/trades/trades.csv
"""

import json
import os
import glob
import sys
import argparse
import csv
from datetime import datetime
from itertools import product

sys.path.append('/workspace/group/fx-portfolio/scripts')
from pipeline_logger import PipelineLogger
from config_loader import get_traders

CURRENCIES = ["EUR", "USD", "GBP", "JPY", "CHF", "AUD", "CAD", "NOK", "SEK", "CNY", "MXN"]

def load_latest_prices(date_str=None):
    """Load exchange rates from Step 1 for a specific date"""
    if date_str:
        price_file = f'/workspace/group/fx-portfolio/data/prices/fx-rates-{date_str}.json'
        if os.path.exists(price_file):
            with open(price_file, 'r') as f:
                data = json.load(f)
                eur_rates = data.get('eur_base_rates', data.get('rates', {}))
                all_pairs = data.get('all_pairs', {})
                return eur_rates, all_pairs

    # Load most recent if no date specified or date not found
    price_files = sorted(glob.glob('/workspace/group/fx-portfolio/data/prices/fx-rates-*.json'))

    if not price_files:
        return None, None

    with open(price_files[-1], 'r') as f:
        data = json.load(f)
        eur_rates = data.get('eur_base_rates', data.get('rates', {}))
        all_pairs = data.get('all_pairs', {})
        return eur_rates, all_pairs

def load_aggregated_signals(date_str=None, generator_ids=None, estimator_ids=None):
    """
    Load aggregated signals from Step 7, filtered by generator and estimator IDs.

    Returns: (aggregated_signals_by_currency, actual_date_str)
    """
    step7_csv = '/workspace/group/fx-portfolio/data/aggregated-signals/aggregated_signals.csv'

    if not os.path.exists(step7_csv):
        aggregated_by_currency = {curr: [] for curr in CURRENCIES}
        inferred_date = date_str if date_str else datetime.now().strftime('%Y-%m-%d')
        return aggregated_by_currency, inferred_date

    aggregated_by_currency = {curr: [] for curr in CURRENCIES}
    dates_with_data = set()

    with open(step7_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_date = row['date']

            # Filter by date if specified
            if date_str and row_date != date_str:
                continue

            # Filter by generator
            if generator_ids and row['generator_id'] not in generator_ids:
                continue

            # Filter by estimator
            if estimator_ids and row['estimator_id'] not in estimator_ids:
                continue

            currency = row['currency']
            if currency in CURRENCIES:
                dates_with_data.add(row_date)

                agg_signal = {
                    'generator_id': row['generator_id'],
                    'estimator_id': row['estimator_id'],
                    'aggregate_signal': float(row['aggregate_signal']),  # Signed signal (with penalty applied)
                    'signal_count': int(row['signal_count']),
                    'penalty_factor': float(row.get('penalty_factor', 1.0)),  # Optional for visibility
                    'base_signal': float(row.get('base_signal', row['aggregate_signal']))  # Optional
                }
                aggregated_by_currency[currency].append(agg_signal)

    # Determine actual date used
    if date_str:
        actual_date = date_str
    elif dates_with_data:
        actual_date = max(dates_with_data)
    else:
        actual_date = datetime.now().strftime('%Y-%m-%d')

    return aggregated_by_currency, actual_date

def combine_aggregated_signals(aggregated_signals, generator_weights=None):
    """
    Combine multiple aggregated signals (from different generator/estimator combinations)
    for a single currency using weighted averaging.

    Returns: (direction, confidence, total_signal_count)
    """
    if not aggregated_signals:
        return 'neutral', 0.0, 0

    weighted_scores = []
    total_weight = 0.0
    total_signal_count = 0

    for agg_sig in aggregated_signals:
        # aggregate_signal is SIGNED (positive=bullish, negative=bearish)
        signed_signal = agg_sig.get('aggregate_signal', 0.0)
        signal_count = agg_sig.get('signal_count', 0)
        generator_id = agg_sig.get('generator_id', '')

        # Apply generator weight if specified
        gen_weight = 1.0
        if generator_weights and generator_id in generator_weights:
            gen_weight = generator_weights[generator_id]

        weighted_scores.append(signed_signal * gen_weight)
        total_weight += gen_weight
        total_signal_count += signal_count

    # Calculate final weighted average
    avg_score = sum(weighted_scores) / total_weight if total_weight > 0 else 0

    # Determine final direction (return SIGNED confidence)
    if avg_score > 0.01:
        return 'bullish', avg_score, total_signal_count
    elif avg_score < -0.01:
        return 'bearish', avg_score, total_signal_count
    else:
        return 'neutral', avg_score, total_signal_count

def generate_trades_combinator(trader_id, aggregate_signals, date_str):
    """
    Generate ALL combinations of bullish/bearish currency pairs.

    For each bullish currency, pair with every bearish currency.
    Trade confidence = average of abs(buy_conf) and abs(sell_conf)

    Returns: List of trade dicts sorted by confidence (descending)
    """
    trades = []

    # Separate bullish and bearish signals
    bullish = []
    bearish = []

    for curr, (direction, conf) in aggregate_signals.items():
        if direction == 'bullish' and conf > 0:
            bullish.append((curr, conf))
        elif direction == 'bearish' and conf < 0:
            bearish.append((curr, conf))

    # Generate ALL combinations
    for buy_currency, buy_conf in bullish:
        for sell_currency, sell_conf in bearish:
            # Trade confidence is average of absolute values
            trade_confidence = (abs(buy_conf) + abs(sell_conf)) / 2.0

            trades.append({
                'trader_id': trader_id,
                'date': date_str,
                'buy_currency': buy_currency,
                'sell_currency': sell_currency,
                'buy_signal': round(buy_conf, 4),
                'sell_signal': round(sell_conf, 4),
                'trade_signal': round(trade_confidence, 4)
            })

    # Sort by signal descending (strongest first)
    trades = sorted(trades, key=lambda x: x['trade_signal'], reverse=True)

    return trades

def generate_trades_cascading(trader_id, aggregate_signals, date_str):
    """
    Pair strongest bullish with strongest bearish, 2nd with 2nd, etc.

    This is the previous pairing logic (not currently used).

    Returns: List of trade dicts sorted by confidence (descending)
    """
    trades = []

    # Separate bullish and bearish signals
    bullish = sorted(
        [(c, conf) for c, (d, conf) in aggregate_signals.items() if d == 'bullish' and conf > 0],
        key=lambda x: x[1],
        reverse=True
    )

    bearish = sorted(
        [(c, conf) for c, (d, conf) in aggregate_signals.items() if d == 'bearish' and conf < 0],
        key=lambda x: abs(x[1]),
        reverse=True
    )

    # Pair strongest with strongest
    for i in range(min(len(bullish), len(bearish))):
        buy_currency, buy_conf = bullish[i]
        sell_currency, sell_conf = bearish[i]

        trade_confidence = (abs(buy_conf) + abs(sell_conf)) / 2.0

        trades.append({
            'trader_id': trader_id,
            'date': date_str,
            'buy_currency': buy_currency,
            'sell_currency': sell_currency,
            'buy_confidence': round(buy_conf, 4),
            'sell_confidence': round(sell_conf, 4),
            'trade_confidence': round(trade_confidence, 4)
        })

    # Already sorted by pairing order (strongest first)
    return trades

def main():
    """Calculate trades for all traders"""
    parser = argparse.ArgumentParser(description='Calculate trades for traders (Step 8)')
    parser.add_argument('--date', help='Date filter (YYYY-MM-DD) - uses data from this date')
    args = parser.parse_args()

    logger = PipelineLogger('step8', 'Calculate Trades')
    logger.start()

    date_str = args.date if args.date else None

    # Validate upstream data (Step 7: Aggregated Signals)
    step7_csv = '/workspace/group/fx-portfolio/data/aggregated-signals/aggregated_signals.csv'
    if not os.path.exists(step7_csv):
        logger.error("Step 7 output not found. Run Step 7 (Aggregate Signals) first.")
        logger.fail()
        sys.exit(1)

    print(f"\n{'='*60}")
    print("Validating Upstream Data (Step 7)")
    print(f"{'='*60}")
    print(f"  ✓ Found Step 7 aggregated signals: {step7_csv}")

    # If date specified, verify Step 7 has data for that date
    if date_str:
        dates_in_step7 = set()
        with open(step7_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dates_in_step7.add(row['date'])

        if date_str not in dates_in_step7:
            logger.error(f"Step 7 has no data for {date_str}. Available dates: {sorted(dates_in_step7)}")
            logger.fail()
            sys.exit(1)

        print(f"  ✓ Step 7 has data for {date_str}")

    # Load traders
    traders = get_traders()
    trader_list = list(traders.items())

    logger.add_count('trader_count', len(trader_list))

    all_trades = []
    eur_rates = None
    all_pairs = None

    for i, (trader_id, trader_config) in enumerate(trader_list, 1):
        trader_type = trader_config.get('type', 'combinator')
        estimator_ids = trader_config.get('estimator_ids', [])
        generator_ids = trader_config.get('generator_ids', [])
        generator_weights = trader_config.get('generator_weights', {})

        print(f"\n[{i}/{len(trader_list)}] Calculating trades: {trader_id}")
        print(f"  type={trader_type}")
        print(f"  estimators={estimator_ids}")
        print(f"  generators={generator_ids}")

        # Load aggregated signals from Step 7
        aggregated_by_currency, actual_date = load_aggregated_signals(date_str, generator_ids, estimator_ids)

        # Use actual date for all trades (first trader sets it, all should be same)
        if i == 1:
            date_str = actual_date
            print(f"  Using data date: {date_str}")

            # Load price data for the determined date
            eur_rates, all_pairs = load_latest_prices(date_str)
            if not eur_rates or not all_pairs:
                logger.error(f"No price data available for {date_str}")
                logger.fail()
                return

        # Combine aggregated signals (if multiple generator/estimator combos for same currency)
        aggregate_signals = {}
        for currency, agg_signals in aggregated_by_currency.items():
            direction, confidence, volume = combine_aggregated_signals(
                agg_signals,
                generator_weights=generator_weights
            )
            aggregate_signals[currency] = (direction, confidence)

        # Generate trades based on trader type
        if trader_type == 'combinator':
            trades = generate_trades_combinator(trader_id, aggregate_signals, date_str)
        elif trader_type == 'cascading':
            trades = generate_trades_cascading(trader_id, aggregate_signals, date_str)
        else:
            logger.error(f"Unknown trader type: {trader_type}")
            trades = []

        all_trades.extend(trades)
        print(f"  Generated trades: {len(trades)}")

    # Save to CSV
    output_dir = '/workspace/group/fx-portfolio/data/trades'
    os.makedirs(output_dir, exist_ok=True)

    csv_file = f'{output_dir}/trades.csv'

    if all_trades:
        fieldnames = [
            'date', 'trader_id', 'buy_currency', 'sell_currency',
            'buy_signal', 'sell_signal', 'trade_signal'
        ]

        # Safely handle appending vs overwriting based on dates
        file_exists = os.path.exists(csv_file)

        if not date_str:
            logger.error("CRITICAL: date_str is None when writing CSV!")
            raise ValueError("date_str must be set before writing trades CSV")

        if file_exists:
            # Read existing data
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)

            # Filter out any existing rows for this date (we're replacing them)
            other_date_rows = [row for row in existing_rows if row.get('date') != date_str]

            # Write everything: other dates + new trades for current date
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(other_date_rows)
                writer.writerows(all_trades)
        else:
            # New file - just write the trades
            with open(csv_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_trades)

        logger.add_count('total_trades', len(all_trades))
        logger.add_info('output_csv', csv_file)

        print(f"\n{'='*60}")
        print(f"✓ Calculated {len(all_trades)} trades across {len(trader_list)} traders")
        print(f"CSV: {csv_file}")
        print(f"{'='*60}")
    else:
        # Write empty CSV with headers
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'date', 'trader_id', 'buy_currency', 'sell_currency',
                'buy_signal', 'sell_signal', 'trade_signal'
            ])
            writer.writeheader()

        print(f"\n{'='*60}")
        print(f"⚠️  No trades generated (no qualifying bull/bear pairs)")
        print(f"CSV: {csv_file}")
        print(f"{'='*60}")

    logger.success()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        logger = PipelineLogger('step8', 'Calculate Trades')
        logger.finish()
