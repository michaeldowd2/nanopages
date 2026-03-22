#!/usr/bin/env python3
"""
Step 9: Execute Trades

Executes the actual trades for each portfolio strategy, calculating exact
currency amounts bought and sold with spreads applied. This is the definitive
trade execution logic that Process 10 (Account Balances) uses as input.

Design:
- Load proposed trades from Step 8
- Load previous portfolio states from Step 10 (previous day)
- Sort trades by confidence and select top N per strategy
- Calculate exact trade amounts based on current balances
- Apply spreads (0.74%) and calculate buy/sell amounts
- Output one row per executed trade with full details

This process feeds into Step 10 which updates account balances.

Input:
- data/trades/{date}.csv (from Process 8)
- data/prices/{date}.csv (from Process 1)
- data/portfolios/{previous_date}.csv (from Process 10, previous day)

Output: data/executed-trades/{date}.csv
"""

import os
import sys
import argparse
from datetime import datetime, timedelta

sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.pipeline_logger import PipelineLogger
from utilities.csv_helper import read_csv, write_csv, csv_exists, get_previous_date
from utilities.config_loader import get_strategies, get_trader, get_currencies

CURRENCIES = get_currencies()

REVOLUT_SPREADS = {
    'default': 0.0074  # 0.74% total
}

INITIAL_BALANCE_PER_CURRENCY = 100.0  # EUR equivalent in each currency


def load_exchange_rates(date_str):
    """Load exchange rates from Process 1 for a specific date"""
    try:
        rates_rows = read_csv('process_1_exchange_rates', date=date_str, validate=False)

        # Build eur_rates dict (EUR/XXX rates)
        eur_rates = {}
        for row in rates_rows:
            if row['base_currency'] == 'EUR':
                eur_rates[row['quote_currency']] = float(row['rate'])

        # Build all_pairs dict (all currency pairs)
        all_pairs = {}
        for row in rates_rows:
            base = row['base_currency']
            quote = row['quote_currency']
            rate = float(row['rate'])

            if base not in all_pairs:
                all_pairs[base] = {}
            all_pairs[base][quote] = rate

        return eur_rates, all_pairs

    except FileNotFoundError:
        return None, None


def load_previous_portfolio(strategy_id, prev_date):
    """
    Load most recent portfolio state for a strategy from previous date CSV.

    Returns: Dict of {currency: balance} or None if not found
    """
    if not prev_date:
        return None

    try:
        rows = read_csv('process_10_portfolio', date=prev_date, validate=False)

        # Find row for this strategy
        for row in rows:
            if row['strategy_id'] == strategy_id:
                portfolio = {}
                for currency in CURRENCIES:
                    if currency in row:
                        portfolio[currency] = float(row[currency])
                    else:
                        portfolio[currency] = 0.0
                return portfolio

        return None

    except FileNotFoundError:
        return None


def initialize_portfolio(eur_rates):
    """
    Initialize portfolio with 100 EUR equivalent in each currency.

    Returns: Dict of {currency: amount}
    """
    portfolio = {}

    for currency in CURRENCIES:
        if currency == 'EUR':
            portfolio[currency] = INITIAL_BALANCE_PER_CURRENCY
        else:
            rate = eur_rates.get(currency)
            if rate:
                # EUR/CURRENCY rate, so CURRENCY amount = EUR amount * rate
                portfolio[currency] = INITIAL_BALANCE_PER_CURRENCY * rate
            else:
                portfolio[currency] = 0.0

    return portfolio


def calculate_portfolio_value(portfolio, eur_rates):
    """Calculate total portfolio value in EUR"""
    total_eur = 0.0

    for currency, amount in portfolio.items():
        if amount <= 0:
            continue

        if currency == 'EUR':
            total_eur += amount
        else:
            rate = eur_rates.get(currency)
            if rate:
                total_eur += amount / rate

    return round(total_eur, 2)


def execute_trade_with_details(trade, all_pairs, eur_rates, portfolio, max_trade_size_pct, confidence_threshold,
                                 strategy_id, date_str):
    """
    Execute a single trade and return full execution details.

    Trade size is calculated as:
    - portfolio_value * max_trade_size_pct * trade_signal

    Only executes if trade_signal >= confidence_threshold

    Returns: Dict with full execution details or None if failed
    """
    buy_curr = trade['buy_currency']
    sell_curr = trade['sell_currency']
    trade_signal = trade['trade_signal']

    # Check if trade meets confidence threshold
    if trade_signal < confidence_threshold:
        return None

    # Check available balance in sell_currency (converted to EUR)
    sell_balance = portfolio.get(sell_curr, 0)

    if sell_balance <= 0:
        return None

    if sell_curr == 'EUR':
        sell_balance_eur = sell_balance
    else:
        sell_rate = eur_rates.get(sell_curr)
        if not sell_rate:
            return None
        sell_balance_eur = sell_balance / sell_rate

    # Calculate target trade size as a percentage of the SELL CURRENCY balance
    target_trade_size_eur = sell_balance_eur * max_trade_size_pct * trade_signal

    # The actual trade size is the target
    actual_trade_size_eur = target_trade_size_eur

    # Convert EUR trade size to sell_currency amount
    if sell_curr == 'EUR':
        sell_amount = actual_trade_size_eur
    else:
        sell_rate = eur_rates.get(sell_curr)
        if not sell_rate:
            return None
        sell_amount = actual_trade_size_eur * sell_rate

    # Get exchange rate sell_curr -> buy_curr
    if sell_curr not in all_pairs or buy_curr not in all_pairs[sell_curr]:
        return None

    pair_rate = all_pairs[sell_curr][buy_curr]

    # Calculate buy amount before spread
    buy_amount_before_spread = sell_amount * pair_rate

    # Apply spread (0.74%)
    spread = REVOLUT_SPREADS['default']
    buy_amount_after_spread = buy_amount_before_spread * (1 - spread)

    # Calculate cost in EUR
    if buy_curr == 'EUR':
        buy_value_eur = buy_amount_after_spread
    else:
        buy_rate = eur_rates.get(buy_curr)
        if not buy_rate:
            return None
        buy_value_eur = buy_amount_after_spread / buy_rate

    cost_eur = actual_trade_size_eur - buy_value_eur

    # Update portfolio balances
    portfolio[sell_curr] -= sell_amount
    portfolio[buy_curr] = portfolio.get(buy_curr, 0) + buy_amount_after_spread

    return {
        'date': date_str,
        'strategy_id': strategy_id,
        'trader_id': trade.get('trader_id', 'unknown'),
        'sell_currency': sell_curr,
        'buy_currency': buy_curr,
        'sell_amount': round(sell_amount, 4),
        'buy_amount': round(buy_amount_after_spread, 4),
        'exchange_rate': round(pair_rate, 6),
        'spread_pct': spread,
        'trade_size_eur': round(actual_trade_size_eur, 2),
        'cost_eur': round(cost_eur, 2),
        'trade_signal': trade['trade_signal']
    }


def main(date_str=None):
    """Extract executed trades for all strategies"""

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    logger = PipelineLogger('step8_1', 'Extract Executed Trades')
    logger.start()

    try:
        print("="*60)
        print("Executed Trades Extractor - CSV Output")
        print("="*60)
        print(f"\nProcessing date: {date_str}")

        # Load exchange rates from Process 1
        print(f"\n1. Loading exchange rates from Process 1...")
        eur_rates, all_pairs = load_exchange_rates(date_str)
        if not eur_rates or not all_pairs:
            print(f"   ✗ No exchange rates found for {date_str}")
            print(f"   Step 1 (Fetch Exchange Rates) must be run first")
            logger.error(f"Missing upstream data: process_1_exchange_rates for {date_str}")
            logger.fail()
            return

        print(f"   ✓ Loaded {len(eur_rates)} EUR rates and {sum(len(v) for v in all_pairs.values())} total pairs")

        # Load trades from Process 8
        print(f"\n2. Loading trades from Process 8...")
        try:
            trades_rows = read_csv('process_8_trades', date=date_str, validate=False)
            print(f"   ✓ Loaded {len(trades_rows)} proposed trades")
            logger.add_count('trades_loaded', len(trades_rows))
        except FileNotFoundError:
            print(f"   ✗ No trades found for {date_str}")
            print(f"   Step 8 (Calculate Trades) must be run first")
            logger.error(f"Missing upstream data: process_8_trades for {date_str}")
            logger.fail()
            return

        # Load strategies
        strategies = get_strategies()
        print(f"\n3. Extracting executed trades for {len(strategies)} strategies...")
        logger.add_count('strategy_count', len(strategies))

        # Get previous date for loading portfolio state
        prev_date = get_previous_date(date_str)

        all_executed_trades = []
        total_trades_extracted = 0

        for i, (strategy_id, strategy_config) in enumerate(strategies.items(), 1):
            params = strategy_config.get('params', {})
            trader_id = params.get('trader_id', 'combinator-standard')
            conf_threshold = params.get('confidence_threshold', 0.5)
            max_trade_size_pct = params.get('trade_size_pct', 0.1)
            target_trades = params.get('target_trades', None)

            print(f"\n   [{i}/{len(strategies)}] Strategy: {strategy_id}")

            # Load portfolio state from previous date or initialize
            portfolio = load_previous_portfolio(strategy_id, prev_date)

            if portfolio is None:
                portfolio = initialize_portfolio(eur_rates)
                print(f"      Initialized new portfolio")
            else:
                print(f"      Loaded portfolio from {prev_date}")

            # Calculate initial portfolio value
            portfolio_value = calculate_portfolio_value(portfolio, eur_rates)

            # Filter trades for this trader
            trader_trades = [
                {
                    'buy_currency': row['buy_currency'],
                    'sell_currency': row['sell_currency'],
                    'buy_signal': float(row['buy_signal']),
                    'sell_signal': float(row['sell_signal']),
                    'trade_signal': float(row['trade_signal']),
                    'trader_id': row['trader_id']
                }
                for row in trades_rows if row['trader_id'] == trader_id
            ]

            # Sort by trade_signal descending
            trader_trades.sort(key=lambda x: x['trade_signal'], reverse=True)

            # Filter by confidence threshold
            qualifying_trades = [t for t in trader_trades if t['trade_signal'] >= conf_threshold]

            # Limit to target number
            if target_trades is not None:
                trades_to_execute = qualifying_trades[:target_trades]
            else:
                trades_to_execute = qualifying_trades

            # Execute trades and capture details
            for trade in trades_to_execute:
                execution = execute_trade_with_details(
                    trade, all_pairs, eur_rates, portfolio, max_trade_size_pct,
                    conf_threshold, strategy_id, date_str
                )
                if execution:
                    all_executed_trades.append(execution)

            print(f"      Extracted {len([t for t in all_executed_trades if t['strategy_id'] == strategy_id])} trades")
            total_trades_extracted += len([t for t in all_executed_trades if t['strategy_id'] == strategy_id])

        logger.add_count('total_trades_extracted', total_trades_extracted)

        # Write to CSV
        print(f"\n4. Saving to CSV...")
        if all_executed_trades:
            csv_path = write_csv(all_executed_trades, '9', date=date_str)
            print(f"   ✓ Saved {len(all_executed_trades)} executed trades to {csv_path}")
            logger.add_info('output_file', str(csv_path))
        else:
            print(f"   ⚠ No trades executed (creating empty file)")
            csv_path = write_csv([], '9', date=date_str)
            logger.add_info('output_file', str(csv_path))

        # Summary
        print(f"\n{'='*60}")
        print(f"✓ Trade Extraction Complete")
        print(f"{'='*60}")
        print(f"  Strategies processed: {len(strategies)}")
        print(f"  Total executed trades: {total_trades_extracted}")

        logger.success()

    except Exception as e:
        logger.error(f"Failed to extract executed trades: {e}")
        logger.fail()
        raise
    finally:
        logger.finish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract executed trades for all strategies')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD), defaults to today')
    args = parser.parse_args()

    main(date_str=args.date)
