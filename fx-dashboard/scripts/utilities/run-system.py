#!/usr/bin/env python3
"""
Run System - Procedural Pipeline Execution

Execute pipeline processes in dependency order based on configuration.
Supports selective reruns by date and/or process IDs.

Usage:
    # Run all processes for today
    python run-system.py

    # Run all processes for specific date
    python run-system.py --date 2024-01-15

    # Run specific processes for today
    python run-system.py --process-ids 1 2 3

    # Run specific processes for specific date
    python run-system.py --date 2024-01-15 --process-ids 5 6 7
"""

import os
import sys
import json
import argparse
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Base directory (fx-portfolio/)
BASE_DIR = Path(__file__).parent.parent.parent


def load_pipeline_config():
    """Load pipeline_steps.json configuration."""
    config_path = BASE_DIR / "config" / "pipeline_steps.json"

    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded pipeline configuration: {config.get('version', 'unknown')}")
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse configuration: {e}")
        sys.exit(1)


def resolve_dependencies(config, process_ids=None):
    """
    Resolve process dependencies and return execution order.

    For specified processes, includes the processes themselves plus any
    downstream processes that depend on them (not upstream dependencies).

    Args:
        config: Pipeline configuration dictionary
        process_ids: Optional list of process IDs to run. If None, runs all.

    Returns:
        List of process IDs in execution order
    """
    steps = config.get('steps', {})

    # If no process_ids specified, run all (except deployment)
    if process_ids is None:
        # Run all steps except step 10 (deployment) by default
        process_ids = [step_id for step_id in steps.keys()
                      if step_id != '10' and steps[step_id].get('script')]
    else:
        # Convert to strings for consistency
        process_ids = [str(pid) for pid in process_ids]

    # Validate all requested process IDs exist
    for pid in list(process_ids):  # Use list() to avoid modifying during iteration
        if pid not in steps:
            logger.error(f"Invalid process ID: {pid}")
            sys.exit(1)
        if not steps[pid].get('script'):
            logger.warning(f"Process {pid} ({steps[pid]['name']}) has no script - skipping")
            process_ids.remove(pid)

    # Build reverse dependency graph (which processes depend on each process)
    downstream_deps = {step_id: [] for step_id in steps.keys()}
    for step_id, step in steps.items():
        for dep_id in step.get('depends_on', []):
            if dep_id in downstream_deps:
                downstream_deps[dep_id].append(step_id)

    # Find all processes to run (requested + downstream, excluding deployment)
    processes_to_run = set(process_ids)

    def add_downstream(step_id):
        """Recursively add all downstream dependencies (excluding deployment)."""
        for downstream_id in downstream_deps.get(step_id, []):
            # Skip deployment (10) unless explicitly requested
            if downstream_id == '10' and '10' not in process_ids:
                continue
            if downstream_id not in processes_to_run and steps[downstream_id].get('script'):
                processes_to_run.add(downstream_id)
                add_downstream(downstream_id)

    # Add all downstream processes
    for pid in process_ids:
        add_downstream(pid)

    # Now determine execution order using topological sort
    visited = set()
    execution_order = []

    def visit(step_id):
        """DFS to determine execution order."""
        if step_id in visited:
            return
        if step_id not in processes_to_run:
            return
        if not steps[step_id].get('script'):
            return

        visited.add(step_id)

        step = steps[step_id]

        # Visit all dependencies first (but only if they're in our run set)
        for dep_id in step.get('depends_on', []):
            if dep_id in processes_to_run:
                visit(dep_id)

        execution_order.append(step_id)

    # Visit all processes in the run set
    for pid in sorted(processes_to_run):
        visit(pid)

    return execution_order


def execute_process(config, process_id, date=None):
    """
    Execute a single pipeline process.

    Args:
        config: Pipeline configuration dictionary
        process_id: Process ID to execute
        date: Optional date string (YYYY-MM-DD format)

    Returns:
        True if successful, False otherwise
    """
    steps = config.get('steps', {})
    step = steps[process_id]

    script_path = step['script']
    step_name = step['name']
    supports_date = step.get('supports_date_filter', False)

    # Update legacy script paths to new folder structure
    script_path = script_path.replace('scripts/', 'scripts/pipeline/')
    if 'calculate-trades-step8.py' in script_path:
        script_path = script_path.replace('calculate-trades-step8.py', 'calculate-trades.py')
    if 'execute-strategies-step9.py' in script_path:
        script_path = script_path.replace('execute-strategies-step9.py', 'execute-strategies.py')
    if 'analyze-time-horizons-llm.py' in script_path:
        script_path = script_path.replace('analyze-time-horizons-llm.py', 'analyze-time-horizons.py')
    if 'generate-sentiment-signals-v2.py' in script_path:
        script_path = script_path.replace('generate-sentiment-signals-v2.py', 'generate-sentiment-signals.py')

    # Build command
    script_full_path = BASE_DIR / script_path

    if not script_full_path.exists():
        logger.error(f"Script not found: {script_full_path}")
        return False

    cmd = ['python3', str(script_full_path)]

    # Add date parameter if supported and provided
    if supports_date and date:
        cmd.extend(['--date', date])

    # Log execution
    date_str = f" for date {date}" if date else ""
    logger.info(f"Executing: Process {process_id} - {step_name}{date_str}")
    logger.info(f"Command: {' '.join(cmd)}")

    # Execute process
    try:
        result = subprocess.run(
            cmd,
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            logger.info(f"✓ Process {process_id} ({step_name}) completed successfully")
            if result.stdout:
                logger.debug(f"Output: {result.stdout[:500]}")  # Log first 500 chars
            return True
        else:
            logger.error(f"✗ Process {process_id} ({step_name}) failed with code {result.returncode}")
            if result.stderr:
                logger.error(f"Error: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"✗ Process {process_id} ({step_name}) failed with exception: {e}")
        return False


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Run FX Portfolio Pipeline processes in dependency order',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all processes for today
  %(prog)s

  # Run all processes for specific date
  %(prog)s --date 2024-01-15

  # Run specific processes for today
  %(prog)s --process-ids 1 2 3

  # Run specific processes for specific date
  %(prog)s --date 2024-01-15 --process-ids 5 6 7

  # Include deployment step
  %(prog)s --process-ids 1 2 3 10
        """
    )

    parser.add_argument(
        '--date',
        type=str,
        default=None,
        help='Date to process (YYYY-MM-DD format). Default: today'
    )

    parser.add_argument(
        '--process-ids',
        type=str,
        nargs='+',
        default=None,
        help='Process IDs to run (space-separated). Default: all processes except deployment'
    )

    parser.add_argument(
        '--include-deployment',
        action='store_true',
        help='Include deployment step (process 10) in execution'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show execution plan without running processes'
    )

    args = parser.parse_args()

    # Determine date
    date = args.date
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"Using current date: {date}")
    else:
        logger.info(f"Using specified date: {date}")

    # Load configuration
    config = load_pipeline_config()

    # Add deployment to process_ids if requested
    process_ids = args.process_ids
    if args.include_deployment:
        if process_ids is None:
            process_ids = []
        process_ids.append('10')

    # Resolve execution order
    execution_order = resolve_dependencies(config, process_ids)

    if not execution_order:
        logger.warning("No processes to execute")
        return

    # Log execution plan
    logger.info("=" * 60)
    logger.info("EXECUTION PLAN")
    logger.info("=" * 60)
    logger.info(f"Date: {date}")
    logger.info(f"Processes to execute: {len(execution_order)}")
    logger.info("")

    steps = config.get('steps', {})
    for i, process_id in enumerate(execution_order, 1):
        step = steps[process_id]
        date_support = "✓" if step.get('supports_date_filter') else "✗"
        logger.info(f"  {i}. Process {process_id}: {step['name']} [date filter: {date_support}]")
        if step.get('depends_on'):
            logger.info(f"     Dependencies: {', '.join(step['depends_on'])}")

    logger.info("=" * 60)

    # Dry run - just show plan
    if args.dry_run:
        logger.info("DRY RUN - No processes executed")
        return

    # Execute processes in order
    logger.info("Starting execution...")
    logger.info("")

    success_count = 0
    failure_count = 0

    for process_id in execution_order:
        success = execute_process(config, process_id, date)
        if success:
            success_count += 1
        else:
            failure_count += 1
            logger.error(f"Process {process_id} failed - stopping execution")
            break

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("EXECUTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {failure_count}")
    logger.info(f"Total: {len(execution_order)}")

    if failure_count == 0:
        logger.info("✓ All processes completed successfully")
        sys.exit(0)
    else:
        logger.error("✗ Pipeline execution failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
