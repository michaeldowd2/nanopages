#!/usr/bin/env python3
"""
Export Pipeline Logs for Dashboard

Exports all pipeline run logs to JSON format for dashboard consumption.
Creates a summary file listing all available dates and aggregates step statistics.
"""

import json
import os
from pathlib import Path
from datetime import datetime

def export_logs():
    """Export all logs to dashboard-friendly format"""

    log_dir = Path('/workspace/group/fx-portfolio/data/logs')
    output_dir = Path('/workspace/group/fx-portfolio/data/exports')
    output_dir.mkdir(parents=True, exist_ok=True)

    if not log_dir.exists():
        print("⚠️ No logs directory found")
        return

    # Get all log files
    log_files = sorted(log_dir.glob('*.json'), reverse=True)

    if not log_files:
        print("⚠️ No log files found")
        return

    # Create summary of all available dates
    dates_summary = []

    for log_file in log_files:
        date_str = log_file.stem

        with open(log_file, 'r') as f:
            log_data = json.load(f)

        steps = log_data.get('steps', [])

        # Calculate summary statistics
        total_steps = len(steps)
        successful_steps = sum(1 for s in steps if s.get('status') == 'success')
        failed_steps = sum(1 for s in steps if s.get('status') == 'failed')
        total_duration = sum(s.get('duration', 0) or 0 for s in steps)
        total_errors = sum(len(s.get('errors', [])) for s in steps)
        total_warnings = sum(len(s.get('warnings', [])) for s in steps)

        dates_summary.append({
            'date': date_str,
            'total_steps': total_steps,
            'successful_steps': successful_steps,
            'failed_steps': failed_steps,
            'total_duration': round(total_duration, 2),
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'status': 'success' if failed_steps == 0 else 'partial' if successful_steps > 0 else 'failed'
        })

    # Save dates summary
    summary_file = output_dir / 'tracking_dates.json'
    with open(summary_file, 'w') as f:
        json.dump({
            'last_updated': datetime.now().isoformat(),
            'total_runs': len(dates_summary),
            'dates': dates_summary
        }, f, indent=2)

    print(f"✓ Exported dates summary: {summary_file}")
    print(f"  Total runs: {len(dates_summary)}")

    # Copy individual log files to exports for dashboard access
    for log_file in log_files:
        dest_file = output_dir / f'tracking_{log_file.name}'

        with open(log_file, 'r') as f:
            log_data = json.load(f)

        # Enrich with additional formatting for dashboard
        for step in log_data.get('steps', []):
            # Format timestamps for display
            if step.get('start_time'):
                step['start_time_display'] = step['start_time'].replace('T', ' ').split('.')[0]
            if step.get('end_time'):
                step['end_time_display'] = step['end_time'].replace('T', ' ').split('.')[0]

            # Add status icon
            status = step.get('status', 'unknown')
            step['status_icon'] = {
                'success': '✓',
                'failed': '❌',
                'running': '⏳',
                'pending': '⏸'
            }.get(status, '?')

        with open(dest_file, 'w') as f:
            json.dump(log_data, f, indent=2)

    print(f"✓ Exported {len(log_files)} log files to exports/")

    return dates_summary


if __name__ == '__main__':
    print("="*60)
    print("Exporting Pipeline Logs")
    print("="*60)

    summary = export_logs()

    if summary:
        print("\n" + "="*60)
        print("Available Runs:")
        print("="*60)
        for run in summary[:10]:  # Show latest 10
            status_icon = '✓' if run['status'] == 'success' else '⚠️' if run['status'] == 'partial' else '❌'
            print(f"{status_icon} {run['date']}: {run['successful_steps']}/{run['total_steps']} steps, {run['total_duration']}s")
        print("="*60)
