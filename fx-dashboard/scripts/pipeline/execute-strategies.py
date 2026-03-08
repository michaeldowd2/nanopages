#!/usr/bin/env python3
"""
Portfolio Executor (Step 9)

Reads proposed trades from Step 8 and executes them on strategy portfolios.
Each strategy maintains its own portfolio state across dates.

Design:
- Start with 100 EUR in each currency if no prior portfolio state exists
- Load previous date's portfolio state from CSV to continue
- Read trades from Step 8 CSV (buy_currency, sell_currency, trade_signal, above_threshold)
- Execute trades above threshold in descending order of confidence
- Apply spreads (0.74%) when converting currencies
- Track portfolio balances and values over time

Input: data/trades/trades.csv
Output: data/portfolios/strategies.csv (portfolio summary with balances)
"""

import json
import os
import glob
import sys
import argparse
import csv
from datetime import datetime, timedelta

sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.pipeline_logger import PipelineLogger
from utilities.config_loader import get_strategies, get_trader

CURRENCIES = ["EUR", "USD", "GBP", "JPY", "CHF", "AUD", "CAD", "NOK", "SEK", "CNY", "MXN"]

REVOLUT_SPREADS = {
    'default': 0.0074  # 0.74% total
}

INITIAL_BALANCE_PER_CURRENCY = 100.0  # EUR equivalent in each currency

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

def load_trades_from_step8(date_str, trader_id):
    """
    Load proposed trades for a specific date and trader from Step 8 CSV.

    Returns: List of trade dicts, sorted by trade_signal descending
    """
    csv_file = '/workspace/group/fx-portfolio/data/trades/trades.csv'

    if not os.path.exists(csv_file):
        return []

    trades = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['date'] == date_str and row['trader_id'] == trader_id:
                trades.append({
                    'buy_currency': row['buy_currency'],
                    'sell_currency': row['sell_currency'],
                    'buy_confidence': float(row['buy_signal']),
                    'sell_confidence': float(row['sell_signal']),
                    'trade_signal': float(row['trade_signal'])
                })

    # Sort by confidence descending (already sorted in Step 8, but just to be sure)
    trades.sort(key=lambda x: x['trade_signal'], reverse=True)

    return trades

def load_previous_portfolio_from_csv(strategy_id, csv_file, current_date):
    """
    Load most recent portfolio state for a strategy from CSV.
    Returns portfolio dict or None if not found.

    Args:
        strategy_id: The strategy to load state for
        csv_file: Path to strategies.csv
        current_date: Current date string (YYYY-MM-DD) to find previous entry

    Returns:
        Dict of {currency: balance} or None if no previous state
    """
    if not os.path.exists(csv_file):
        return None

    try:
        # Parse current date
        from datetime import datetime
        current_dt = datetime.fromisoformat(current_date)

        # Read CSV and find most recent row for this strategy before current date
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            matching_rows = []

            for row in reader:
                if row['strategy_id'] == strategy_id:
                    row_date = datetime.fromisoformat(row['date'])
                    if row_date < current_dt:
                        matching_rows.append(row)

            if not matching_rows:
                return None

            # Sort by date and get most recent
            matching_rows.sort(key=lambda x: x['date'], reverse=True)
            most_recent = matching_rows[0]

            # Extract currency balances
            portfolio = {}
            for currency in CURRENCIES:
                if currency in most_recent:
                    portfolio[currency] = float(most_recent[currency])
                else:
                    portfolio[currency] = 0.0

            return portfolio

    except Exception as e:
        print(f"  Warning: Could not load previous state from CSV: {e}")
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
    trade_conf = trade['trade_signal']

    # Check if trade meets confidence threshold
    if trade_conf < confidence_threshold:
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
    # This prevents draining currencies to zero (exponential decay)
    target_trade_size_eur = sell_balance_eur * max_trade_size_pct * trade_conf

    # The actual trade size is the target (no need for min() since it's already based on balance)
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
        'buy_confidence': trade['buy_confidence'],
        'sell_confidence': trade['sell_confidence'],
        'trade_signal': trade['trade_signal']
    }

# Removed combine_aggregated_signals and load_aggregated_signals_from_step7 functions
# These were only used for display purposes and were not used in actual trading logic
# Step 9 now relies solely on Step 8's trade recommendations (trade_signal)

def main():
    """Execute portfolio strategies"""
    parser = argparse.ArgumentParser(description='Execute portfolio strategies (Step 9)')
    parser.add_argument('--date', required=True, help='Date to process (YYYY-MM-DD)')
    args = parser.parse_args()

    logger = PipelineLogger('step9', 'Execute Portfolio Strategies')
    logger.start()

    date_str = args.date

    print(f"{'='*60}")
    print("Execute Portfolio Strategies")
    print(f"{'='*60}")
    print(f"Using data date: {date_str}\n")

    # Validate upstream data (Step 8)
    step8_csv = '/workspace/group/fx-portfolio/data/exports/step8_trades.csv'
    if not os.path.exists(step8_csv):
        logger.error("Step 8 output not found. Run Step 8 (Calculate Trades) first.")
        logger.fail()
        sys.exit(1)

    # Load exchange rates
    eur_rates, all_pairs = load_latest_prices(date_str)
    if not eur_rates or not all_pairs:
        logger.error(f"No price data available for {date_str}")
        logger.fail()
        sys.exit(1)

    # Load strategies
    strategies = get_strategies()

    results = []
    total_trades_executed = 0

    for strategy_id, strategy_config in strategies.items():
        params = strategy_config.get('params', {})
        trader_id = params.get('trader_id', 'combinator-standard')
        conf_threshold = params.get('confidence_threshold', 0.5)
        max_trade_size_pct = params.get('trade_size_pct', 0.1)
        target_trades = params.get('target_trades', None)  # None means unlimited

        print(f"[{strategy_id}]")
        print(f"  trader_id={trader_id}")
        print(f"  conf_threshold={conf_threshold} (trades must be above this)")
        if target_trades:
            print(f"  target_trades={target_trades} (execute top {target_trades} trades above threshold)")
        else:
            print(f"  target_trades=unlimited (execute all trades above threshold)")
        print(f"  max_trade_size_pct={max_trade_size_pct} (% of portfolio, scaled by signal strength)")

        # Load portfolio state from CSV or initialize new one
        csv_file = '/workspace/group/fx-portfolio/data/portfolios/strategies.csv'
        portfolio = load_previous_portfolio_from_csv(strategy_id, csv_file, date_str)

        if portfolio is None:
            # No prior state - initialize with 100 EUR equivalent in each currency
            # Total starting value = 1100 EUR (100 * 11 currencies)
            print(f"  Initializing new portfolio with {INITIAL_BALANCE_PER_CURRENCY} EUR in each currency (total ~1100 EUR)")
            portfolio = initialize_portfolio(eur_rates)
        else:
            # Calculate previous portfolio value for display
            prev_value = calculate_portfolio_value(portfolio, eur_rates)
            print(f"  Loading portfolio from previous date (value: €{prev_value:.2f})")

        # Load proposed trades from Step 8 (filtered by trader_id)
        proposed_trades = load_trades_from_step8(date_str, trader_id)

        # Filter trades by confidence threshold
        qualifying_trades = [t for t in proposed_trades if t['trade_signal'] >= conf_threshold]

        # Limit to target number of trades if specified
        if target_trades is not None:
            trades_to_execute = qualifying_trades[:target_trades]
        else:
            trades_to_execute = qualifying_trades

        # Execute selected trades
        executed_trades = []
        for trade in trades_to_execute:
            execution = execute_trade(trade, all_pairs, eur_rates, portfolio, max_trade_size_pct, conf_threshold)
            if execution:
                executed_trades.append(execution)

        # Calculate portfolio value after trades
        portfolio_value = calculate_portfolio_value(portfolio, eur_rates)

        print(f"  Portfolio value: €{portfolio_value:.2f}")
        print(f"  Executed trades: {len(executed_trades)}")

        # Load trader config to get generator/estimator IDs for signal display
        trader_config = get_trader(trader_id)
        if trader_config:
            trader_estimator_ids = trader_config.get('estimator_ids', [])
            trader_generator_ids = trader_config.get('generator_ids', [])
            trader_generator_weights = trader_config.get('generator_weights', {})
        else:
            trader_estimator_ids = []
            trader_generator_ids = []
            trader_generator_weights = {}

        # Build result record
        result = {
            'date': date_str,
            'strategy_id': strategy_id,
            'strategy_name': strategy_config.get('type', 'unknown'),
            'strategy_params': f"conf={conf_threshold}_T={target_trades if target_trades else 'all'}_size={max_trade_size_pct}",
            'no_trades_executed': len(executed_trades),
            'current_value': portfolio_value
        }

        # Add portfolio balance columns
        for curr in CURRENCIES:
            result[curr] = portfolio.get(curr, 0.0)

        results.append(result)
        total_trades_executed += len(executed_trades)

    # Save results to CSV
    output_dir = '/workspace/group/fx-portfolio/data/portfolios'
    os.makedirs(output_dir, exist_ok=True)

    csv_file = f'{output_dir}/strategies.csv'

    # Define fieldnames
    fieldnames = ['date', 'strategy_id', 'strategy_name', 'strategy_params', 'no_trades_executed']
    # Add balance columns
    for curr in CURRENCIES:
        fieldnames.append(curr)
    fieldnames.append('current_value')

    # Read existing data and merge
    file_exists = os.path.exists(csv_file)

    if file_exists:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            existing_rows = list(reader)

        # Filter out rows for current date
        other_date_rows = [row for row in existing_rows if row.get('date') != date_str]

        # Write all data
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(other_date_rows)
            writer.writerows(results)
    else:
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    logger.add_count('strategy_combinations', len(strategies))
    logger.add_count('strategies_executed', len(results))
    logger.add_count('total_trades', total_trades_executed)
    logger.add_info('output_csv', csv_file)

    print(f"\n{'='*60}")
    print(f"✓ Completed {len(results)} strategy runs")
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
