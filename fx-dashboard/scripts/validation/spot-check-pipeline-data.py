#!/usr/bin/env python3
"""
Pipeline Data Spot Check

Validates pipeline data quality after execution.
Detects common issues like stale API data, missing records, anomalies.

Exit codes:
  0 = All checks passed
  1 = Critical failures (stop deployment)
  2 = Warnings only (proceed with caution)
"""

import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import json

# Add utilities to path
sys.path.append('/workspace/group/fx-portfolio/scripts')
from utilities.csv_helper import read_csv
from utilities.config_loader import get_currencies

CURRENCIES = get_currencies()

class SpotChecker:
    def __init__(self, date_str):
        self.date_str = date_str
        self.failures = []
        self.warnings = []
        self.passes = []

    def check_duplicate_exchange_rates(self):
        """Check if today's rates are identical to previous day (stale data)"""
        print("\n[1/4] Checking exchange rates for staleness...")

        try:
            # Load today's rates
            today_rates = read_csv('1', date=self.date_str, validate=False)
            if not today_rates:
                self.failures.append("No exchange rates found for today")
                print("   ✗ FAIL: No rates data found")
                return False

            # Load previous day's rates
            date_obj = datetime.strptime(self.date_str, '%Y-%m-%d')
            prev_date = date_obj - timedelta(days=1)
            prev_date_str = prev_date.strftime('%Y-%m-%d')

            try:
                prev_rates = read_csv('1', date=prev_date_str, validate=False)
            except Exception:
                self.warnings.append(f"Could not load previous day rates ({prev_date_str})")
                print(f"   ⚠️  WARN: No previous day data to compare")
                return True

            # Build rate lookup for comparison
            today_lookup = {(r['base_currency'], r['quote_currency']): float(r['rate'])
                          for r in today_rates}
            prev_lookup = {(r['base_currency'], r['quote_currency']): float(r['rate'])
                         for r in prev_rates}

            # Compare rates
            identical_count = 0
            total_pairs = 0
            sample_identical = []

            for pair, rate in today_lookup.items():
                if pair in prev_lookup:
                    total_pairs += 1
                    if abs(rate - prev_lookup[pair]) < 0.0001:  # Essentially identical
                        identical_count += 1
                        if len(sample_identical) < 5:
                            sample_identical.append((pair, rate))

            if total_pairs == 0:
                self.warnings.append("No overlapping pairs to compare")
                print("   ⚠️  WARN: Cannot compare (different pairs)")
                return True

            identical_pct = (identical_count / total_pairs) * 100

            # Critical: All rates identical
            if identical_pct >= 99:
                msg = f"All rates unchanged ({identical_pct:.1f}%) - likely stale API data"
                self.failures.append(msg)
                print(f"   ✗ FAIL: {msg}")
                print(f"      Sample identical pairs:")
                for pair, rate in sample_identical[:3]:
                    print(f"      {pair[0]}/{pair[1]}: {rate} (same as {prev_date_str})")
                return False

            # Warning: Most rates identical
            elif identical_pct >= 90:
                msg = f"{identical_pct:.1f}% rates unchanged - suspicious"
                self.warnings.append(msg)
                print(f"   ⚠️  WARN: {msg}")
                return True

            # Pass: Rates have changed
            else:
                msg = f"Rates changed: {100-identical_pct:.1f}% different from previous day"
                self.passes.append(msg)
                print(f"   ✓ PASS: {msg}")
                return True

        except Exception as e:
            self.failures.append(f"Exchange rate check failed: {e}")
            print(f"   ✗ FAIL: Error - {e}")
            return False

    def check_data_completeness(self):
        """Verify expected data volumes"""
        print("\n[2/4] Checking data completeness...")

        checks = [
            ('1', 'exchange rates', 121, 121),  # min, max
            ('3', 'news articles', 10, 150),
            ('5', 'signals', 20, 500),
            ('9', 'portfolios', 9, 9),
        ]

        all_passed = True

        for step_id, name, min_expected, max_expected in checks:
            try:
                rows = read_csv(step_id, date=self.date_str, validate=False)
                count = len(rows)

                if count < min_expected:
                    msg = f"{name}: {count} rows (expected {min_expected}+)"
                    self.failures.append(msg)
                    print(f"   ✗ FAIL: {msg}")
                    all_passed = False
                elif count > max_expected:
                    msg = f"{name}: {count} rows (expected <{max_expected})"
                    self.warnings.append(msg)
                    print(f"   ⚠️  WARN: {msg}")
                else:
                    msg = f"{name}: {count} rows ✓"
                    self.passes.append(msg)
                    print(f"   ✓ PASS: {msg}")

            except Exception as e:
                msg = f"{name}: File not found or read error"
                self.failures.append(msg)
                print(f"   ✗ FAIL: {msg}")
                all_passed = False

        return all_passed

    def check_value_ranges(self):
        """Check for anomalous values"""
        print("\n[3/4] Checking value ranges...")

        try:
            # Check exchange rates are reasonable
            rates = read_csv('1', date=self.date_str, validate=False)
            extreme_rates = []

            for row in rates:
                rate = float(row['rate'])
                if rate < 0.001 or rate > 10000:
                    extreme_rates.append(f"{row['base_currency']}/{row['quote_currency']}: {rate}")

            if extreme_rates:
                msg = f"Extreme rates found: {len(extreme_rates)}"
                self.warnings.append(msg)
                print(f"   ⚠️  WARN: {msg}")
                for extreme in extreme_rates[:3]:
                    print(f"      {extreme}")
            else:
                print("   ✓ PASS: All rates within normal range")
                self.passes.append("Exchange rates within normal range")

            # Check portfolio values are reasonable
            portfolios = read_csv('9', date=self.date_str, validate=False)
            extreme_portfolios = []

            for row in portfolios:
                value = float(row['portfolio_value'])
                if value < 500 or value > 2000:  # Started at ~€1000
                    extreme_portfolios.append(f"{row['strategy_id']}: €{value:.2f}")

            if extreme_portfolios:
                msg = f"Extreme portfolio values: {len(extreme_portfolios)}"
                self.warnings.append(msg)
                print(f"   ⚠️  WARN: {msg}")
                for extreme in extreme_portfolios[:3]:
                    print(f"      {extreme}")
            else:
                print("   ✓ PASS: Portfolio values within normal range")
                self.passes.append("Portfolio values reasonable")

            return True

        except Exception as e:
            self.warnings.append(f"Value range check error: {e}")
            print(f"   ⚠️  WARN: Could not complete check - {e}")
            return True

    def check_temporal_consistency(self):
        """Verify dates are consistent"""
        print("\n[4/4] Checking temporal consistency...")

        try:
            # Check that all files have correct date
            date_obj = datetime.strptime(self.date_str, '%Y-%m-%d')
            today = datetime.now().date()

            if date_obj.date() > today:
                msg = f"Future date detected: {self.date_str}"
                self.failures.append(msg)
                print(f"   ✗ FAIL: {msg}")
                return False

            print(f"   ✓ PASS: Date {self.date_str} is valid")
            self.passes.append("Temporal consistency OK")
            return True

        except Exception as e:
            self.failures.append(f"Temporal check failed: {e}")
            print(f"   ✗ FAIL: {e}")
            return False

    def run_all_checks(self):
        """Run all spot checks"""
        print("=" * 60)
        print(f"Pipeline Data Spot Check - {self.date_str}")
        print("=" * 60)

        # Run checks
        self.check_duplicate_exchange_rates()
        self.check_data_completeness()
        self.check_value_ranges()
        self.check_temporal_consistency()

        # Summarize
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        print(f"✓ Passed: {len(self.passes)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"✗ Failures: {len(self.failures)}")

        if self.failures:
            print("\n❌ CRITICAL FAILURES DETECTED")
            for failure in self.failures:
                print(f"  • {failure}")
            return 1
        elif self.warnings:
            print("\n⚠️  WARNINGS DETECTED (proceed with caution)")
            for warning in self.warnings:
                print(f"  • {warning}")
            return 2
        else:
            print("\n✅ ALL CHECKS PASSED")
            return 0

    def save_log(self, exit_code):
        """Save check results to log file"""
        log_dir = Path('/workspace/group/fx-portfolio/data/validation')
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"spot-check-{self.date_str}.json"

        log_data = {
            'date': self.date_str,
            'timestamp': datetime.now().isoformat(),
            'exit_code': exit_code,
            'passes': self.passes,
            'warnings': self.warnings,
            'failures': self.failures
        }

        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)

        print(f"\n📝 Log saved: {log_file}")


def main():
    parser = argparse.ArgumentParser(description='Spot check pipeline data quality')
    parser.add_argument('--date', type=str, required=True, help='Date to check (YYYY-MM-DD)')
    parser.add_argument('--check', type=str, choices=['rates', 'completeness', 'ranges', 'temporal', 'all'],
                       default='all', help='Specific check to run')
    args = parser.parse_args()

    checker = SpotChecker(args.date)

    if args.check == 'rates':
        result = checker.check_duplicate_exchange_rates()
        exit_code = 0 if result else 1
    elif args.check == 'completeness':
        result = checker.check_data_completeness()
        exit_code = 0 if result else 1
    elif args.check == 'ranges':
        result = checker.check_value_ranges()
        exit_code = 0 if result else 1
    elif args.check == 'temporal':
        result = checker.check_temporal_consistency()
        exit_code = 0 if result else 1
    else:
        exit_code = checker.run_all_checks()

    checker.save_log(exit_code)
    print("=" * 60)

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
