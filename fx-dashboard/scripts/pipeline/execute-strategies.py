#!/usr/bin/env python3
"""
Step 9: Portfolio Executor

Reads proposed trades from Step 8 and executes them on strategy portfolios.
Each strategy maintains its own portfolio state across dates.

Design:
- Start with 100 EUR in each currency if no prior portfolio state exists
- Load previous date's portfolio state from CSV to continue
- Read trades from Step 8 CSV (buy_currency, sell_currency, trade_signal)
- Execute trades above threshold in descending order of confidence
- Apply spreads (0.74%) when converting currencies
- Track portfolio balances and values over time

Reads from Processes 1 and 8 CSVs, writes to Process 9 CSV.

Input:
- data/trades/{date}.csv (from Process 8)
- data/prices/{date}.csv (from Process 1)
- data/portfolios/{date}.csv (from previous run of Process 9)

Output: data/portfolios/{date}.csv
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
        rows = read_csv('process_9_portfolio', date=prev_date, validate=False)

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


def execute_trade(trade, all_pairs, eur_rates, portfolio, max_trade_size_pct, confidence_threshold):
    """
    Execute a single trade: sell sell_currency, buy buy_currency.

    Trade size is calculated as:
    - portfolio_value * max_trade_size_pct * trade_signal

    Only executes if trade_signal >= confidence_threshold

    Returns: Dict with execution details or None if failed
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
        'sell_currency': sell_curr,
        'buy_currency': buy_curr,
        'sell_amount': round(sell_amount, 4),
        'buy_amount': round(buy_amount_after_spread, 4),
        'trade_size_eur': round(actual_trade_size_eur, 2),
        'cost_eur': round(cost_eur, 2),
        'exchange_rate': round(pair_rate, 6),
        'buy_signal': trade['buy_signal'],
        'sell_signal': trade['sell_signal'],
        'trade_signal': trade['trade_signal']
    }


def main(date_str=None):
    """Execute portfolio strategies"""

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    logger = PipelineLogger('step9', 'Execute Portfolio Strategies')
    logger.start()

    try:
        print("="*60)
        print("Portfolio Executor - CSV Output")
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
        print(f"\n3. Executing {len(strategies)} strategies...")
        logger.add_count('strategy_count', len(strategies))

        # Get previous date for loading portfolio state
        prev_date = get_previous_date(date_str)

        results = []
        total_trades_executed = 0

        for i, (strategy_id, strategy_config) in enumerate(strategies.items(), 1):
            params = strategy_config.get('params', {})
            trader_id = params.get('trader_id', 'combinator-standard')
            conf_threshold = params.get('confidence_threshold', 0.5)
            max_trade_size_pct = params.get('trade_size_pct', 0.1)
            target_trades = params.get('target_trades', None)

            print(f"\n   [{i}/{len(strategies)}] Strategy: {strategy_id}")
            print(f"      Trader: {trader_id}")
            print(f"      Confidence threshold: {conf_threshold}")
            print(f"      Target trades: {target_trades if target_trades else 'unlimited'}")
            print(f"      Max trade size: {max_trade_size_pct * 100}% of balance")

            # Load portfolio state from previous date or initialize
            portfolio = load_previous_portfolio(strategy_id, prev_date)

            if portfolio is None:
                print(f"      Initializing new portfolio with {INITIAL_BALANCE_PER_CURRENCY} EUR per currency")
                portfolio = initialize_portfolio(eur_rates)
            else:
                prev_value = calculate_portfolio_value(portfolio, eur_rates)
                print(f"      Loaded portfolio from {prev_date} (value: €{prev_value:.2f})")

            # Filter trades for this trader
            trader_trades = [
                {
                    'buy_currency': row['buy_currency'],
                    'sell_currency': row['sell_currency'],
                    'buy_signal': float(row['buy_signal']),
                    'sell_signal': float(row['sell_signal']),
                    'trade_signal': float(row['trade_signal'])
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

            # Execute trades
            executed_trades = []
            for trade in trades_to_execute:
                execution = execute_trade(trade, all_pairs, eur_rates, portfolio, max_trade_size_pct, conf_threshold)
                if execution:
                    executed_trades.append(execution)

            # Calculate portfolio value
            portfolio_value = calculate_portfolio_value(portfolio, eur_rates)

            print(f"      Portfolio value: €{portfolio_value:.2f}")
            print(f"      Executed trades: {len(executed_trades)}")

            # Build result record
            result = {
                'date': date_str,
                'strategy_id': strategy_id,
                'trader_id': trader_id,
                'trades_executed': len(executed_trades),
                'portfolio_value': portfolio_value
            }

            # Add currency balances
            for curr in CURRENCIES:
                result[curr] = round(portfolio.get(curr, 0.0), 4)

            results.append(result)
            total_trades_executed += len(executed_trades)

        logger.add_count('total_trades_executed', total_trades_executed)

        # Write to CSV
        print(f"\n4. Saving to CSV...")
        csv_path = write_csv(results, 'process_9_portfolio', date=date_str)
        print(f"   ✓ Saved {len(results)} portfolio states to {csv_path}")
        logger.add_info('output_file', str(csv_path))

        # Summary
        print(f"\n{'='*60}")
        print(f"✓ Portfolio Execution Complete")
        print(f"{'='*60}")
        print(f"  Strategies executed: {len(results)}")
        print(f"  Total trades: {total_trades_executed}")

        logger.success()

    except Exception as e:
        logger.error(f"Failed to execute strategies: {e}")
        logger.fail()
        raise
    finally:
        logger.finish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Execute portfolio strategies')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD), defaults to today')
    args = parser.parse_args()

    main(date_str=args.date)
