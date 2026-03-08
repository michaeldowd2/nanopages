# pipeline-paths

**Config-driven path management helper for pipeline scripts.**

## Purpose

The `pipeline_paths` module eliminates hardcoded paths in pipeline scripts by providing helper functions that read input/output paths from `config/pipeline_steps.json`. This makes the system more maintainable and ensures consistency across all scripts.

**Benefits**:
- Single source of truth for all paths
- Easy to refactor directory structure
- No hardcoded paths in scripts
- Type-safe Path objects
- Template variable support (date, currency, etc.)

---

## Quick Start

### Basic Usage

```python
from utilities.pipeline_paths import PipelinePaths

# Initialize for your process
paths = PipelinePaths(process_id='1')

# Get output path with date template
output_file = paths.get_output_path(date='2024-01-15')
# Returns: /path/to/fx-portfolio/data/prices/fx-rates-2024-01-15.json

# Get input paths
inputs = paths.get_input_paths(date='2024-01-15')
# Returns: [Path('/path/to/fx-portfolio/data/...')]
```

### Convenience Functions

```python
from utilities.pipeline_paths import get_output_path, get_input_paths, get_data_dir

# Quick path lookups without creating object
output = get_output_path('1', date='2024-01-15')
inputs = get_input_paths('2', date='2024-01-15')
prices_dir = get_data_dir('prices')
```

---

## API Reference

### PipelinePaths Class

#### `__init__(process_id, config_path=None)`

Initialize path helper for a specific process.

**Parameters**:
- `process_id` (str): Process ID from config (e.g., '1', '2', '3')
- `config_path` (str, optional): Path to pipeline_steps.json (auto-detected if None)

**Example**:
```python
paths = PipelinePaths('1')  # Exchange Rates
paths = PipelinePaths('5')  # Sentiment Signals
```

#### `get_output_path(date=None, currency=None, source=None, **kwargs)`

Get the primary output path for this process.

**Parameters**:
- `date` (str): Date in YYYY-MM-DD format
- `currency` (str): Currency code (EUR, USD, etc.)
- `source` (str): Source identifier
- `**kwargs`: Additional template variables

**Returns**: `Path` object

**Examples**:
```python
# Process 1: Exchange Rates
paths = PipelinePaths('1')
output = paths.get_output_path(date='2024-01-15')
# → data/prices/fx-rates-2024-01-15.json

# Process 2: Currency Indices
paths = PipelinePaths('2')
output = paths.get_output_path(currency='EUR')
# → data/indices/EUR_index.json

# Process 3: News
paths = PipelinePaths('3')
output = paths.get_output_path(currency='EUR', date='2024-01-15', source='newsapi')
# → data/news/EUR/2024-01-15_newsapi.json
```

#### `get_input_paths(date=None, currency=None, **kwargs)`

Get input paths for this process.

**Parameters**:
- `date` (str): Date in YYYY-MM-DD format
- `currency` (str): Currency code
- `**kwargs`: Additional template variables

**Returns**: `List[Path]`

**Examples**:
```python
# Process 2: Currency Indices (depends on Process 1)
paths = PipelinePaths('2')
inputs = paths.get_input_paths(date='2024-01-15')
# → [Path('data/prices/fx-rates-2024-01-15.json')]

# Process 6: Signal Realization (depends on 2, 4, 5)
paths = PipelinePaths('6')
inputs = paths.get_input_paths(date='2024-01-15', currency='EUR')
# → [Path('data/signals/EUR/2024-01-15.json'),
#    Path('data/article-analysis/2024-01-15.json'),
#    Path('data/indices/EUR_index.json')]
```

#### `get_output_patterns()`

Get output file glob patterns for this process.

**Returns**: `List[str]` - Patterns relative to base directory

**Example**:
```python
paths = PipelinePaths('1')
patterns = paths.get_output_patterns()
# → ['data/prices/fx-rates-*.json']
```

#### `get_data_dir(subdir)`

Get path to a data subdirectory (creates if needed).

**Parameters**:
- `subdir` (str): Subdirectory name

**Returns**: `Path` object

**Example**:
```python
paths = PipelinePaths('1')
prices_dir = paths.get_data_dir('prices')
# → /path/to/fx-portfolio/data/prices
# (directory is created if it doesn't exist)
```

#### `get_process_info()`

Get full process configuration from config file.

**Returns**: `Dict` with process configuration

**Example**:
```python
paths = PipelinePaths('1')
info = paths.get_process_info()
# → {'id': '1', 'name': 'Exchange Rates', 'script': '...', ...}
```

---

## Convenience Functions

### `get_output_path(process_id, date=None, currency=None, **kwargs)`

Quick output path lookup without creating object.

```python
from utilities.pipeline_paths import get_output_path

output = get_output_path('1', date='2024-01-15')
```

### `get_input_paths(process_id, date=None, currency=None, **kwargs)`

Quick input paths lookup without creating object.

```python
from utilities.pipeline_paths import get_input_paths

inputs = get_input_paths('2', date='2024-01-15')
```

### `get_data_dir(subdir)`

Quick data directory path lookup.

```python
from utilities.pipeline_paths import get_data_dir

prices_dir = get_data_dir('prices')
signals_dir = get_data_dir('signals')
```

---

## Usage Examples

### Example 1: Fetch Exchange Rates (Process 1)

```python
from utilities.pipeline_paths import PipelinePaths

def fetch_rates(date):
    paths = PipelinePaths('1')

    # Get output path from config
    output_file = paths.get_output_path(date=date)

    # Fetch rates from API
    rates = fetch_from_api()

    # Save to config-defined location
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(rates, f, indent=2)
```

### Example 2: Calculate Currency Indices (Process 2)

```python
from utilities.pipeline_paths import PipelinePaths

def calculate_indices(date, currency):
    paths = PipelinePaths('2')

    # Get input path from config
    input_files = paths.get_input_paths(date=date)

    # Load exchange rates
    with open(input_files[0], 'r') as f:
        rates = json.load(f)

    # Calculate index
    index = calculate_index(rates, currency)

    # Save to config-defined location
    output_file = paths.get_output_path(currency=currency)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(index, f, indent=2)
```

### Example 3: Multiple Inputs (Process 6)

```python
from utilities.pipeline_paths import PipelinePaths
import glob

def check_realization(date):
    paths = PipelinePaths('6')

    # Get input patterns
    input_patterns = paths.get_input_paths(date=date, currency='*')

    # Expand wildcards
    signal_files = glob.glob(str(input_patterns[0]))
    horizon_file = input_patterns[1]
    index_pattern = input_patterns[2]

    # Process data...
    result = process_signals(signal_files, horizon_file, index_pattern)

    # Save to config-defined location
    output_file = paths.get_output_path(date=date)
    save_result(result, output_file)
```

---

## Migration Guide

### Before (Hardcoded Paths)

```python
import os
from pathlib import Path

# Hardcoded paths
BASE_DIR = Path(__file__).parent.parent
output_file = BASE_DIR / "data" / "prices" / f"fx-rates-{date}.json"

# Must update path in code if directory structure changes
```

### After (Config-Driven)

```python
from utilities.pipeline_paths import get_output_path

# Path comes from config
output_file = get_output_path('1', date=date)

# Directory structure changes only require config update
```

---

## Template Variables

Paths in config can use template variables that are replaced at runtime:

| Variable | Description | Example |
|----------|-------------|---------|
| `{date}` | Date in YYYY-MM-DD format | `2024-01-15` |
| `{currency}` | Currency code | `EUR`, `USD`, `GBP` |
| `{source}` | Source identifier | `newsapi`, `rss` |

**Config Example**:
```json
{
  "outputs": {
    "primary": "data/news/{currency}/{date}_{source}.json"
  }
}
```

**Usage**:
```python
path = paths.get_output_path(
    currency='EUR',
    date='2024-01-15',
    source='newsapi'
)
# → data/news/EUR/2024-01-15_newsapi.json
```

---

## Error Handling

### Invalid Process ID

```python
try:
    paths = PipelinePaths('99')  # Invalid
except ValueError as e:
    print(f"Error: {e}")
    # Error: Process ID '99' not found in config
```

### Missing Config File

```python
try:
    paths = PipelinePaths('1', config_path='/wrong/path')
except FileNotFoundError as e:
    print(f"Error: {e}")
    # Error: Config file not found: /wrong/path/config/pipeline_steps.json
```

### Missing Output Definition

```python
try:
    paths = PipelinePaths('4.1')  # Currency Events (static data)
    output = paths.get_output_path()
except ValueError as e:
    print(f"Error: {e}")
    # Note: Process 4.1 does have output, but this shows the error pattern
```

---

## Benefits

### 1. Single Source of Truth
All paths defined in one place (`config/pipeline_steps.json`)

### 2. Easy Refactoring
Change `data/prices/` to `data/exchange-rates/` in config only

### 3. Consistency
All scripts use same path resolution logic

### 4. Type Safety
Returns `Path` objects, not strings

### 5. Auto-Create Directories
`get_data_dir()` creates directories automatically

### 6. Template Support
Dynamic paths with variable substitution

---

## Related

- **Configuration**: See `config/pipeline_steps.json` for path definitions
- **Architecture**: See `docs/ARCHITECTURE.md` for system overview
- **Config Loader**: See `scripts/utilities/config_loader.py` for system config
