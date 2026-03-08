#!/usr/bin/env python3
"""
Environment Variable Loader for FX Portfolio
Centralized utility for loading .env files across all scripts
"""

import os


def load_env_file():
    """
    Load environment variables from .env file

    Searches multiple possible locations for .env file:
    1. /workspace/project/.env (container-level config)
    2. /workspace/group/.env (group-level config)
    3. Script directory/../.env (project-level config)

    Returns:
        bool: True if .env file was found and loaded, False otherwise
    """
    env_paths = [
        '/workspace/project/.env',           # Container-level (recommended)
        '/workspace/group/.env',             # Group-level
        os.path.join(os.path.dirname(__file__), '../.env')  # Project-level
    ]

    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Only set if not already in environment (allow override)
                        if key not in os.environ:
                            os.environ[key] = value
            return True
    return False


def get_env_var(key, default=None, required=False):
    """
    Get environment variable with better error handling

    Args:
        key: Environment variable name
        default: Default value if not found
        required: If True, raises ValueError if not found

    Returns:
        str: Environment variable value or default

    Raises:
        ValueError: If required=True and variable not found
    """
    value = os.environ.get(key, default)

    if required and value is None:
        raise ValueError(
            f"Required environment variable '{key}' not found. "
            f"Please set it in /workspace/project/.env file."
        )

    return value


# Auto-load on import
load_env_file()


# Convenience functions for common API keys
def get_newsapi_key():
    """Get NewsAPI key from environment"""
    return get_env_var('NEWSAPI_APIKEY') or get_env_var('newsapi_apikey')


def get_anthropic_key():
    """Get Anthropic API key from environment"""
    return get_env_var('ANT_API_KEY') or get_env_var('ant_api_key')


def get_github_token():
    """Get GitHub token from environment"""
    return get_env_var('GITHUB_TOKEN')


# Export commonly used functions
__all__ = ['load_env_file', 'get_env_var', 'get_newsapi_key', 'get_anthropic_key', 'get_github_token']
