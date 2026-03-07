#!/usr/bin/env python3
"""
Pipeline Logging Infrastructure

Provides unified logging for all pipeline steps with structured JSON output.
Each step logs: start_time, end_time, duration, status, counts, errors.

Usage:
    from pipeline_logger import PipelineLogger

    logger = PipelineLogger('step1', 'Fetch Exchange Rates')
    logger.start()

    try:
        # ... your code ...
        logger.add_count('pairs_fetched', 121)
        logger.success()
    except Exception as e:
        logger.error(str(e))
        raise
    finally:
        logger.finish()
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

class PipelineLogger:
    """Logger for pipeline steps with structured JSON output"""

    def __init__(self, step_id, step_name, date_str=None):
        """
        Initialize logger for a pipeline step

        Args:
            step_id: Step identifier (e.g., 'step1', 'step2', ...)
            step_name: Human-readable step name (e.g., 'Fetch Exchange Rates')
            date_str: Date string (YYYY-MM-DD), defaults to today
        """
        self.step_id = step_id
        self.step_name = step_name
        self.date_str = date_str or datetime.now().strftime('%Y-%m-%d')

        self.log_entry = {
            'step_id': step_id,
            'step_name': step_name,
            'date': self.date_str,
            'start_time': None,
            'end_time': None,
            'duration': None,
            'status': 'pending',
            'counts': {},
            'errors': [],
            'warnings': [],
            'info': {}
        }

        self.start_timestamp = None

    def start(self):
        """Mark step as started"""
        self.start_timestamp = time.time()
        self.log_entry['start_time'] = datetime.now().isoformat()
        self.log_entry['status'] = 'running'
        print(f"\n{'='*60}")
        print(f"{self.step_name}")
        print(f"{'='*60}")

    def add_count(self, key, value):
        """Add a count metric (e.g., 'pairs_fetched': 121)"""
        self.log_entry['counts'][key] = value

    def add_info(self, key, value):
        """Add informational metadata (e.g., 'api_used': 'fixer.io')"""
        self.log_entry['info'][key] = value

    def warning(self, message):
        """Add a warning (non-fatal)"""
        self.log_entry['warnings'].append({
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        print(f"⚠️ Warning: {message}")

    def error(self, message):
        """Add an error (may or may not be fatal)"""
        self.log_entry['errors'].append({
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        print(f"❌ Error: {message}")

    def success(self):
        """Mark step as successful"""
        self.log_entry['status'] = 'success'

    def fail(self):
        """Mark step as failed"""
        self.log_entry['status'] = 'failed'

    def finish(self):
        """Complete logging and save to file"""
        if self.start_timestamp:
            end_timestamp = time.time()
            self.log_entry['end_time'] = datetime.now().isoformat()
            self.log_entry['duration'] = round(end_timestamp - self.start_timestamp, 2)

        # Auto-set status based on errors if not explicitly set
        if self.log_entry['status'] == 'running':
            if self.log_entry['errors']:
                self.log_entry['status'] = 'failed'
            else:
                self.log_entry['status'] = 'success'

        # Save to file
        self._save_log()

        # Print summary
        print(f"\n{'='*60}")
        status_symbol = '✓' if self.log_entry['status'] == 'success' else '❌'
        print(f"{status_symbol} {self.step_name}: {self.log_entry['status'].upper()}")
        if self.log_entry['duration']:
            print(f"Duration: {self.log_entry['duration']}s")
        if self.log_entry['counts']:
            for key, value in self.log_entry['counts'].items():
                print(f"  • {key}: {value}")
        if self.log_entry['errors']:
            print(f"  • Errors: {len(self.log_entry['errors'])}")
        print(f"{'='*60}\n")

    def _save_log(self):
        """Save log entry to JSON file"""
        # Create logs directory
        log_dir = Path('/workspace/group/fx-portfolio/data/logs')
        log_dir.mkdir(parents=True, exist_ok=True)

        # Load or create daily log file
        log_file = log_dir / f'{self.date_str}.json'

        if log_file.exists():
            with open(log_file, 'r') as f:
                daily_logs = json.load(f)
        else:
            daily_logs = {
                'date': self.date_str,
                'steps': []
            }

        # Update or append this step's log
        # Find existing entry for this step (if re-run)
        existing_idx = None
        for idx, step in enumerate(daily_logs['steps']):
            if step['step_id'] == self.step_id:
                existing_idx = idx
                break

        if existing_idx is not None:
            # Update existing entry
            daily_logs['steps'][existing_idx] = self.log_entry
        else:
            # Append new entry
            daily_logs['steps'].append(self.log_entry)

        # Save updated log
        with open(log_file, 'w') as f:
            json.dump(daily_logs, f, indent=2)

        print(f"📝 Log saved: {log_file}")


def get_available_log_dates():
    """Get list of dates with available logs"""
    log_dir = Path('/workspace/group/fx-portfolio/data/logs')
    if not log_dir.exists():
        return []

    log_files = sorted(log_dir.glob('*.json'), reverse=True)
    return [f.stem for f in log_files]


def get_log_for_date(date_str):
    """Get log data for a specific date"""
    log_file = Path(f'/workspace/group/fx-portfolio/data/logs/{date_str}.json')

    if not log_file.exists():
        return None

    with open(log_file, 'r') as f:
        return json.load(f)


def get_latest_log():
    """Get most recent log"""
    dates = get_available_log_dates()
    if not dates:
        return None
    return get_log_for_date(dates[0])


if __name__ == '__main__':
    # Test the logger
    print("Testing PipelineLogger...\n")

    logger = PipelineLogger('test', 'Test Step')
    logger.start()

    time.sleep(0.5)

    logger.add_count('items_processed', 42)
    logger.add_count('items_skipped', 3)
    logger.add_info('version', '1.0.0')
    logger.warning('This is a test warning')
    logger.success()

    logger.finish()

    print("\nTest complete. Check /workspace/group/fx-portfolio/data/logs/")
