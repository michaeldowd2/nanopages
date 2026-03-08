#!/usr/bin/env python3
"""
Validate that all upstream dependencies have data for a given date.
Used by orchestrator to ensure data consistency before running steps.
"""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional

def load_config() -> dict:
    """Load pipeline configuration."""
    config_path = Path(__file__).parent.parent / 'config' / 'pipeline_steps.json'
    with open(config_path) as f:
        return json.load(f)

def get_upstream_dependencies(step_id: str, config: dict) -> List[str]:
    """Get all upstream dependencies (direct + transitive) for a step."""
    visited = set()
    to_visit = [step_id]

    while to_visit:
        current = to_visit.pop(0)
        if current in visited or current not in config['steps']:
            continue
        visited.add(current)

        deps = config['steps'][current].get('depends_on', [])
        to_visit.extend(deps)

    # Remove the step itself from dependencies
    visited.discard(step_id)
    return sorted(visited, key=lambda x: int(x))

def extract_dates_from_filename(filename: str) -> Set[str]:
    """
    Extract dates from filename patterns like:
    - step2_indices.csv (no date = all dates)
    - step3_news_2026-02-25.csv (specific date)
    - fx-rates-2026-02-26.json (specific date)
    """
    # Pattern: YYYY-MM-DD
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    matches = re.findall(date_pattern, filename)
    return set(matches) if matches else set()

def get_available_dates_for_step(step_id: str, config: dict) -> Set[str]:
    """
    Get all dates that a step has data for by checking its export files.
    Returns empty set if step doesn't export data or files don't exist.
    """
    step = config['steps'].get(step_id)
    if not step:
        return set()

    exports = step.get('outputs', {}).get('exports', [])
    if not exports:
        return set()

    all_dates = set()
    exports_dir = Path(__file__).parent.parent / 'data' / 'exports'

    for export_pattern in exports:
        # Get just the filename (strip data/exports/)
        export_file = Path(export_pattern).name

        # Handle wildcards (e.g., step1_exchange_rates_matrix*.json)
        if '*' in export_file:
            pattern = export_file.replace('*', '*')
            matching_files = list(exports_dir.glob(pattern))
        else:
            matching_files = [exports_dir / export_file] if (exports_dir / export_file).exists() else []

        for file_path in matching_files:
            if not file_path.exists():
                continue

            # Check if filename contains date
            dates = extract_dates_from_filename(file_path.name)
            if dates:
                all_dates.update(dates)
            else:
                # File exists but has no date in name - check if it's a CSV with date column
                if file_path.suffix == '.csv':
                    try:
                        with open(file_path) as f:
                            header = f.readline().strip().split(',')
                            if 'date' in [h.lower() for h in header]:
                                # Read all dates from CSV
                                for line in f:
                                    parts = line.strip().split(',')
                                    if len(parts) > 0:
                                        # Find date column
                                        date_idx = [h.lower() for h in header].index('date')
                                        date_val = parts[date_idx] if date_idx < len(parts) else None
                                        if date_val:
                                            # Extract YYYY-MM-DD from date value
                                            date_matches = re.findall(r'\d{4}-\d{2}-\d{2}', date_val)
                                            if date_matches:
                                                all_dates.add(date_matches[0])
                    except Exception:
                        pass

    return all_dates

def find_latest_common_date(step_id: str, config: dict) -> Optional[str]:
    """
    Find the latest date that ALL upstream dependencies have data for.
    Returns None if no common date exists or step has no dependencies.
    """
    deps = get_upstream_dependencies(step_id, config)
    if not deps:
        # No dependencies - return latest date from own exports or None
        own_dates = get_available_dates_for_step(step_id, config)
        return max(own_dates) if own_dates else None

    # Get dates for each dependency
    dep_dates = {}
    for dep_id in deps:
        dates = get_available_dates_for_step(dep_id, config)
        if not dates:
            # Dependency has no dated exports - treat as "available for all dates"
            # This handles steps like exchange rates that don't date their outputs
            continue
        dep_dates[dep_id] = dates

    if not dep_dates:
        # All dependencies have no dated exports - any date is valid
        return None

    # Find intersection of all dates
    common_dates = set.intersection(*dep_dates.values())

    return max(common_dates) if common_dates else None

def validate_date_for_step(step_id: str, target_date: str, config: dict) -> Dict[str, any]:
    """
    Validate that a specific date is available for all upstream dependencies.

    Returns:
        {
            'valid': bool,
            'missing_deps': [{'step_id': str, 'step_name': str, 'available_dates': [str]}],
            'message': str
        }
    """
    deps = get_upstream_dependencies(step_id, config)
    if not deps:
        return {
            'valid': True,
            'missing_deps': [],
            'message': f"Step {step_id} has no dependencies - can run for any date"
        }

    missing_deps = []
    for dep_id in deps:
        dates = get_available_dates_for_step(dep_id, config)
        if not dates:
            # No dated exports - assume available for all dates
            continue

        if target_date not in dates:
            dep_name = config['steps'][dep_id]['name']
            missing_deps.append({
                'step_id': dep_id,
                'step_name': dep_name,
                'available_dates': sorted(dates, reverse=True)[:5]  # Show 5 most recent
            })

    if missing_deps:
        step_name = config['steps'][step_id]['name']
        msg = f"Cannot run Step {step_id} ({step_name}) for {target_date}:\n"
        for dep in missing_deps:
            msg += f"  • Step {dep['step_id']} ({dep['step_name']}) missing data for {target_date}\n"
            if dep['available_dates']:
                msg += f"    Available dates: {', '.join(dep['available_dates'][:3])}"
                if len(dep['available_dates']) > 3:
                    msg += f" (+ {len(dep['available_dates']) - 3} more)"
                msg += "\n"
            else:
                msg += "    No dates available\n"

        return {
            'valid': False,
            'missing_deps': missing_deps,
            'message': msg.strip()
        }

    return {
        'valid': True,
        'missing_deps': [],
        'message': f"Step {step_id} can run for {target_date} - all dependencies satisfied"
    }

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Validate step dependencies for date-specific execution'
    )
    parser.add_argument('step_id', help='Step ID to validate')
    parser.add_argument('--date', help='Specific date to validate (YYYY-MM-DD)')
    parser.add_argument('--find-latest', action='store_true',
                       help='Find latest date available for all dependencies')
    parser.add_argument('--json', action='store_true',
                       help='Output result as JSON')

    args = parser.parse_args()
    config = load_config()

    if args.step_id not in config['steps']:
        print(f"Error: Step {args.step_id} not found in config", file=sys.stderr)
        sys.exit(1)

    step_name = config['steps'][args.step_id]['name']

    if args.find_latest:
        latest = find_latest_common_date(args.step_id, config)
        if args.json:
            print(json.dumps({'latest_date': latest}))
        else:
            if latest:
                print(f"Latest available date for Step {args.step_id} ({step_name}): {latest}")
            else:
                print(f"No common date found for Step {args.step_id} ({step_name}) dependencies")
                deps = get_upstream_dependencies(args.step_id, config)
                if deps:
                    print("Dependency status:")
                    for dep_id in deps:
                        dep_dates = get_available_dates_for_step(dep_id, config)
                        dep_name = config['steps'][dep_id]['name']
                        if dep_dates:
                            print(f"  Step {dep_id} ({dep_name}): {len(dep_dates)} dates, latest = {max(dep_dates)}")
                        else:
                            print(f"  Step {dep_id} ({dep_name}): No dated exports")
        sys.exit(0 if latest else 1)

    elif args.date:
        result = validate_date_for_step(args.step_id, args.date, config)
        if args.json:
            print(json.dumps(result))
        else:
            print(result['message'])
        sys.exit(0 if result['valid'] else 1)

    else:
        # Default: show dependency info
        deps = get_upstream_dependencies(args.step_id, config)
        print(f"Step {args.step_id}: {step_name}")
        print(f"Dependencies: {', '.join(deps) if deps else 'None'}")
        print()

        if deps:
            print("Dependency data availability:")
            for dep_id in deps:
                dep_dates = get_available_dates_for_step(dep_id, config)
                dep_name = config['steps'][dep_id]['name']
                if dep_dates:
                    latest = max(dep_dates)
                    print(f"  Step {dep_id} ({dep_name}): {len(dep_dates)} dates available (latest: {latest})")
                else:
                    print(f"  Step {dep_id} ({dep_name}): No dated exports (available for all dates)")

        latest = find_latest_common_date(args.step_id, config)
        print()
        if latest:
            print(f"✓ Latest common date: {latest}")
        else:
            print("✗ No common date found across dependencies")

if __name__ == '__main__':
    main()
