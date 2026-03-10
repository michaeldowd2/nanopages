#!/usr/bin/env python3
"""
Step 8: Trade Calculator

Generates trade recommendations based on trader configurations.
Traders define HOW to generate trades from aggregated signals (inputs, weighting, pairing logic).

Trader Types:
- "combinator": Generates ALL combinations of bullish/bearish currency pairs
- "cascading": Pairs strongest bull with strongest bear, 2nd with 2nd, etc.

Reads from Processes 1 and 7 CSVs, writes to Process 8 CSV.

Input:
- data/aggregated-signals/{date}.csv (from Process 7)
- data/prices/{date}.csv (from Process 1, for validation)

Output: data/trades/{date}.csv
"""

import os
import sys
import argparse
from datetime import datetime

sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.pipeline_logger import PipelineLogger
from utilities.csv_helper import read_csv, write_csv
from utilities.config_loader import get_traders, get_currencies

CURRENCIES = get_currencies()


def combine_aggregated_signals(aggregated_signals, generator_weights=None):
    """
    Combine multiple aggregated signals (from different generator/estimator combinations)
    for a single currency using weighted averaging.

    Returns: (direction, avg_signal, total_count)
    """
    if not aggregated_signals:
        return 'neutral', 0.0, 0

    weighted_scores = []
    total_weight = 0.0
    total_signal_count = 0

    for agg_sig in aggregated_signals:
        # avg_signal is SIGNED (positive=bullish, negative=bearish)
        signed_signal = float(agg_sig.get('avg_signal', 0.0))
        signal_count = int(agg_sig.get('count', 0))
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

    # Determine final direction
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
    Trade signal = average of abs(buy_signal) and abs(sell_signal)

    Returns: List of trade dicts sorted by trade_signal (descending)
    """
    trades = []

    # Separate bullish and bearish signals
    bullish = []
    bearish = []

    for curr, (direction, signal) in aggregate_signals.items():
        if direction == 'bullish' and signal > 0:
            bullish.append((curr, signal))
        elif direction == 'bearish' and signal < 0:
            bearish.append((curr, signal))

    # Generate ALL combinations
    for buy_currency, buy_signal in bullish:
        for sell_currency, sell_signal in bearish:
            # Trade signal is average of absolute values
            trade_signal = (abs(buy_signal) + abs(sell_signal)) / 2.0

            trades.append({
                'date': date_str,
                'trader_id': trader_id,
                'buy_currency': buy_currency,
                'sell_currency': sell_currency,
                'buy_signal': round(buy_signal, 4),
                'sell_signal': round(sell_signal, 4),
                'trade_signal': round(trade_signal, 4)
            })

    # Sort by trade_signal descending (strongest first)
    trades = sorted(trades, key=lambda x: x['trade_signal'], reverse=True)

    return trades


def generate_trades_cascading(trader_id, aggregate_signals, date_str):
    """
    Pair strongest bullish with strongest bearish, 2nd with 2nd, etc.

    Returns: List of trade dicts sorted by trade_signal (descending)
    """
    trades = []

    # Separate and sort bullish/bearish signals
    bullish = sorted(
        [(c, signal) for c, (d, signal) in aggregate_signals.items() if d == 'bullish' and signal > 0],
        key=lambda x: x[1],
        reverse=True
    )

    bearish = sorted(
        [(c, signal) for c, (d, signal) in aggregate_signals.items() if d == 'bearish' and signal < 0],
        key=lambda x: abs(x[1]),
        reverse=True
    )

    # Pair strongest with strongest
    for i in range(min(len(bullish), len(bearish))):
        buy_currency, buy_signal = bullish[i]
        sell_currency, sell_signal = bearish[i]

        trade_signal = (abs(buy_signal) + abs(sell_signal)) / 2.0

        trades.append({
            'date': date_str,
            'trader_id': trader_id,
            'buy_currency': buy_currency,
            'sell_currency': sell_currency,
            'buy_signal': round(buy_signal, 4),
            'sell_signal': round(sell_signal, 4),
            'trade_signal': round(trade_signal, 4)
        })

    return trades


def main(date_str=None):
    """Calculate trades for all traders"""

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    logger = PipelineLogger('step8', 'Calculate Trades')
    logger.start()

    try:
        print("="*60)
        print("Trade Calculator - CSV Output")
        print("="*60)
        print(f"\nProcessing date: {date_str}")

        # Load aggregated signals from Process 7
        print(f"\n1. Loading aggregated signals from Process 7...")
        try:
            aggregated_rows = read_csv('process_7_aggregated_signals', date=date_str, validate=False)
            print(f"   ✓ Loaded {len(aggregated_rows)} aggregated signal groups")
            logger.add_count('aggregated_groups_loaded', len(aggregated_rows))
        except FileNotFoundError:
            print(f"   ✗ No aggregated signals found for {date_str}")
            print(f"   Step 7 (Aggregate Signals) must be run first")
            logger.error(f"Missing upstream data: process_7_aggregated_signals for {date_str}")
            logger.fail()
            return

        # Load traders
        traders = get_traders()
        trader_list = list(traders.items())

        print(f"\n2. Processing {len(trader_list)} traders...")
        logger.add_count('trader_count', len(trader_list))

        all_trades = []

        for i, (trader_id, trader_config) in enumerate(trader_list, 1):
            trader_type = trader_config.get('type', 'combinator')
            estimator_ids = trader_config.get('estimator_ids', [])
            generator_ids = trader_config.get('generator_ids', [])
            generator_weights = trader_config.get('generator_weights', {})

            print(f"\n   [{i}/{len(trader_list)}] Trader: {trader_id}")
            print(f"      Type: {trader_type}")
            print(f"      Estimators: {estimator_ids}")
            print(f"      Generators: {generator_ids}")

            # Filter aggregated signals by trader's generator and estimator IDs
            filtered_rows = []
            for row in aggregated_rows:
                # Filter by generator
                if generator_ids and row['generator_id'] not in generator_ids:
                    continue

                # Filter by estimator
                if estimator_ids and row['estimator_id'] not in estimator_ids:
                    continue

                filtered_rows.append(row)

            # Group by currency
            aggregated_by_currency = {}
            for currency in CURRENCIES:
                aggregated_by_currency[currency] = []

            for row in filtered_rows:
                currency = row['currency']
                if currency in CURRENCIES:
                    aggregated_by_currency[currency].append(row)

            # Combine aggregated signals for each currency
            aggregate_signals = {}
            for currency, agg_signals in aggregated_by_currency.items():
                direction, signal, count = combine_aggregated_signals(
                    agg_signals,
                    generator_weights=generator_weights
                )
                aggregate_signals[currency] = (direction, signal)

            # Generate trades based on trader type
            if trader_type == 'combinator':
                trades = generate_trades_combinator(trader_id, aggregate_signals, date_str)
            elif trader_type == 'cascading':
                trades = generate_trades_cascading(trader_id, aggregate_signals, date_str)
            else:
                print(f"      ⚠ Unknown trader type: {trader_type}")
                trades = []

            all_trades.extend(trades)
            print(f"      Generated: {len(trades)} trades")

        logger.add_count('total_trades', len(all_trades))

        # Write to CSV
        print(f"\n3. Saving to CSV...")
        if all_trades:
            csv_path = write_csv(all_trades, 'process_8_trades', date=date_str)
            print(f"   ✓ Saved {len(all_trades)} trades to {csv_path}")
            logger.add_info('output_file', str(csv_path))
        else:
            # Write empty CSV
            csv_path = write_csv([], 'process_8_trades', date=date_str)
            print(f"   ⚠ No trades generated (no qualifying bull/bear pairs)")
            logger.warning("No trades generated")

        # Summary
        print(f"\n{'='*60}")
        print(f"✓ Trade Calculation Complete")
        print(f"{'='*60}")
        print(f"  Traders processed: {len(trader_list)}")
        print(f"  Total trades: {len(all_trades)}")

        logger.success()

    except Exception as e:
        logger.error(f"Failed to calculate trades: {e}")
        logger.fail()
        raise
    finally:
        logger.finish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate trades for traders')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD), defaults to today')
    args = parser.parse_args()

    main(date_str=args.date)
