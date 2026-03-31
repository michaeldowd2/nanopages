#!/usr/bin/env python3
"""
Step 10: Calculate Account Balances

Reads executed trades from Step 9 and updates portfolio account balances.
Each strategy maintains its own portfolio state across dates.

Design:
- Start with 100 EUR in each currency if no prior portfolio state exists
- Load previous date's portfolio state from CSV to continue
- Read executed trades from Step 9 CSV (sell_amount, buy_amount, sell_currency, buy_currency)
- Apply trades to update portfolio balances
- Track portfolio balances over time

This process simply applies the pre-calculated trade amounts from Process 9,
without re-executing any trade logic. All trade calculations happen in Process 9.

Input:
- data/executed-trades/{date}.csv (from Process 9)
- data/prices/{date}.csv (from Process 1, for initialization only)
- data/portfolios/{previous_date}.csv (from previous run of Process 10)

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
        rows = read_csv('process_10_portfolio', date=prev_date, validate=False)

        # Find row for this strategy
        for row in rows:
            if row['strategy_id'] == strategy_id:
                portfolio = {}
                for currency in CURRENCIES:
                    col_name = currency.lower() + '_acc_val'
                    if col_name in row:
                        portfolio[currency] = float(row[col_name])
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
    """Calculate updated account balances from executed trades"""

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    logger = PipelineLogger('step10', 'Calculate Account Balances')
    logger.start()

    try:
        print("="*60)
        print("Account Balance Calculator - CSV Output")
        print("="*60)
        print(f"\nProcessing date: {date_str}")

        # Load exchange rates from Process 1 (needed for initialization only)
        print(f"\n1. Loading exchange rates from Process 1...")
        eur_rates, all_pairs = load_exchange_rates(date_str)
        if not eur_rates or not all_pairs:
            print(f"   ✗ No exchange rates found for {date_str}")
            print(f"   Step 1 (Fetch Exchange Rates) must be run first")
            logger.error(f"Missing upstream data: process_1_exchange_rates for {date_str}")
            logger.fail()
            return

        print(f"   ✓ Loaded {len(eur_rates)} EUR rates")

        # Load executed trades from Process 9
        print(f"\n2. Loading executed trades from Process 9...")
        try:
            executed_trades_rows = read_csv('process_9_executed_trades', date=date_str, validate=False)
            print(f"   ✓ Loaded {len(executed_trades_rows)} executed trades")
            logger.add_count('executed_trades_loaded', len(executed_trades_rows))
        except FileNotFoundError:
            print(f"   ✗ No executed trades found for {date_str}")
            print(f"   Step 9 (Execute Trades) must be run first")
            logger.error(f"Missing upstream data: process_9_executed_trades for {date_str}")
            logger.fail()
            return

        # Load strategies
        strategies = get_strategies()
        print(f"\n3. Updating balances for {len(strategies)} strategies...")
        logger.add_count('strategy_count', len(strategies))

        # Get previous date for loading portfolio state
        prev_date = get_previous_date(date_str)

        # Group executed trades by strategy
        trades_by_strategy = {}
        for trade in executed_trades_rows:
            strategy_id = trade['strategy_id']
            if strategy_id not in trades_by_strategy:
                trades_by_strategy[strategy_id] = []
            trades_by_strategy[strategy_id].append(trade)

        results = []
        total_trades_applied = 0

        for i, (strategy_id, strategy_config) in enumerate(strategies.items(), 1):
            params = strategy_config.get('params', {})
            trader_id = params.get('trader_id', 'combinator-standard')

            print(f"\n   [{i}/{len(strategies)}] Strategy: {strategy_id}")

            # Load portfolio state from previous date or initialize
            portfolio = load_previous_portfolio(strategy_id, prev_date)

            if portfolio is None:
                print(f"      Initializing new portfolio with {INITIAL_BALANCE_PER_CURRENCY} EUR per currency")
                portfolio = initialize_portfolio(eur_rates)
            else:
                print(f"      Loaded portfolio from {prev_date}")

            # Apply executed trades for this strategy
            strategy_trades = trades_by_strategy.get(strategy_id, [])

            for trade in strategy_trades:
                sell_curr = trade['sell_currency']
                buy_curr = trade['buy_currency']
                sell_amount = float(trade['sell_amount'])
                buy_amount = float(trade['buy_amount'])

                # Update balances
                portfolio[sell_curr] -= sell_amount
                portfolio[buy_curr] = portfolio.get(buy_curr, 0) + buy_amount

            print(f"      Applied {len(strategy_trades)} trades")
            total_trades_applied += len(strategy_trades)

            # Build result record
            result = {
                'date': date_str,
                'strategy_id': strategy_id,
                'trader_id': trader_id,
                'trades_executed': len(strategy_trades)
            }

            # Add currency balances
            for curr in CURRENCIES:
                result[curr.lower() + '_acc_val'] = round(portfolio.get(curr, 0.0), 4)

            results.append(result)

        logger.add_count('total_trades_applied', total_trades_applied)

        # Write to CSV
        print(f"\n4. Saving to CSV...")
        csv_path = write_csv(results, 'process_10_portfolio', date=date_str)
        print(f"   ✓ Saved {len(results)} portfolio states to {csv_path}")
        logger.add_info('output_file', str(csv_path))

        # Validation checks
        print(f"\n5. Running validation checks...")
        validation_warnings = []

        if total_trades_applied > 0:
            # Check if balances changed from previous day
            if prev_date:
                prev_portfolios = {}
                try:
                    prev_rows = read_csv('process_10_portfolio', date=prev_date, validate=False)
                    for row in prev_rows:
                        prev_portfolios[row['strategy_id']] = {curr.lower() + '_acc_val': float(row[curr.lower() + '_acc_val']) for curr in CURRENCIES}
                except:
                    pass  # Previous day might not exist

                if prev_portfolios:
                    unchanged_count = 0
                    for result in results:
                        strategy_id = result['strategy_id']
                        if strategy_id in prev_portfolios:
                            prev = prev_portfolios[strategy_id]
                            current = {curr: result[curr.lower() + '_acc_val'] for curr in CURRENCIES}
                            # Check if all balances are identical
                            if all(abs(prev[curr.lower() + '_acc_val'] - current[curr]) < 0.0001 for curr in CURRENCIES):
                                unchanged_count += 1

                    if unchanged_count > 0:
                        warning = f"⚠️  WARNING: {unchanged_count} portfolios have identical balances to previous day despite {total_trades_applied} trades executed"
                        print(f"   {warning}")
                        validation_warnings.append(warning)
                        logger.add_info('validation_warning', warning)
                    else:
                        print(f"   ✓ All portfolio balances changed from previous day")

        # Summary
        print(f"\n{'='*60}")
        print(f"✓ Account Balance Calculation Complete")
        print(f"{'='*60}")
        print(f"  Strategies processed: {len(results)}")
        print(f"  Total trades applied: {total_trades_applied}")
        if validation_warnings:
            print(f"\n  Validation Warnings: {len(validation_warnings)}")
            for warning in validation_warnings:
                print(f"    - {warning}")

        logger.success()

    except Exception as e:
        logger.error(f"Failed to calculate account balances: {e}")
        logger.fail()
        raise
    finally:
        logger.finish()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Execute portfolio strategies')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD), defaults to today')
    args = parser.parse_args()

    main(date_str=args.date)
