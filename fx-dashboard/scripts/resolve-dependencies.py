#!/usr/bin/env python3
"""
Pipeline Dependency Resolver

This script provides dependency resolution for the FX pipeline orchestration system.
It reads the pipeline_steps.json configuration and provides utilities to:
- Find all dependencies (upstream) for a given step
- Find all dependents (downstream) for a given step
- Get execution order for a set of steps
- Validate dependency graph for cycles

Usage:
    # Get all upstream dependencies for a step (in execution order)
    ./scripts/resolve-dependencies.py --upstream 6

    # Get all downstream dependents for a step (in execution order)
    ./scripts/resolve-dependencies.py --downstream 3

    # Get execution order for multiple steps
    ./scripts/resolve-dependencies.py --order 3 5 7a

    # Validate dependency graph
    ./scripts/resolve-dependencies.py --validate

    # Export as bash arrays (for use in shell scripts)
    ./scripts/resolve-dependencies.py --downstream 3 --bash
"""

import json
import sys
from pathlib import Path
from typing import Set, List, Dict


def load_config() -> Dict:
    """Load pipeline configuration"""
    config_file = Path(__file__).parent.parent / "config" / "pipeline_steps.json"
    with open(config_file) as f:
        return json.load(f)


def get_all_upstream(step_id: str, config: Dict, visited: Set[str] = None) -> Set[str]:
    """
    Get all upstream dependencies for a step (what this step needs to run).
    Returns set of step IDs that must be executed before this step.
    """
    if visited is None:
        visited = set()

    if step_id in visited:
        return visited

    visited.add(step_id)

    step = config["steps"].get(step_id)
    if not step:
        return visited

    for dep in step.get("depends_on", []):
        get_all_upstream(dep, config, visited)

    return visited


def get_all_downstream(step_id: str, config: Dict, visited: Set[str] = None) -> Set[str]:
    """
    Get all downstream dependents for a step (what depends on this step).
    Returns set of step IDs that must be re-run if this step changes.
    """
    if visited is None:
        visited = set()

    if step_id in visited:
        return visited

    visited.add(step_id)

    # Find all steps that depend on step_id
    for sid, step in config["steps"].items():
        if step_id in step.get("depends_on", []):
            get_all_downstream(sid, config, visited)

    return visited


def topological_sort(step_ids: Set[str], config: Dict) -> List[str]:
    """
    Sort steps in execution order using topological sort.
    Steps with no dependencies come first, then steps that depend on them, etc.
    """
    # Build dependency graph
    graph = {}
    in_degree = {}

    for sid in step_ids:
        step = config["steps"][sid]
        deps = [d for d in step.get("depends_on", []) if d in step_ids]
        graph[sid] = deps
        in_degree[sid] = len(deps)

    # Kahn's algorithm for topological sort
    queue = [sid for sid in step_ids if in_degree[sid] == 0]
    result = []

    while queue:
        # Sort queue by step ID to ensure consistent ordering when dependencies are equal
        queue.sort(key=lambda x: (x.replace('a', '.1').replace('b', '.2')))

        current = queue.pop(0)
        result.append(current)

        # Reduce in-degree for all dependents
        for sid in step_ids:
            if current in graph.get(sid, []):
                in_degree[sid] -= 1
                if in_degree[sid] == 0:
                    queue.append(sid)

    if len(result) != len(step_ids):
        raise ValueError("Cycle detected in dependency graph!")

    return result


def validate_graph(config: Dict) -> bool:
    """
    Validate that the dependency graph has no cycles.
    Returns True if valid, raises ValueError if cycle detected.
    """
    all_steps = set(config["steps"].keys())
    try:
        topological_sort(all_steps, config)
        return True
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return False


def get_step_info(step_id: str, config: Dict) -> Dict:
    """Get step information"""
    return config["steps"].get(step_id, {})


def format_bash_array(items: List[str], var_name: str = "STEPS") -> str:
    """Format list as bash array declaration"""
    return f'{var_name}=({" ".join(items)})'


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Resolve pipeline dependencies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get all dependencies for step 6 (in execution order)
  %(prog)s --upstream 6

  # Get what depends on step 3 (what needs to rerun if 3 changes)
  %(prog)s --downstream 3

  # Get execution order for multiple steps
  %(prog)s --order 3 5 7a 8

  # Validate dependency graph
  %(prog)s --validate

  # Export as bash array for scripting
  %(prog)s --downstream 3 --bash
        """
    )

    parser.add_argument("--upstream", metavar="STEP",
                       help="Get all upstream dependencies for STEP")
    parser.add_argument("--downstream", metavar="STEP",
                       help="Get all downstream dependents for STEP")
    parser.add_argument("--order", nargs="+", metavar="STEP",
                       help="Get execution order for STEP(s)")
    parser.add_argument("--validate", action="store_true",
                       help="Validate dependency graph for cycles")
    parser.add_argument("--bash", action="store_true",
                       help="Output as bash array")
    parser.add_argument("--var-name", default="STEPS",
                       help="Variable name for bash array (default: STEPS)")
    parser.add_argument("--info", metavar="STEP",
                       help="Show detailed information for STEP")

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config()
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}", file=sys.stderr)
        sys.exit(1)

    # Handle commands
    if args.validate:
        if validate_graph(config):
            print("✓ Dependency graph is valid (no cycles detected)")
            sys.exit(0)
        else:
            sys.exit(1)

    elif args.upstream:
        deps = get_all_upstream(args.upstream, config)
        ordered = topological_sort(deps, config)

        if args.bash:
            print(format_bash_array(ordered, args.var_name))
        else:
            print(f"Upstream dependencies for step {args.upstream} (in execution order):")
            for step_id in ordered:
                step = get_step_info(step_id, config)
                print(f"  {step_id}: {step.get('name', 'Unknown')}")

    elif args.downstream:
        deps = get_all_downstream(args.downstream, config)
        ordered = topological_sort(deps, config)

        if args.bash:
            print(format_bash_array(ordered, args.var_name))
        else:
            print(f"Downstream dependents for step {args.downstream} (in execution order):")
            for step_id in ordered:
                step = get_step_info(step_id, config)
                marker = "→" if step_id != args.downstream else "●"
                print(f"  {marker} {step_id}: {step.get('name', 'Unknown')}")

    elif args.order:
        try:
            ordered = topological_sort(set(args.order), config)

            if args.bash:
                print(format_bash_array(ordered, args.var_name))
            else:
                print(f"Execution order for steps {', '.join(args.order)}:")
                for i, step_id in enumerate(ordered, 1):
                    step = get_step_info(step_id, config)
                    print(f"  {i}. {step_id}: {step.get('name', 'Unknown')}")
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.info:
        step = get_step_info(args.info, config)
        if not step:
            print(f"ERROR: Step {args.info} not found", file=sys.stderr)
            sys.exit(1)

        print(f"Step {args.info}: {step.get('name', 'Unknown')}")
        print(f"  Script: {step.get('script', 'N/A')}")
        print(f"  Description: {step.get('description', 'N/A')}")
        print(f"  Dependencies: {', '.join(step.get('depends_on', [])) or 'None'}")
        print(f"  Date filter: {'Yes' if step.get('supports_date_filter') else 'No'}")
        print(f"  Safe to clear: {'Yes' if step.get('is_safe_to_clear') else 'No'}")
        if step.get('warning'):
            print(f"  ⚠️  {step['warning']}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
