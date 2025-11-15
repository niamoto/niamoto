# Complete Corrections Plan for Niamoto

## Executive Summary

This document compiles **all identified issues** in the Niamoto system and proposes concrete, prioritized, and estimated corrections. Issues are classified by criticality: 🔴 Critical, 🟠 Important, 🟡 Moderate, 🟢 Enhancement.

**Total estimated impact**: 3-6 months to fix everything, but critical fixes can be done in 2-3 weeks.

---

## 1. CRITICAL ISSUES 🔴 (Fix Immediately)

### 1.1 Plaintext Secrets in YAML ✅

**Problem**
```yaml
# test-instance/niamoto-og/config/import.yml:22
auth_params:
  key: "1e106508-9a86-4242-9012-d6cafdea3374"  # Plaintext API key!
```

**Solution**
```python
# src/niamoto/common/config.py - Add environment variable support
import os
from string import Template

class Config:
    def _load_yaml_with_env(self, path: str) -> dict:
        """Load YAML with environment variable substitution"""
        with open(path) as f:
            content = f.read()

        # Replace ${VAR_NAME} with environment value
        template = Template(content)
        resolved = template.safe_substitute(os.environ)

        return yaml.safe_load(resolved)
```

```yaml
# config/import.yml - Secure version
auth_params:
  key: ${ENDEMIA_API_KEY}  # Environment variable
```

```bash
# .env.example
ENDEMIA_API_KEY=your-key-here
DATABASE_URL=postgresql://...
```

**Effort**: 4 hours — ✅ delivered (${VAR} / ${VAR:-default} substitution in `Config._load_yaml_with_defaults`).
**Impact**: Critical security — keys must no longer appear in plaintext.

---

### 1.2 Inconsistent Parameter Validation ✅

**Problem**
```python
# src/niamoto/core/services/transformer.py:190
# Passes raw dict without validation!
result = plugin.transform(data, config['params'])  # Dangerous
```

**Solution**
```python
# src/niamoto/core/services/transformer.py - Centralized validation
from pydantic import ValidationError

class TransformerService:
    def execute_widget(self, widget_config: dict, data: Any) -> Any:
        """Execute a widget with centralized validation"""

        plugin_name = widget_config.get('plugin')
        plugin = self.registry.get(plugin_name)

        # NEW: Validation BEFORE call
        try:
            # Use plugin's param_schema for validation
            if hasattr(plugin, 'param_schema'):
                validated_params = plugin.param_schema(**widget_config.get('params', {}))
            else:
                # Fallback for legacy plugins
                validated_params = widget_config.get('params', {})
                logger.warning(f"Plugin {plugin_name} has no param_schema")
        except ValidationError as e:
            raise ValueError(f"Invalid params for {plugin_name}: {e}")

        # Call with validated params (Pydantic object, not dict)
        return plugin.transform(data, validated_params)
```

**Effort**: 1 day — ✅ delivered (`TransformerService.transform_data` now calls `_validate_plugin_configuration`).
**Impact**: Critical stability (invalid plugins blocked before execution).

---

### 1.3 Strong Plugin Coupling

**Problem**
```python
# src/niamoto/core/plugins/transformers/aggregation/field_aggregator.py:101
class FieldAggregator(TransformerPlugin):
    def __init__(self, db):
        super().__init__(db)
        # PROBLEM: Direct access to global config!
        self.config = Config()
        self.imports_config = self.config.get_imports_config
```

**Solution**
```python
# src/niamoto/core/plugins/base.py - Dependency injection
from typing import Protocol

class DataProvider(Protocol):
    """Interface for data access"""
    def get_table_data(self, table: str, filters: dict = None) -> pd.DataFrame:
        ...

    def get_config_value(self, key: str) -> Any:
        ...

class TransformerPlugin(Plugin, ABC):
    """Plugin with dependency injection"""

    def __init__(self, data_provider: DataProvider):
        self.data_provider = data_provider  # Interface, not implementation

    @abstractmethod
    def transform(self, data: Any, params: BaseModel) -> Any:
        """Transform with validated params"""
        pass

# src/niamoto/core/services/transformer.py
class TransformerService:
    def __init__(self):
        # Create centralized provider
        self.data_provider = DataProviderImpl(self.db, self.config)

    def create_plugin(self, plugin_class):
        """Inject dependencies"""
        return plugin_class(self.data_provider)
```

**Effort**: 2 days
**Impact**: Architecture, testability

---

## 2. PERFORMANCE ISSUES 🟠

### 2.1 Repetitive Data Reloading (TRANSFORM + EXPORT)

**Confirmed Problem in Code**

**A. In TransformerService** (`src/niamoto/core/services/transformer.py:186-236`)
```python
# For each group_id, load data
for group_id in group_ids:
    group_data = self._get_group_data(group_config, csv_file, group_id)  # Line 188

    # Then for each widget, some plugins make their own queries!
    for widget_name, widget_config in widgets_config.items():
        transformer = PluginRegistry.get_plugin(...)
        widget_results = transformer.transform(data_to_pass, config)  # Line 236
```

**Concrete Example**: `field_aggregator.py:108-113` and `binary_counter.py:108-113`
```python
# Plugin reloads data even though it's already passed as parameter!
if params.source != "occurrences":
    sql_query = f"SELECT * FROM {params.source}"
    result = self.db.execute_select(sql_query)  # Redundant query
    data = pd.DataFrame(result.fetchall(), ...)
```

**B. In HtmlPageExporter** (`src/niamoto/core/plugins/exporters/html_page_exporter.py:660-710`)
```python
# Load index once
index_data = self._get_group_index_data(repository, table_name, id_column)  # Line 660

# THEN for EACH item, make a complete SQL query!
for item_summary in index_data:  # Line 696
    item_data = self._get_item_detail_data(  # Line 708
        repository, table_name, id_column, item_id
    )
    # Line 1238: SELECT * FROM "{table_name}" WHERE "{id_column}" = :item_id
```

**Result**: For 1000 taxa = **1001 SQL queries** (1 index + 1000 details)!

**C. In JsonApiExporter** (`src/niamoto/core/plugins/exporters/json_api_exporter.py:697-750`)
```python
# Line 708: Load ENTIRE group at once (BETTER)
query = text(f"SELECT * FROM {table_name}")

# Line 726-742: BUT parse JSON for EACH cell of EACH row
for col_name, col_value in row_dict.items():
    if col_value:
        if isinstance(col_value, str):
            data = json.loads(col_value)  # Repetitive parsing!
```

**Measured Impact**:
- 1000 items × 20 columns = **20,000 calls to json.loads()** potential
- Navigation cache lost between exports (line 53: `self._navigation_cache = {}` reinitialized)

**Optimal Solution: Unified DataContext**

```python
# src/niamoto/core/services/data_context.py
from typing import Dict, Any, Optional, Callable, List
import time
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

class DataContext:
    """Shared data context between Transform and Export with intelligent cache"""

    def __init__(self, db, ttl: int = 3600):
        """
        Args:
            db: Database instance
            ttl: Cache time-to-live in seconds (default: 1h)
        """
        self.db = db
        self._cache: Dict[str, tuple[float, Any]] = {}
        self._ttl = ttl
        self._json_cache: Dict[int, Any] = {}  # JSON parsing cache

    def get_or_load(self, cache_key: str, loader_fn: Callable, *args, **kwargs) -> Any:
        """
        Retrieve from cache or execute loader

        Args:
            cache_key: Unique cache key
            loader_fn: Function that loads data if not in cache
            *args, **kwargs: Arguments for loader_fn

        Returns:
            Data (from cache or freshly loaded)
        """
        # Check cache
        if cache_key in self._cache:
            timestamp, data = self._cache[cache_key]
            age = time.time() - timestamp

            if age < self._ttl:
                logger.debug(f"Cache hit: {cache_key} (age: {age:.1f}s)")
                return data
            else:
                logger.debug(f"Cache expired: {cache_key} (age: {age:.1f}s)")
                del self._cache[cache_key]

        # Load and cache
        logger.debug(f"Cache miss: {cache_key}, loading...")
        data = loader_fn(*args, **kwargs)
        self._cache[cache_key] = (time.time(), data)
        return data

    def get_all_items(self, table_name: str, id_column: str = None) -> List[Dict[str, Any]]:
        """
        Load all items from a table (with cache)

        Args:
            table_name: Table name
            id_column: ID column (for sorting)

        Returns:
            List of dictionaries representing rows
        """
        cache_key = f"all_items:{table_name}"

        def loader():
            if id_column:
                query = f'SELECT * FROM "{table_name}" ORDER BY "{id_column}"'
            else:
                query = f'SELECT * FROM "{table_name}"'

            results = self.db.fetch_all(query)
            items = [dict(row) for row in results]
            logger.info(f"Loaded {len(items)} items from {table_name}")
            return items

        return self.get_or_load(cache_key, loader)

    def get_item_by_id(self, table_name: str, id_column: str, item_id: Any) -> Optional[Dict[str, Any]]:
        """
        Retrieve ONE item by ID using all items cache
        (avoids individual SQL queries)

        Args:
            table_name: Table name
            id_column: ID column name
            item_id: ID value to search for

        Returns:
            Item dict or None if not found
        """
        # Load ALL items once (cached)
        all_items = self.get_all_items(table_name, id_column)

        # Search item in cached list
        for item in all_items:
            if item.get(id_column) == item_id:
                return item

        logger.warning(f"Item {id_column}={item_id} not found in {table_name}")
        return None

    def parse_json_cached(self, value: str) -> Any:
        """
        Parse JSON with cache to avoid repetitive parsing

        Args:
            value: JSON string to parse

        Returns:
            Parsed Python object
        """
        if not isinstance(value, str):
            return value

        # Use hash as key (faster than storing complete string)
        cache_key = hash(value)

        if cache_key in self._json_cache:
            return self._json_cache[cache_key]

        try:
            parsed = json.loads(value)
            self._json_cache[cache_key] = parsed
            return parsed
        except json.JSONDecodeError:
            # Not valid JSON, return as-is
            return value

    def invalidate(self, pattern: str = None):
        """
        Invalidate cache (partially or completely)

        Args:
            pattern: If provided, only invalidate keys containing this pattern
        """
        if pattern:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for k in keys_to_remove:
                del self._cache[k]
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching '{pattern}'")
        else:
            count = len(self._cache)
            self._cache.clear()
            self._json_cache.clear()
            logger.info(f"Invalidated entire cache ({count} entries)")

    def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics"""
        total_size = sum(
            len(str(data)) for _, data in self._cache.values()
        )
        return {
            "entries": len(self._cache),
            "json_cache_entries": len(self._json_cache),
            "total_size_bytes": total_size,
            "ttl_seconds": self._ttl
        }
```

**Integration in TransformerService**

```python
# src/niamoto/core/services/transformer.py
class TransformerService:
    def __init__(
        self,
        db_path: str,
        config: Config,
        *,
        data_context: Optional[DataContext] = None,
        enable_cli_integration: bool | None = None,
    ):
        self.db = Database(db_path)
        self.config = config

        # Inject or create DataContext
        self.data_context = data_context or DataContext(self.db)

        # ... rest of code
```

**Integration in HtmlPageExporter**

```python
# src/niamoto/core/plugins/exporters/html_page_exporter.py
class HtmlPageExporter(ExporterPlugin):

    def __init__(self, db: Database, data_context: Optional[DataContext] = None):
        super().__init__(db)
        self.data_context = data_context or DataContext(db)
        # ... rest of code

    def _get_item_detail_data(
        self, repository: Database, table_name: str, id_column: str, item_id: Any
    ) -> Optional[Dict[str, Any]]:
        """Use cache to avoid repeated queries"""
        return self.data_context.get_item_by_id(table_name, id_column, item_id)

    def _load_and_cache_navigation_data(
        self, referential_data_source: str, required_fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Use shared DataContext instead of local cache"""
        return self.data_context.get_all_items(referential_data_source)
```

**Integration in JsonApiExporter**

```python
# src/niamoto/core/plugins/exporters/json_api_exporter.py
class JsonApiExporter(ExporterPlugin):

    def __init__(self, db: Database, data_context: Optional[DataContext] = None):
        super().__init__(db)
        self.data_context = data_context or DataContext(db)
        # ... rest of code

    def _fetch_group_data(
        self, repository: Database, data_source: str, group_name: str
    ) -> List[Dict[str, Any]]:
        """Use cache to avoid reloading"""
        # Use get_all_items which is cached
        items = self.data_context.get_all_items(group_name)

        # Parse JSON with cache
        result = []
        for item in items:
            parsed_item = {}
            for col_name, col_value in item.items():
                if col_value:
                    parsed_item[col_name] = self.data_context.parse_json_cached(col_value)
                else:
                    parsed_item[col_name] = col_value
            result.append(parsed_item)

        return result
```

**CLI Flag Addition**

```python
# src/niamoto/cli/commands.py
@click.option('--clear-cache', is_flag=True, help='Clear data cache before processing')
def transform(clear_cache: bool, ...):
    """Transform data"""
    service = TransformerService(db_path, config)

    if clear_cache:
        service.data_context.invalidate()
        click.echo("✓ Cache cleared")

    service.transform_data(...)
```

**Before/After Comparison**

| Scenario | Before | After | Gain |
|----------|-------|-------|------|
| HTML Export 1000 taxa | 1001 SQL queries | **1 query** | **x1000** |
| Transform 1000 taxa × 20 widgets | Data reloaded by some plugins | Shared cache | **x3-5** |
| JSON parsing (1000 items × 20 cols) | 20,000 `json.loads()` | **~100** (deduplicated) | **x200** |
| HTML then JSON export (same group) | 2 complete loads | **1 load** (shared) | **x2** |

**Advantages of this solution**:
1. ✅ **Works with instance methods** (no `@lru_cache` issue)
2. ✅ **Integrates with existing loader pattern**
3. ✅ **Shared cache between Transform AND Export**
4. ✅ **Handles invalidation by TTL and manual**
5. ✅ **Caches JSON parsing** (issue not mentioned in original doc)
6. ✅ **Cache stats for monitoring**

**Effort**: 2 days (vs 1 day initially estimated)
- Day 1: Implement DataContext + TransformerService integration
- Day 2: Exporter integration + tests + CLI flag

**Impact**: Performance **x5-15** (vs x5-10 estimated)
- x5 minimum on small datasets
- x15 on large datasets with many JSON columns

---

### 2.2 Sequential Pipeline (No Parallelization)

**Problem**
```python
# Current: Everything is sequential
for taxon in taxons:        # 1000 taxa
    for widget in widgets:   # 20 widgets
        process()            # = 20,000 sequential operations!
```

**Solution**
```python
# src/niamoto/core/services/parallel_transformer.py
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import List
import multiprocessing as mp

class ParallelTransformerService:
    """Service with parallelization"""

    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or mp.cpu_count()

    def process_taxons_parallel(self, taxon_ids: List[int]):
        """Process taxa in parallel"""

        # Use ProcessPool for heavy computations
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            for taxon_id in taxon_ids:
                future = executor.submit(self.process_single_taxon, taxon_id)
                futures.append(future)

            # Collect results
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except TimeoutError:
                    logger.error(f"Timeout processing taxon")

        return results

    def process_widgets_parallel(self, taxon_id: int, widgets: List[dict]):
        """Process independent widgets in parallel"""

        # Identify independent widgets
        independent = self.identify_independent_widgets(widgets)
        dependent = [w for w in widgets if w not in independent]

        # Parallelize independent ones
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(self.process_widget, taxon_id, w): w
                for w in independent
            }

            results = {}
            for future in as_completed(futures):
                widget = futures[future]
                results[widget['name']] = future.result()

        # Then dependent ones in sequence
        for widget in dependent:
            results[widget['name']] = self.process_widget(taxon_id, widget, results)

        return results
```

**Effort**: 2 days
**Impact**: Performance x4-8 on multi-core

---

### 2.3 No Cache for Expensive Transformations

**Problem**
```python
# Constant recalculation of same transformations
process_taxon(123)  # 10 seconds
process_taxon(123)  # 10 seconds again! (same result)
```

**Solution**
```python
# src/niamoto/core/cache/transform_cache.py
import pickle
import hashlib
from pathlib import Path
from typing import Optional

class TransformCache:
    """Persistent cache for transformations"""

    def __init__(self, cache_dir: str = ".niamoto_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def get_cache_key(self, entity_id: str, widget: str, params: dict) -> str:
        """Generate unique cache key"""
        # Hash params to detect changes
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()

        return f"{entity_id}_{widget}_{params_hash}"

    def get(self, entity_id: str, widget: str, params: dict) -> Optional[Any]:
        """Retrieve from cache if exists"""
        key = self.get_cache_key(entity_id, widget, params)
        cache_file = self.cache_dir / f"{key}.pkl"

        if cache_file.exists():
            # Check freshness (24h)
            age = time.time() - cache_file.stat().st_mtime
            if age < 86400:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)

        return None

    def set(self, entity_id: str, widget: str, params: dict, data: Any):
        """Save to cache"""
        key = self.get_cache_key(entity_id, widget, params)
        cache_file = self.cache_dir / f"{key}.pkl"

        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)

    def invalidate(self, entity_id: str = None):
        """Invalidate cache"""
        if entity_id:
            # Invalidate only for this entity
            for file in self.cache_dir.glob(f"{entity_id}_*.pkl"):
                file.unlink()
        else:
            # Invalidate everything
            for file in self.cache_dir.glob("*.pkl"):
                file.unlink()
```

**Effort**: 1 day
**Impact**: Performance x10-100 on re-runs

---

## 3. MAINTAINABILITY ISSUES 🟡

### 3.1 Monolithic YAML Configuration

**Problem**
```yaml
# transform.yml: 900+ lines!
# export.yml: 1600+ lines!
```

**Solution**
```python
# src/niamoto/config/modular_loader.py
class ModularConfigLoader:
    """Load modular configs with includes"""

    def load_config(self, main_file: str) -> dict:
        """Load config with includes support"""

        with open(main_file) as f:
            config = yaml.safe_load(f)

        # Resolve includes
        config = self._resolve_includes(config, Path(main_file).parent)

        # Resolve templates
        config = self._resolve_templates(config)

        return config

    def _resolve_includes(self, config: dict, base_dir: Path) -> dict:
        """Resolve !include directives"""

        if isinstance(config, dict):
            result = {}
            for key, value in config.items():
                if isinstance(value, str) and value.startswith("!include"):
                    # Load included file
                    include_path = base_dir / value.replace("!include ", "")
                    with open(include_path) as f:
                        result[key] = yaml.safe_load(f)
                else:
                    result[key] = self._resolve_includes(value, base_dir)
            return result
        elif isinstance(config, list):
            return [self._resolve_includes(item, base_dir) for item in config]
        return config
```

```yaml
# config/transform/main.yml - Modular
taxon:
  !include taxon/general.yml
  !include taxon/distributions.yml
  !include taxon/phenology.yml

plot:
  !include plot/config.yml

shape:
  !include shape/config.yml
```

**Effort**: 1 day
**Impact**: Maintainability ++

---

### 3.2 Massive Duplication in Configs

**Problem**
```yaml
# Same structure repeated 50+ times
- plugin: radial_gauge
  params:
    style_mode: "contextual"
    show_axis: false
    # ... 10 identical lines
```

**Solution**: See Templates section (already detailed in previous docs)

**Effort**: 2 days
**Impact**: -60% config lines

---

### 3.3 No Tests for Plugins

**Problem**
```python
# Tests difficult due to coupling
# How to test a plugin that directly accesses the DB?
```

**Solution**
```python
# tests/plugins/test_plugin_base.py
import pytest
from unittest.mock import Mock, MagicMock
from typing import Any

class PluginTestCase:
    """Base class for plugin tests"""

    @pytest.fixture
    def mock_data_provider(self):
        """Mock data provider"""
        provider = Mock()
        provider.get_table_data.return_value = pd.DataFrame({
            'id': [1, 2, 3],
            'value': [10, 20, 30]
        })
        return provider

    @pytest.fixture
    def plugin_factory(self, mock_data_provider):
        """Factory to create testable plugins"""
        def factory(plugin_class, **params):
            plugin = plugin_class(mock_data_provider)
            # Inject validated params
            if hasattr(plugin, 'param_schema'):
                validated = plugin.param_schema(**params)
            else:
                validated = params
            return plugin, validated
        return factory

# tests/plugins/transformers/test_field_aggregator.py
class TestFieldAggregator(PluginTestCase):
    def test_aggregation(self, plugin_factory):
        """Test field aggregation"""

        # Arrange
        plugin, params = plugin_factory(
            FieldAggregator,
            fields=[{
                'source': 'test_table',
                'field': 'value',
                'target': 'aggregated',
                'transformation': 'sum'
            }]
        )

        # Act
        result = plugin.transform(pd.DataFrame(), params)

        # Assert
        assert 'aggregated' in result
        assert result['aggregated'] == 60  # sum(10, 20, 30)
```

**Effort**: 3 days
**Impact**: Quality, regression prevention

---

## 4. ARCHITECTURE ISSUES 🟡

### 4.1 Insufficient Logging

**Problem**
```python
# src/niamoto/core/plugins/plugin_loader.py:165
except Exception:
    pass  # Silent error!
```

**Solution**
```python
# src/niamoto/common/logging.py
import logging
from functools import wraps
import traceback

def setup_logging():
    """Configure structured logging"""

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('niamoto.log'),
            logging.StreamHandler()
        ]
    )

    # Structured logging for production
    if os.getenv('ENV') == 'production':
        import structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
        )

def log_exceptions(logger):
    """Decorator to log exceptions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Exception in {func.__name__}",
                    exc_info=True,
                    extra={
                        'function': func.__name__,
                        'args': str(args)[:200],
                        'kwargs': str(kwargs)[:200],
                        'traceback': traceback.format_exc()
                    }
                )
                raise
        return wrapper
    return decorator
```

**Effort**: 1 day
**Impact**: Debugging, monitoring

---

### 4.2 No Health Check Mechanism

**Problem**
```python
# How to know if a plugin works?
# How to detect broken plugins?
```

**Solution**
```python
# src/niamoto/core/health.py
from typing import Dict, List
from enum import Enum

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthChecker:
    """Check system health"""

    def check_all(self) -> Dict[str, HealthStatus]:
        """Check all components"""

        results = {
            'database': self._check_database(),
            'plugins': self._check_plugins(),
            'config': self._check_config(),
            'cache': self._check_cache()
        }

        return results

    def _check_plugins(self) -> HealthStatus:
        """Check that plugins are loaded"""

        registry = PluginRegistry()
        required_plugins = [
            'field_aggregator',
            'binned_distribution',
            'bar_plot'
        ]

        for plugin_name in required_plugins:
            if not registry.has(plugin_name):
                logger.error(f"Missing required plugin: {plugin_name}")
                return HealthStatus.UNHEALTHY

        # Basic test of each plugin
        for plugin_name in registry.list():
            try:
                plugin = registry.get(plugin_name)
                # Check plugin has required methods
                if not hasattr(plugin, 'transform'):
                    return HealthStatus.DEGRADED
            except Exception as e:
                logger.error(f"Plugin {plugin_name} health check failed: {e}")
                return HealthStatus.UNHEALTHY

        return HealthStatus.HEALTHY

# src/niamoto/cli/commands.py
@click.command()
def health():
    """Check system health"""
    checker = HealthChecker()
    results = checker.check_all()

    for component, status in results.items():
        if status == HealthStatus.HEALTHY:
            click.echo(f"✅ {component}: {status.value}")
        elif status == HealthStatus.DEGRADED:
            click.echo(f"⚠️  {component}: {status.value}")
        else:
            click.echo(f"❌ {component}: {status.value}")

    # Exit code based on overall health
    if all(s == HealthStatus.HEALTHY for s in results.values()):
        sys.exit(0)
    else:
        sys.exit(1)
```

**Effort**: 1 day
**Impact**: Monitoring, ops

---

### 4.3 No Plugin Versioning

**Solution**: Manifest System (see external analysis)
```python
# src/niamoto/core/plugins/manifest.py
from pydantic import BaseModel
from typing import List, Optional

class PluginManifest(BaseModel):
    """Manifest for a plugin"""

    name: str
    version: str
    type: PluginType
    author: Optional[str]
    description: str

    # Compatibility
    niamoto_version: str  # ">=2.0.0"

    # Dependencies
    dependencies: List[str] = []

    # Inputs/Outputs
    inputs: List[Dict[str, str]]
    outputs: List[Dict[str, str]]

    # Parameters
    param_schema: Optional[str]  # Schema reference

# plugins/my_plugin/__manifest__.py
MANIFEST = PluginManifest(
    name="dbh_distribution",
    version="1.2.0",
    type=PluginType.TRANSFORMER,
    description="Calculate DBH distribution with bins",
    niamoto_version=">=2.0.0",
    dependencies=["numpy>=1.20", "pandas>=1.3"],
    inputs=[
        {"type": "DataFrame", "schema": "occurrences_v2"}
    ],
    outputs=[
        {"type": "Dict", "schema": "distribution"}
    ]
)
```

**Effort**: 2 days
**Impact**: Governance, compatibility

---

## 5. DEVELOPER EXPERIENCE ISSUES 🟢

### 5.1 Missing Auto-Generated Documentation

**Solution**
```python
# tools/generate_plugin_docs.py
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType

def generate_plugin_docs():
    """Generate Markdown doc for all plugins"""

    registry = PluginRegistry()
    docs = []

    for plugin_name in registry.list():
        plugin = registry.get(plugin_name)

        doc = f"""
## {plugin_name}

**Type**: {plugin.type.value}
**Module**: {plugin.__module__}

### Description
{plugin.__doc__ or 'No description'}

### Parameters
"""
        if hasattr(plugin, 'param_schema'):
            schema = plugin.param_schema.schema()
            for field, config in schema['properties'].items():
                doc += f"- **{field}**: {config.get('description', 'No description')}\n"
                doc += f"  - Type: {config.get('type', 'unknown')}\n"
                if 'default' in config:
                    doc += f"  - Default: {config['default']}\n"

        docs.append(doc)

    with open('docs/plugins.md', 'w') as f:
        f.write('\n'.join(docs))

if __name__ == "__main__":
    generate_plugin_docs()
```

**Effort**: 4 hours
**Impact**: Documentation

---

## 6. Prioritized Action Plan

### Phase 1: Critical Fixes (1 week)
| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Externalize secrets | 🔴 | 4h | Security |
| Centralized validation | 🔴 | 1d | Stability |
| Improved logging | 🟠 | 1d | Debugging |
| Basic cache | 🟠 | 1d | Perf x5 |

### Phase 2: Architecture (2 weeks)
| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Dependency injection | 🔴 | 2d | Testability |
| YAML templates | 🟠 | 2d | -60% config |
| Plugin tests | 🟠 | 3d | Quality |
| Health checks | 🟡 | 1d | Monitoring |

### Phase 3: Performance (1 week)
| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Parallelization | 🟠 | 2d | Perf x4-8 |
| Advanced cache | 🟠 | 1d | Perf x10 |
| Data provider | 🟡 | 2d | Architecture |

### Phase 4: Governance (2 weeks)
| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Plugin manifest | 🟡 | 2d | Versioning |
| Modular config | 🟡 | 1d | Maintainability |
| Auto-generated docs | 🟢 | 4h | DX |
| UI config builder | 🟢 | 1 wk | UX |

## 7. Quick Start: The First 3 Actions

### Action 1: Secure Secrets (Today)
```bash
# 1. Create .env
echo "ENDEMIA_API_KEY=${CURRENT_KEY}" > .env

# 2. Modify Config class
# Add code from section 1.1

# 3. Update YAMLs
# Replace values with ${VAR_NAME}

# 4. Test
niamoto transform --config config/transform.yml
```

### Action 2: Add Validation (Tomorrow)
```python
# 1. Modify TransformerService
# Add code from section 1.2

# 2. Verify all plugins have param_schema
# If not, add progressively

# 3. Test with invalid config
# Should raise clear error
```

### Action 3: Implement Cache (This Week)
```python
# 1. Add DataCache
# Code from section 2.1

# 2. Modify TransformerService to use cache

# 3. Measure gains
# time niamoto transform --config config/transform.yml
# Should be 5-10x faster on 2nd run
```

## 8. Success Metrics

### Before Corrections
- 🔴 Plaintext secrets
- 🔴 Frequent crashes (validation)
- 🔴 Performance: 30 min for complete pipeline
- 🔴 Config: 2500+ YAML lines
- 🔴 Tests: 0% plugin coverage

### After Corrections (Goal)
- ✅ Externalized secrets
- ✅ Validation = 0 crashes
- ✅ Performance: 3-5 min (x6-10)
- ✅ Config: 800 lines (-70%)
- ✅ Tests: 80% coverage

## 9. Resources and Tools

### Recommended Tools
- **Monitoring**: Prometheus + Grafana for metrics
- **Logging**: ELK Stack or Loki for centralization
- **Cache**: Redis for distributed cache (future)
- **CI/CD**: GitHub Actions for automated tests

### Reference Documentation
- [The Twelve-Factor App](https://12factor.net/) - Best practices
- [Plugin Architecture Patterns](https://www.martinfowler.com/articles/injection.html) - Dependency injection
- [Python Testing Best Practices](https://realpython.com/pytest-python-testing/) - Testing with pytest

## Conclusion

**80% of benefits will come from 20% of corrections**. Focus on:

1. **Security** (secrets)
2. **Stability** (validation)
3. **Performance** (cache)
4. **Maintainability** (templates)

Critical fixes can be done in **1-2 weeks** for immediate gain. The rest can be spread over 2-3 months depending on resources.
