# Plan de Corrections Complet pour Niamoto

## Résumé Exécutif

Ce document compile **tous les problèmes identifiés** dans le système Niamoto et propose des corrections concrètes, priorisées et estimées. Les problèmes sont classés par criticité : 🔴 Critique, 🟠 Important, 🟡 Modéré, 🟢 Amélioration.

**Impact total estimé** : 3-6 mois pour tout corriger, mais les corrections critiques peuvent être faites en 2-3 semaines.

---

## 1. PROBLÈMES CRITIQUES 🔴 (À corriger immédiatement)

### 1.1 Secrets en Clair dans les YAML

**Problème**
```yaml
# test-instance/niamoto-og/config/import.yml:22
auth_params:
  key: "1e106508-9a86-4242-9012-d6cafdea3374"  # API key en clair !
```

**Solution**
```python
# src/niamoto/common/config.py - Ajouter le support des variables d'env
import os
from string import Template

class Config:
    def _load_yaml_with_env(self, path: str) -> dict:
        """Charge YAML avec substitution de variables d'environnement"""
        with open(path) as f:
            content = f.read()

        # Remplace ${VAR_NAME} par la valeur d'environnement
        template = Template(content)
        resolved = template.safe_substitute(os.environ)

        return yaml.safe_load(resolved)
```

```yaml
# config/import.yml - Version sécurisée
auth_params:
  key: ${ENDEMIA_API_KEY}  # Variable d'environnement
```

```bash
# .env.example
ENDEMIA_API_KEY=your-key-here
DATABASE_URL=postgresql://...
```

**Effort** : 4 heures
**Impact** : Sécurité critique

---

### 1.2 Validation Inconsistante des Paramètres

**Problème**
```python
# src/niamoto/core/services/transformer.py:190
# Passe un dict brut sans validation !
result = plugin.transform(data, config['params'])  # Dangereux
```

**Solution**
```python
# src/niamoto/core/services/transformer.py - Validation centralisée
from pydantic import ValidationError

class TransformerService:
    def execute_widget(self, widget_config: dict, data: Any) -> Any:
        """Exécute un widget avec validation centralisée"""

        plugin_name = widget_config.get('plugin')
        plugin = self.registry.get(plugin_name)

        # NOUVEAU : Validation AVANT l'appel
        try:
            # Utilise le param_schema du plugin pour valider
            if hasattr(plugin, 'param_schema'):
                validated_params = plugin.param_schema(**widget_config.get('params', {}))
            else:
                # Fallback pour anciens plugins
                validated_params = widget_config.get('params', {})
                logger.warning(f"Plugin {plugin_name} has no param_schema")
        except ValidationError as e:
            raise ValueError(f"Invalid params for {plugin_name}: {e}")

        # Appel avec params validés (objet Pydantic, pas dict)
        return plugin.transform(data, validated_params)
```

**Effort** : 1 jour
**Impact** : Stabilité critique

---

### 1.3 Couplage Fort des Plugins

**Problème**
```python
# src/niamoto/core/plugins/transformers/aggregation/field_aggregator.py:101
class FieldAggregator(TransformerPlugin):
    def __init__(self, db):
        super().__init__(db)
        # PROBLÈME : Accès direct à la config globale !
        self.config = Config()
        self.imports_config = self.config.get_imports_config
```

**Solution**
```python
# src/niamoto/core/plugins/base.py - Injection de dépendances
from typing import Protocol

class DataProvider(Protocol):
    """Interface pour accès aux données"""
    def get_table_data(self, table: str, filters: dict = None) -> pd.DataFrame:
        ...

    def get_config_value(self, key: str) -> Any:
        ...

class TransformerPlugin(Plugin, ABC):
    """Plugin avec injection de dépendances"""

    def __init__(self, data_provider: DataProvider):
        self.data_provider = data_provider  # Interface, pas implémentation

    @abstractmethod
    def transform(self, data: Any, params: BaseModel) -> Any:
        """Transform avec params validés"""
        pass

# src/niamoto/core/services/transformer.py
class TransformerService:
    def __init__(self):
        # Crée le provider centralisé
        self.data_provider = DataProviderImpl(self.db, self.config)

    def create_plugin(self, plugin_class):
        """Injecte les dépendances"""
        return plugin_class(self.data_provider)
```

**Effort** : 2 jours
**Impact** : Architecture, testabilité

---

## 2. PROBLÈMES DE PERFORMANCE 🟠

### 2.1 Rechargement Répétitif des Données

**Problème**
```python
# Chaque plugin recharge les mêmes données
plugin1: SELECT * FROM occurrences WHERE taxon_id = 123
plugin2: SELECT * FROM occurrences WHERE taxon_id = 123  # Même requête !
plugin3: SELECT * FROM occurrences WHERE taxon_id = 123  # Encore !
```

**Solution**
```python
# src/niamoto/core/services/data_cache.py
from functools import lru_cache
from typing import Optional
import hashlib

class DataCache:
    """Cache centralisé pour les données"""

    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self._cache = {}

    def get_or_compute(self, key: str, compute_fn):
        """Get from cache or compute"""
        if key in self._cache:
            logger.debug(f"Cache hit: {key}")
            return self._cache[key]

        logger.debug(f"Cache miss: {key}, computing...")
        result = compute_fn()
        self._cache[key] = result
        return result

    @lru_cache(maxsize=128)
    def get_occurrences(self, taxon_id: int) -> pd.DataFrame:
        """Cache par taxon"""
        return pd.read_sql(
            f"SELECT * FROM occurrences WHERE taxon_id = {taxon_id}",
            self.engine
        )

# Utilisation dans le service
class TransformerService:
    def __init__(self):
        self.cache = DataCache()

    def process_taxon(self, taxon_id: int):
        # Chargé une seule fois, partagé entre plugins
        occurrences = self.cache.get_occurrences(taxon_id)

        for widget in self.widgets:
            plugin.transform(occurrences, params)  # Même data
```

**Effort** : 1 jour
**Impact** : Performance x5-10

---

### 2.2 Pipeline Séquentiel (Pas de Parallélisation)

**Problème**
```python
# Actuel : Tout est séquentiel
for taxon in taxons:        # 1000 taxons
    for widget in widgets:   # 20 widgets
        process()            # = 20,000 opérations séquentielles !
```

**Solution**
```python
# src/niamoto/core/services/parallel_transformer.py
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import List
import multiprocessing as mp

class ParallelTransformerService:
    """Service avec parallélisation"""

    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or mp.cpu_count()

    def process_taxons_parallel(self, taxon_ids: List[int]):
        """Traite les taxons en parallèle"""

        # Utilise ProcessPool pour calculs lourds
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            for taxon_id in taxon_ids:
                future = executor.submit(self.process_single_taxon, taxon_id)
                futures.append(future)

            # Collecte les résultats
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except TimeoutError:
                    logger.error(f"Timeout processing taxon")

        return results

    def process_widgets_parallel(self, taxon_id: int, widgets: List[dict]):
        """Traite les widgets indépendants en parallèle"""

        # Identifie les widgets indépendants
        independent = self.identify_independent_widgets(widgets)
        dependent = [w for w in widgets if w not in independent]

        # Parallélise les indépendants
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(self.process_widget, taxon_id, w): w
                for w in independent
            }

            results = {}
            for future in as_completed(futures):
                widget = futures[future]
                results[widget['name']] = future.result()

        # Puis les dépendants en séquence
        for widget in dependent:
            results[widget['name']] = self.process_widget(taxon_id, widget, results)

        return results
```

**Effort** : 2 jours
**Impact** : Performance x4-8 sur multi-core

---

### 2.3 Absence de Cache pour Transformations Coûteuses

**Problème**
```python
# Recalcul constant des mêmes transformations
process_taxon(123)  # 10 secondes
process_taxon(123)  # 10 secondes encore ! (même résultat)
```

**Solution**
```python
# src/niamoto/core/cache/transform_cache.py
import pickle
import hashlib
from pathlib import Path
from typing import Optional

class TransformCache:
    """Cache persistant pour transformations"""

    def __init__(self, cache_dir: str = ".niamoto_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def get_cache_key(self, entity_id: str, widget: str, params: dict) -> str:
        """Génère une clé de cache unique"""
        # Hash des params pour détecter les changements
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()

        return f"{entity_id}_{widget}_{params_hash}"

    def get(self, entity_id: str, widget: str, params: dict) -> Optional[Any]:
        """Récupère du cache si existe"""
        key = self.get_cache_key(entity_id, widget, params)
        cache_file = self.cache_dir / f"{key}.pkl"

        if cache_file.exists():
            # Vérifie la fraîcheur (24h)
            age = time.time() - cache_file.stat().st_mtime
            if age < 86400:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)

        return None

    def set(self, entity_id: str, widget: str, params: dict, data: Any):
        """Sauvegarde en cache"""
        key = self.get_cache_key(entity_id, widget, params)
        cache_file = self.cache_dir / f"{key}.pkl"

        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)

    def invalidate(self, entity_id: str = None):
        """Invalide le cache"""
        if entity_id:
            # Invalide seulement pour cette entité
            for file in self.cache_dir.glob(f"{entity_id}_*.pkl"):
                file.unlink()
        else:
            # Invalide tout
            for file in self.cache_dir.glob("*.pkl"):
                file.unlink()
```

**Effort** : 1 jour
**Impact** : Performance x10-100 sur re-runs

---

## 3. PROBLÈMES DE MAINTENABILITÉ 🟡

### 3.1 Configuration YAML Monolithique

**Problème**
```yaml
# transform.yml : 900+ lignes !
# export.yml : 1600+ lignes !
```

**Solution**
```python
# src/niamoto/config/modular_loader.py
class ModularConfigLoader:
    """Charge des configs modulaires avec includes"""

    def load_config(self, main_file: str) -> dict:
        """Charge une config avec support des includes"""

        with open(main_file) as f:
            config = yaml.safe_load(f)

        # Résout les includes
        config = self._resolve_includes(config, Path(main_file).parent)

        # Résout les templates
        config = self._resolve_templates(config)

        return config

    def _resolve_includes(self, config: dict, base_dir: Path) -> dict:
        """Résout les !include"""

        if isinstance(config, dict):
            result = {}
            for key, value in config.items():
                if isinstance(value, str) and value.startswith("!include"):
                    # Charge le fichier inclus
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
# config/transform/main.yml - Modulaire
taxon:
  !include taxon/general.yml
  !include taxon/distributions.yml
  !include taxon/phenology.yml

plot:
  !include plot/config.yml

shape:
  !include shape/config.yml
```

**Effort** : 1 jour
**Impact** : Maintenabilité ++

---

### 3.2 Duplication Massive dans les Configs

**Problème**
```yaml
# Même structure répétée 50+ fois
- plugin: radial_gauge
  params:
    style_mode: "contextual"
    show_axis: false
    # ... 10 lignes identiques
```

**Solution** : Voir section Templates (déjà détaillée dans docs précédents)

**Effort** : 2 jours
**Impact** : -60% lignes de config

---

### 3.3 Pas de Tests pour les Plugins

**Problème**
```python
# Tests difficiles à cause du couplage
# Comment tester un plugin qui accède directement à la DB ?
```

**Solution**
```python
# tests/plugins/test_plugin_base.py
import pytest
from unittest.mock import Mock, MagicMock
from typing import Any

class PluginTestCase:
    """Classe de base pour tests de plugins"""

    @pytest.fixture
    def mock_data_provider(self):
        """Mock du data provider"""
        provider = Mock()
        provider.get_table_data.return_value = pd.DataFrame({
            'id': [1, 2, 3],
            'value': [10, 20, 30]
        })
        return provider

    @pytest.fixture
    def plugin_factory(self, mock_data_provider):
        """Factory pour créer des plugins testables"""
        def factory(plugin_class, **params):
            plugin = plugin_class(mock_data_provider)
            # Injecte les params validés
            if hasattr(plugin, 'param_schema'):
                validated = plugin.param_schema(**params)
            else:
                validated = params
            return plugin, validated
        return factory

# tests/plugins/transformers/test_field_aggregator.py
class TestFieldAggregator(PluginTestCase):
    def test_aggregation(self, plugin_factory):
        """Test l'agrégation de champs"""

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

**Effort** : 3 jours
**Impact** : Qualité, régression prevention

---

## 4. PROBLÈMES D'ARCHITECTURE 🟡

### 4.1 Logging Insuffisant

**Problème**
```python
# src/niamoto/core/plugins/plugin_loader.py:165
except Exception:
    pass  # Erreur silencieuse !
```

**Solution**
```python
# src/niamoto/common/logging.py
import logging
from functools import wraps
import traceback

def setup_logging():
    """Configure un logging structuré"""

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('niamoto.log'),
            logging.StreamHandler()
        ]
    )

    # Logging structuré pour production
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
    """Décorateur pour logger les exceptions"""
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

**Effort** : 1 jour
**Impact** : Debugging, monitoring

---

### 4.2 Pas de Mécanisme de Health Check

**Problème**
```python
# Comment savoir si un plugin fonctionne ?
# Comment détecter les plugins cassés ?
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
    """Vérifie la santé du système"""

    def check_all(self) -> Dict[str, HealthStatus]:
        """Vérifie tous les composants"""

        results = {
            'database': self._check_database(),
            'plugins': self._check_plugins(),
            'config': self._check_config(),
            'cache': self._check_cache()
        }

        return results

    def _check_plugins(self) -> HealthStatus:
        """Vérifie que les plugins sont chargés"""

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

        # Test basique de chaque plugin
        for plugin_name in registry.list():
            try:
                plugin = registry.get(plugin_name)
                # Vérifie que le plugin a les méthodes requises
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

**Effort** : 1 jour
**Impact** : Monitoring, ops

---

### 4.3 Pas de Versioning des Plugins

**Solution** : Manifest System (voir analyse externe)
```python
# src/niamoto/core/plugins/manifest.py
from pydantic import BaseModel
from typing import List, Optional

class PluginManifest(BaseModel):
    """Manifest pour un plugin"""

    name: str
    version: str
    type: PluginType
    author: Optional[str]
    description: str

    # Compatibilité
    niamoto_version: str  # ">=2.0.0"

    # Dépendances
    dependencies: List[str] = []

    # Entrées/Sorties
    inputs: List[Dict[str, str]]
    outputs: List[Dict[str, str]]

    # Paramètres
    param_schema: Optional[str]  # Référence au schema

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

**Effort** : 2 jours
**Impact** : Gouvernance, compatibilité

---

## 5. PROBLÈMES D'EXPÉRIENCE DÉVELOPPEUR 🟢

### 5.1 Documentation Auto-générée Manquante

**Solution**
```python
# tools/generate_plugin_docs.py
from niamoto.core.plugins.registry import PluginRegistry
from niamoto.core.plugins.base import PluginType

def generate_plugin_docs():
    """Génère la doc Markdown de tous les plugins"""

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

**Effort** : 4 heures
**Impact** : Documentation

---

## 6. Plan d'Action Priorisé

### Phase 1 : Corrections Critiques (1 semaine)
| Tâche | Priorité | Effort | Impact |
|-------|----------|--------|--------|
| Externaliser les secrets | 🔴 | 4h | Sécurité |
| Validation centralisée | 🔴 | 1j | Stabilité |
| Logging amélioré | 🟠 | 1j | Debugging |
| Cache basique | 🟠 | 1j | Perf x5 |

### Phase 2 : Architecture (2 semaines)
| Tâche | Priorité | Effort | Impact |
|-------|----------|--------|--------|
| Injection dépendances | 🔴 | 2j | Testabilité |
| Templates YAML | 🟠 | 2j | -60% config |
| Tests plugins | 🟠 | 3j | Qualité |
| Health checks | 🟡 | 1j | Monitoring |

### Phase 3 : Performance (1 semaine)
| Tâche | Priorité | Effort | Impact |
|-------|----------|--------|--------|
| Parallélisation | 🟠 | 2j | Perf x4-8 |
| Cache avancé | 🟠 | 1j | Perf x10 |
| Data provider | 🟡 | 2j | Architecture |

### Phase 4 : Gouvernance (2 semaines)
| Tâche | Priorité | Effort | Impact |
|-------|----------|--------|--------|
| Plugin manifest | 🟡 | 2j | Versioning |
| Config modulaire | 🟡 | 1j | Maintenabilité |
| Doc auto-générée | 🟢 | 4h | DX |
| UI config builder | 🟢 | 1 sem | UX |

## 7. Quick Start : Les 3 Premières Actions

### Action 1 : Sécuriser les Secrets (Aujourd'hui)
```bash
# 1. Créer .env
echo "ENDEMIA_API_KEY=${CURRENT_KEY}" > .env

# 2. Modifier Config class
# Ajouter le code de la section 1.1

# 3. Mettre à jour les YAML
# Remplacer les valeurs par ${VAR_NAME}

# 4. Tester
niamoto transform --config config/transform.yml
```

### Action 2 : Ajouter la Validation (Demain)
```python
# 1. Modifier TransformerService
# Ajouter le code de la section 1.2

# 2. Vérifier que tous les plugins ont param_schema
# Si non, ajouter progressivement

# 3. Tester avec config invalide
# Doit lever une erreur claire
```

### Action 3 : Implémenter le Cache (Cette Semaine)
```python
# 1. Ajouter DataCache
# Code de la section 2.1

# 2. Modifier TransformerService pour utiliser le cache

# 3. Mesurer les gains
# time niamoto transform --config config/transform.yml
# Devrait être 5-10x plus rapide au 2e run
```

## 8. Métriques de Succès

### Avant Corrections
- 🔴 Secrets en clair
- 🔴 Crashes fréquents (validation)
- 🔴 Performance : 30 min pour pipeline complet
- 🔴 Config : 2500+ lignes YAML
- 🔴 Tests : 0% coverage plugins

### Après Corrections (Objectif)
- ✅ Secrets externalisés
- ✅ Validation = 0 crashes
- ✅ Performance : 3-5 min (x6-10)
- ✅ Config : 800 lignes (-70%)
- ✅ Tests : 80% coverage

## 9. Ressources et Outils

### Outils Recommandés
- **Monitoring** : Prometheus + Grafana pour métriques
- **Logging** : ELK Stack ou Loki pour centralisation
- **Cache** : Redis pour cache distribué (futur)
- **CI/CD** : GitHub Actions pour tests automatiques

### Documentation de Référence
- [The Twelve-Factor App](https://12factor.net/) - Bonnes pratiques
- [Plugin Architecture Patterns](https://www.martinfowler.com/articles/injection.html) - Injection de dépendances
- [Python Testing Best Practices](https://realpython.com/pytest-python-testing/) - Tests avec pytest

## Conclusion

**80% des bénéfices viendront de 20% des corrections**. Focalisez sur :

1. **Sécurité** (secrets)
2. **Stabilité** (validation)
3. **Performance** (cache)
4. **Maintenabilité** (templates)

Les corrections critiques peuvent être faites en **1-2 semaines** pour un gain immédiat. Le reste peut être étalé sur 2-3 mois selon les ressources.
