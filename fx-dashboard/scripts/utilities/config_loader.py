#!/usr/bin/env python3
"""
Configuration Loader for FX Portfolio System

Loads and manages system configuration from system_config.json.

New Design Principles:
- Each module+parameter combo has a unique ID
- All items in config are implicitly active (no "active" flag)
- Strategies reference estimator/generator IDs
- Simple, flat structure
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any

# Base directory for the project
BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = BASE_DIR / 'config' / 'system_config.json'

def get_base_dir() -> Path:
    """Get the base directory for the project"""
    return BASE_DIR

def load_config() -> Dict[str, Any]:
    """Load system configuration from JSON file"""
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(config: Dict[str, Any]):
    """Save system configuration to JSON file"""
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)

# ============================================================================
# Currencies
# ============================================================================

def get_currencies() -> List[str]:
    """Get list of active currencies"""
    config = load_config()
    return config.get('currencies', [])

# ============================================================================
# Horizon Estimators
# ============================================================================

def get_estimators() -> Dict[str, Dict]:
    """Get all estimator configurations (all are active)"""
    config = load_config()
    return config.get('horizon_estimators', {})

def get_estimator(estimator_id: str) -> Dict:
    """Get specific estimator configuration"""
    estimators = get_estimators()
    return estimators.get(estimator_id)

# ============================================================================
# Signal Generators
# ============================================================================

def get_generators() -> Dict[str, Dict]:
    """Get all generator configurations (all are active)"""
    config = load_config()
    return config.get('signal_generators', {})

def get_generator(generator_id: str) -> Dict:
    """Get specific generator configuration"""
    generators = get_generators()
    return generators.get(generator_id)

# ============================================================================
# Traders
# ============================================================================

def get_traders() -> Dict[str, Dict]:
    """Get all trader configurations (all are active)"""
    config = load_config()
    return config.get('traders', {})

def get_trader(trader_id: str) -> Dict:
    """Get specific trader configuration"""
    traders = get_traders()
    return traders.get(trader_id)

# ============================================================================
# Strategies
# ============================================================================

def get_strategies() -> Dict[str, Dict]:
    """Get all strategy configurations (all are active)"""
    config = load_config()
    return config.get('strategies', {})

def get_strategy(strategy_id: str) -> Dict:
    """Get specific strategy configuration"""
    strategies = get_strategies()
    return strategies.get(strategy_id)

# ============================================================================
# Pipeline Settings
# ============================================================================

def get_pipeline_settings() -> Dict:
    """Get pipeline settings"""
    config = load_config()
    return config.get('pipeline_settings', {})

# ============================================================================
# CLI Interface
# ============================================================================

def print_config_summary():
    """Print a summary of the current configuration"""
    config = load_config()

    print("="*60)
    print("FX Portfolio System Configuration")
    print("="*60)

    # Currencies
    currencies = config.get('currencies', [])
    print(f"\nCurrencies ({len(currencies)}):")
    print(f"  {', '.join(currencies)}")

    # Estimators
    estimators = config.get('horizon_estimators', {})
    print(f"\nHorizon Estimators ({len(estimators)}):")
    for est_id, est in estimators.items():
        print(f"  • {est_id} ({est['type']})")

    # Generators
    generators = config.get('signal_generators', {})
    print(f"\nSignal Generators ({len(generators)}):")
    for gen_id, gen in generators.items():
        print(f"  • {gen_id} ({gen['type']})")

    # Traders
    traders = config.get('traders', {})
    print(f"\nTraders ({len(traders)}):")
    for trader_id, trader in traders.items():
        print(f"  • {trader_id} ({trader['type']})")

    # Strategies
    strategies = config.get('strategies', {})
    print(f"\nStrategies ({len(strategies)}):")
    for strat_id, strat in strategies.items():
        params = strat.get('params', {})
        conf = params.get('confidence_threshold', 'N/A')
        size = params.get('trade_size_pct', 'N/A')
        print(f"  • {strat_id}: conf={conf}, size={size}")

    # Pipeline settings
    settings = config.get('pipeline_settings', {})
    print(f"\nPipeline Settings:")
    for key, value in settings.items():
        print(f"  • {key}: {value}")

    print("="*60)

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print_config_summary()
    else:
        command = sys.argv[1]

        if command == 'list-currencies':
            currencies = get_currencies()
            print('\n'.join(currencies))

        elif command == 'list-estimators':
            estimators = get_estimators()
            for est_id in estimators.keys():
                print(est_id)

        elif command == 'list-generators':
            generators = get_generators()
            for gen_id in generators.keys():
                print(gen_id)

        elif command == 'list-traders':
            traders = get_traders()
            for trader_id in traders.keys():
                print(trader_id)

        elif command == 'list-strategies':
            strategies = get_strategies()
            for strat_id in strategies.keys():
                print(strat_id)

        else:
            print(f"Unknown command: {command}")
            print("Available commands: list-currencies, list-estimators, list-generators, list-traders, list-strategies")
