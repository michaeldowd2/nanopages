# Environment Variables Guide

**Date**: 2026-02-24
**Status**: Standardized across all scripts

---

## Overview

All scripts in the FX Portfolio project use a **centralized environment loader** (`env_loader.py`) to access API keys and configuration from `.env` files.

---

## .env File Location

**Primary location**: `/workspace/project/.env`

This is the container-level configuration file that contains:
- `NEWSAPI_APIKEY` - NewsAPI.org API key
- `ANTHROPIC_API_KEY` - Anthropic Claude API key
- `GITHUB_TOKEN` - GitHub personal access token
- `GITHUB_REPO` - GitHub repository URL
- `TELEGRAM_BOT_TOKEN` - Telegram bot token (for nano)
- Other service credentials

**Fallback locations** (checked in order):
1. `/workspace/project/.env` (recommended)
2. `/workspace/group/.env`
3. `/workspace/group/fx-portfolio/.env`

---

## Using Environment Variables in Scripts

### Standard Approach (Recommended)

All scripts should use the centralized `env_loader.py`:

```python
#!/usr/bin/env python3
import sys
import os

# Add scripts directory to path
sys.path.append(os.path.dirname(__file__))
from env_loader import get_newsapi_key, get_anthropic_key

# Get API keys
newsapi_key = get_newsapi_key()
anthropic_key = get_anthropic_key()

if not newsapi_key:
    print("⚠️ NewsAPI key not found. Set NEWSAPI_APIKEY in /workspace/project/.env")
```

### Available Helper Functions

```python
from env_loader import (
    get_newsapi_key,      # Get NewsAPI key
    get_anthropic_key,    # Get Anthropic API key
    get_github_token,     # Get GitHub token
    get_env_var           # Get any environment variable
)

# Get any environment variable with default
value = get_env_var('MY_VAR', default='fallback_value')

# Get required environment variable (raises error if not found)
value = get_env_var('REQUIRED_VAR', required=True)
```

---

## Current API Keys

### NewsAPI

**Variable**: `NEWSAPI_APIKEY`
**Used by**: `fetch-news.py`
**Free tier**: 100 requests/day
**Status**: ✅ Active and working

**Current value** (redacted): `dee0e81a...`

### Anthropic Claude API

**Variable**: `ANTHROPIC_API_KEY`
**Used by**: Future LLM-based sentiment analysis
**Status**: 🔄 Available but not yet integrated

**Potential use cases**:
- Step 4: Time horizon analysis (currently manual)
- Step 5: Enhanced sentiment analysis (currently keyword-based)
- News summarization
- Signal reasoning generation

### GitHub Token

**Variable**: `GITHUB_TOKEN`
**Used by**: Dashboard deployment (`publish-github-pages`)
**Status**: ✅ Active

### Other Keys

- `TELEGRAM_BOT_TOKEN` - For nano assistant
- `CLAUDE_CODE_OAUTH_TOKEN` - For Claude Code integration

---

## Migration Status

### ✅ Migrated to env_loader.py

1. **fetch-news.py**
   - Uses `get_newsapi_key()`
   - Removed inline .env loading code
   - Centralized through env_loader.py

### 📝 No Migration Needed

These scripts don't currently use API keys:
- `fetch-exchange-rates.py` - Uses free GitHub Currency API
- `calculate-currency-indices.py` - Pure calculation
- `generate-sentiment-signals.py` - Keyword-based (no API)
- `check-signal-realization.py` - Pure calculation
- `calculate-trades.py` - Pure logic
- `execute-trades.py` - Pure calculation
- `calculate-account-balances.py` - Pure logic
- `calculate-portfolio-performance.py` - Pure calculation
- `export-pipeline-data.py` - File processing only

### 🔮 Future Integration Candidates

Scripts that could benefit from API keys in future:

1. **analyze-time-horizons.py**
   - Current: Manual nanoclaw integration
   - Future: Use `get_anthropic_key()` for automated LLM analysis

2. **generate-sentiment-signals.py**
   - Current: Keyword-based sentiment
   - Future: Use `get_anthropic_key()` for LLM-based sentiment

---

## Best Practices

### 1. Always Use env_loader.py

❌ **Don't do this**:
```python
import os
api_key = os.environ.get('NEWSAPI_APIKEY')
```

✅ **Do this instead**:
```python
from env_loader import get_newsapi_key
api_key = get_newsapi_key()
```

**Why?**
- Centralized loading logic
- Automatic fallback to multiple .env locations
- Consistent error messages
- Easier to update/maintain

### 2. Graceful Degradation

Always handle missing API keys gracefully:

```python
api_key = get_newsapi_key()
if not api_key:
    print("⚠️ NewsAPI key not found, skipping NewsAPI queries")
    # Continue with RSS feeds only
else:
    # Fetch from NewsAPI
    pass
```

### 3. Don't Hardcode Secrets

❌ Never commit API keys to git:
```python
API_KEY = "<your-api-key-here>"  # NEVER DO THIS!
```

✅ Always load from environment:
```python
from env_loader import get_newsapi_key
API_KEY = get_newsapi_key()
```

### 4. Document Required Variables

At the top of your script, document required environment variables:

```python
"""
Script Name

Required environment variables:
- NEWSAPI_APIKEY: API key for NewsAPI.org (optional, degrades gracefully)
- ANTHROPIC_API_KEY: API key for Anthropic Claude (required for LLM features)

Set these in /workspace/project/.env
"""
```

---

## Troubleshooting

### Issue: "NewsAPI key not found"

**Symptoms**:
```
⚠️ NewsAPI key not found in environment (NEWSAPI_APIKEY)
   Set it in /workspace/project/.env file
```

**Solution**:
1. Check if .env file exists:
   ```bash
   ls -la /workspace/project/.env
   ```

2. Check if key is in the file:
   ```bash
   grep NEWSAPI_APIKEY /workspace/project/.env
   ```

3. If missing, add it:
   ```bash
   echo "NEWSAPI_APIKEY=your-key-here" >> /workspace/project/.env
   ```

4. Test the script again

### Issue: Environment variable not being read

**Cause**: Python may have cached the environment before .env was updated

**Solution**:
1. Restart the Python script
2. If using interactive Python, reload the env_loader:
   ```python
   import importlib
   import env_loader
   importlib.reload(env_loader)
   ```

### Issue: Different scripts using different .env locations

**Solution**: Use `env_loader.py` consistently. It checks all standard locations:
- `/workspace/project/.env` (primary)
- `/workspace/group/.env` (fallback)
- Project-relative `.env` (fallback)

---

## File Structure

```
/workspace/
├── project/
│   └── .env                          # Primary .env location ✅
├── group/
│   ├── .env                          # Fallback location
│   └── fx-portfolio/
│       ├── scripts/
│       │   ├── env_loader.py         # Centralized loader ⭐
│       │   ├── fetch-news.py         # Uses get_newsapi_key()
│       │   └── [other scripts]
│       └── docs/
│           └── ENVIRONMENT_VARIABLES_GUIDE.md  # This file
```

---

## Summary

**Current state**:
- ✅ Centralized environment loader (`env_loader.py`)
- ✅ NewsAPI integration using env_loader
- ✅ Consistent approach across scripts
- ✅ Graceful degradation when keys missing
- ✅ Clear error messages

**Best practice**:
```python
from env_loader import get_newsapi_key

api_key = get_newsapi_key()
if not api_key:
    print("⚠️ Missing API key, see /workspace/group/fx-portfolio/docs/ENVIRONMENT_VARIABLES_GUIDE.md")
```

**Future additions**:
- Integrate Anthropic API for LLM-based analysis
- Use env_loader consistently in all new scripts
- Document all required environment variables
