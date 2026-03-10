#!/usr/bin/env python3
"""
CSV Helper - Read/write CSV files with schema validation.

Provides utilities for reading and writing CSV files according to the
schemas defined in config/pipeline_steps.json.

Uses standard library csv module (no pandas dependency).
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = BASE_DIR / "config" / "pipeline_steps.json"


def load_schema(process_name: str) -> Dict:
    """
    Load CSV schema for a process from config.

    Args:
        process_name: Schema name (e.g., 'process_1_exchange_rates')

    Returns:
        Dict with 'columns' and 'output_path'
    """
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

    schemas = config.get('csv_schemas', {})
    if process_name not in schemas:
        raise ValueError(f"Schema not found: {process_name}")

    return schemas[process_name]


def get_column_names(process_name: str) -> List[str]:
    """Get list of column names for a process."""
    schema = load_schema(process_name)
    return [col['name'] for col in schema['columns']]


def get_output_path(process_name: str, **kwargs) -> Path:
    """
    Get output path for a process with template substitution.

    Args:
        process_name: Schema name
        **kwargs: Template variables (date, currency, etc.)

    Returns:
        Absolute Path object
    """
    schema = load_schema(process_name)
    path_template = schema['output_path']

    # Substitute template variables
    path_str = path_template.format(**kwargs)

    return BASE_DIR / path_str


def read_csv(process_name: str, validate: bool = True, **kwargs) -> List[Dict]:
    """
    Read CSV file for a process.

    Args:
        process_name: Schema name
        validate: Whether to validate columns match schema
        **kwargs: Template variables for path (date, currency, etc.)

    Returns:
        List of dicts (rows)
    """
    csv_path = get_output_path(process_name, **kwargs)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Read CSV
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Validate columns if requested
    if validate and rows:
        expected_cols = get_column_names(process_name)
        actual_cols = list(rows[0].keys())

        if actual_cols != expected_cols:
            raise ValueError(
                f"Column mismatch for {process_name}:\n"
                f"Expected: {expected_cols}\n"
                f"Actual: {actual_cols}"
            )

    return rows


def read_csv_multi_dates(
    process_name: str,
    dates: List[str],
    validate: bool = True
) -> List[Dict]:
    """
    Read and concatenate CSV files for multiple dates.

    Args:
        process_name: Schema name
        dates: List of dates in YYYY-MM-DD format
        validate: Whether to validate columns

    Returns:
        List of dicts with concatenated data from all dates
    """
    all_rows = []

    for date in dates:
        csv_path = get_output_path(process_name, date=date)
        if csv_path.exists():
            with open(csv_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                all_rows.extend(list(reader))

    if not all_rows:
        raise FileNotFoundError(f"No CSV files found for dates: {dates}")

    # Validate columns if requested
    if validate and all_rows:
        expected_cols = get_column_names(process_name)
        actual_cols = list(all_rows[0].keys())

        if actual_cols != expected_cols:
            raise ValueError(
                f"Column mismatch for {process_name}:\n"
                f"Expected: {expected_cols}\n"
                f"Actual: {actual_cols}"
            )

    return all_rows


def write_csv(
    rows: List[Dict],
    process_name: str,
    validate: bool = True,
    **kwargs
) -> Path:
    """
    Write list of dicts to CSV file for a process.

    Args:
        rows: List of dicts to write
        process_name: Schema name
        validate: Whether to validate columns match schema
        **kwargs: Template variables for path (date, currency, etc.)

    Returns:
        Path where CSV was written
    """
    # Get column names
    expected_cols = get_column_names(process_name)

    # Handle empty rows - write header-only CSV
    if not rows:
        output_path = get_output_path(process_name, **kwargs)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=expected_cols)
            writer.writeheader()

        return output_path

    # Validate columns if requested
    if validate:
        actual_cols = list(rows[0].keys())

        if actual_cols != expected_cols:
            raise ValueError(
                f"Column mismatch for {process_name}:\n"
                f"Expected: {expected_cols}\n"
                f"Actual: {actual_cols}"
            )

    # Get output path
    csv_path = get_output_path(process_name, **kwargs)

    # Create parent directory if needed
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    # Write CSV
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=expected_cols)
        writer.writeheader()
        writer.writerows(rows)

    return csv_path


def get_date_range(start_date: str, end_date: str) -> List[str]:
    """
    Get list of dates between start and end (inclusive).

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        List of date strings in YYYY-MM-DD format
    """
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')

    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)

    return dates


def get_previous_date(date: str) -> str:
    """
    Get previous date.

    Args:
        date: Date in YYYY-MM-DD format

    Returns:
        Previous date in YYYY-MM-DD format
    """
    dt = datetime.strptime(date, '%Y-%m-%d')
    prev_dt = dt - timedelta(days=1)
    return prev_dt.strftime('%Y-%m-%d')


def csv_exists(process_name: str, **kwargs) -> bool:
    """
    Check if CSV file exists for a process.

    Args:
        process_name: Schema name
        **kwargs: Template variables for path

    Returns:
        True if file exists, False otherwise
    """
    csv_path = get_output_path(process_name, **kwargs)
    return csv_path.exists()


if __name__ == '__main__':
    # Test the helper functions
    print("Testing CSV Helper...")

    # Test schema loading
    schema = load_schema('process_1_exchange_rates')
    print(f"\nProcess 1 schema: {schema['description']}")
    print(f"Columns: {get_column_names('process_1_exchange_rates')}")

    # Test path generation
    path = get_output_path('process_1_exchange_rates', date='2026-02-24')
    print(f"\nOutput path: {path}")
    print(f"Exists: {csv_exists('process_1_exchange_rates', date='2026-02-24')}")

    # Test reading
    try:
        rows = read_csv('process_1_exchange_rates', date='2026-02-24')
        print(f"\nRead {len(rows)} rows from Process 1")
        if rows:
            print(f"Columns: {list(rows[0].keys())}")
    except Exception as e:
        print(f"\nError reading: {e}")
