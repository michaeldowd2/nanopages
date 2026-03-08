#!/usr/bin/env python3
"""
Pipeline Path Helper - Config-driven path management

Provides helper functions for scripts to get input/output paths from config
instead of hardcoding them. Makes the system more maintainable and config-driven.

Usage:
    from utilities.pipeline_paths import PipelinePaths

    paths = PipelinePaths(process_id='1')

    # Get output path
    output_file = paths.get_output_path(date='2024-01-15')

    # Get input paths
    input_files = paths.get_input_paths(date='2024-01-15', currency='EUR')
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional


class PipelinePaths:
    """Helper class for managing pipeline input/output paths from config."""

    def __init__(self, process_id: str, config_path: Optional[str] = None):
        """
        Initialize path helper for a specific process.

        Args:
            process_id: Process ID (e.g., '1', '2', '3', ...)
            config_path: Optional path to pipeline_steps.json (auto-detected if None)
        """
        self.process_id = str(process_id)

        # Find base directory (fx-portfolio/)
        if config_path:
            self.base_dir = Path(config_path).parent.parent
        else:
            # Auto-detect from script location
            self.base_dir = Path(__file__).parent.parent.parent

        # Load config
        config_file = self.base_dir / "config" / "pipeline_steps.json"
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        with open(config_file, 'r') as f:
            self.config = json.load(f)

        # Get process config
        steps = self.config.get('steps', {})
        if self.process_id not in steps:
            raise ValueError(f"Process ID '{self.process_id}' not found in config")

        self.process = steps[self.process_id]

    def get_output_path(self, date: Optional[str] = None, currency: Optional[str] = None,
                       source: Optional[str] = None, **kwargs) -> Path:
        """
        Get the primary output path for this process.

        Args:
            date: Date string (YYYY-MM-DD format)
            currency: Currency code (e.g., 'EUR', 'USD')
            source: Source identifier (e.g., for news sources)
            **kwargs: Additional template variables

        Returns:
            Absolute Path object for the output file

        Example:
            paths = PipelinePaths('1')
            output = paths.get_output_path(date='2024-01-15')
            # Returns: /path/to/fx-portfolio/data/prices/fx-rates-2024-01-15.json
        """
        outputs = self.process.get('outputs', {})
        primary = outputs.get('primary', '')

        if not primary:
            raise ValueError(f"Process {self.process_id} has no primary output defined")

        # Replace template variables
        template_vars = {
            'date': date or '',
            'currency': currency or '',
            'source': source or '',
            **kwargs
        }

        path_str = primary
        for key, value in template_vars.items():
            path_str = path_str.replace(f'{{{key}}}', value)

        return self.base_dir / path_str

    def get_input_paths(self, date: Optional[str] = None, currency: Optional[str] = None,
                       **kwargs) -> List[Path]:
        """
        Get input paths for this process.

        Args:
            date: Date string (YYYY-MM-DD format)
            currency: Currency code
            **kwargs: Additional template variables

        Returns:
            List of absolute Path objects for input files

        Example:
            paths = PipelinePaths('2')
            inputs = paths.get_input_paths(date='2024-01-15')
            # Returns: [/path/to/fx-portfolio/data/prices/fx-rates-2024-01-15.json]
        """
        inputs = self.process.get('inputs', [])

        if not inputs:
            return []

        # Replace template variables
        template_vars = {
            'date': date or '',
            'currency': currency or '',
            **kwargs
        }

        result = []
        for input_pattern in inputs:
            path_str = input_pattern
            for key, value in template_vars.items():
                path_str = path_str.replace(f'{{{key}}}', value)

            # Handle wildcards - return the pattern, caller can glob it
            result.append(self.base_dir / path_str)

        return result

    def get_output_patterns(self) -> List[str]:
        """
        Get output file patterns for this process.

        Returns:
            List of glob patterns for output files (relative to base_dir)

        Example:
            paths = PipelinePaths('1')
            patterns = paths.get_output_patterns()
            # Returns: ['data/prices/fx-rates-*.json']
        """
        outputs = self.process.get('outputs', {})
        return outputs.get('patterns', [])

    def get_data_dir(self, subdir: str) -> Path:
        """
        Get path to a data subdirectory.

        Args:
            subdir: Subdirectory name (e.g., 'prices', 'indices', 'news')

        Returns:
            Absolute Path object for the subdirectory

        Example:
            paths = PipelinePaths('1')
            prices_dir = paths.get_data_dir('prices')
            # Returns: /path/to/fx-portfolio/data/prices
        """
        data_dir = self.base_dir / "data" / subdir
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def get_process_info(self) -> Dict:
        """
        Get full process configuration.

        Returns:
            Dictionary with process configuration
        """
        return self.process.copy()

    @staticmethod
    def get_base_dir() -> Path:
        """
        Get the base directory (fx-portfolio/).

        Returns:
            Absolute Path object for base directory
        """
        return Path(__file__).parent.parent.parent


# Convenience functions for common operations

def get_output_path(process_id: str, date: Optional[str] = None,
                   currency: Optional[str] = None, **kwargs) -> Path:
    """
    Convenience function to get output path without creating PipelinePaths object.

    Args:
        process_id: Process ID
        date: Date string
        currency: Currency code
        **kwargs: Additional template variables

    Returns:
        Absolute Path object for output file

    Example:
        from utilities.pipeline_paths import get_output_path
        output = get_output_path('1', date='2024-01-15')
    """
    paths = PipelinePaths(process_id)
    return paths.get_output_path(date=date, currency=currency, **kwargs)


def get_input_paths(process_id: str, date: Optional[str] = None,
                   currency: Optional[str] = None, **kwargs) -> List[Path]:
    """
    Convenience function to get input paths without creating PipelinePaths object.

    Args:
        process_id: Process ID
        date: Date string
        currency: Currency code
        **kwargs: Additional template variables

    Returns:
        List of absolute Path objects for input files

    Example:
        from utilities.pipeline_paths import get_input_paths
        inputs = get_input_paths('2', date='2024-01-15')
    """
    paths = PipelinePaths(process_id)
    return paths.get_input_paths(date=date, currency=currency, **kwargs)


def get_data_dir(subdir: str) -> Path:
    """
    Convenience function to get data subdirectory path.

    Args:
        subdir: Subdirectory name

    Returns:
        Absolute Path object for subdirectory

    Example:
        from utilities.pipeline_paths import get_data_dir
        prices_dir = get_data_dir('prices')
    """
    base_dir = Path(__file__).parent.parent.parent
    data_dir = base_dir / "data" / subdir
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir
