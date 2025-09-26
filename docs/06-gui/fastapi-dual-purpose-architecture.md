# Architecture FastAPI Double Usage pour Niamoto

## Vision

Utiliser FastAPI non seulement pour l'interface de configuration, mais aussi comme serveur de données dynamique optionnel, réutilisant les données transformées et l'API statique générée.

## Architecture Proposée

### 1. Mode de Fonctionnement Dual

```python
# niamoto/api/server.py
@cli.command()
@click.option('--mode', type=click.Choice(['config', 'data', 'both']), default='config')
@click.option('--port', default=8080)
@click.option('--static-fallback/--no-static-fallback', default=True)
def serve(mode, port, static_fallback):
    """
    Lance le serveur FastAPI

    Modes:
    - config: Interface de configuration uniquement
    - data: API de données uniquement
    - both: Configuration + API de données
    """
    app = create_app(mode, static_fallback)
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### 2. Architecture FastAPI Modulaire

```python
# niamoto/api/app.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

def create_app(mode='both', static_fallback=True):
    app = FastAPI(
        title="Niamoto API",
        description="Configuration et données écologiques"
    )

    # Toujours monter l'interface statique React
    app.mount("/ui", StaticFiles(directory="static"), name="ui")

    if mode in ['config', 'both']:
        # Routes pour la configuration
        from .routers import config
        app.include_router(config.router, prefix="/api/config")

    if mode in ['data', 'both']:
        # Routes pour les données
        from .routers import data
        app.include_router(
            data.create_router(static_fallback),
            prefix="/api/data"
        )

    return app
```

### 3. API de Configuration (Mode Config)

```python
# niamoto/api/routers/config.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()

class ConfigUpdate(BaseModel):
    section: str  # 'import', 'transform', 'export'
    config: Dict[str, Any]

@router.get("/projects")
async def list_projects():
    """Liste les projets Niamoto disponibles"""
    return {"projects": find_niamoto_projects()}

@router.get("/projects/{project_id}/config")
async def get_config(project_id: str):
    """Récupère la configuration complète d'un projet"""
    return {
        "import": load_yaml(f"{project_id}/config/import.yml"),
        "transform": load_yaml(f"{project_id}/config/transform.yml"),
        "export": load_yaml(f"{project_id}/config/export.yml")
    }

@router.post("/projects/{project_id}/validate")
async def validate_config(project_id: str, update: ConfigUpdate):
    """Valide une configuration sans l'appliquer"""
    try:
        validate_section(update.section, update.config)
        return {"valid": True, "message": "Configuration valide"}
    except ValidationError as e:
        return {"valid": False, "errors": e.errors()}

@router.post("/projects/{project_id}/preview")
async def preview_transformation(project_id: str, transform_id: str):
    """Preview d'une transformation spécifique"""
    # Utilise le moteur de transformation en mode dry-run
    result = preview_transform(project_id, transform_id, limit=100)
    return {"preview": result}
```

### 4. API de Données Dynamique (Mode Data)

```python
# niamoto/api/routers/data.py
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import json
from pathlib import Path

def create_router(static_fallback=True):
    router = APIRouter()

    @router.get("/taxons")
    async def list_taxons(
        limit: int = Query(100, le=1000),
        offset: int = 0,
        family: Optional[str] = None,
        endemic: Optional[bool] = None,
        search: Optional[str] = None
    ):
        """API dynamique avec filtrage et pagination"""

        # Option 1: Requête directe à la DB
        if has_database_connection():
            return query_taxons_db(limit, offset, family, endemic, search)

        # Option 2: Fallback sur l'API statique générée
        elif static_fallback:
            static_data = load_static_api("exports/api/all_taxons.json")
            filtered = filter_static_data(static_data, family, endemic, search)
            return paginate(filtered, limit, offset)

        raise HTTPException(status_code=503, detail="No data source available")

    @router.get("/taxons/{taxon_id}")
    async def get_taxon(taxon_id: int):
        """Détails d'un taxon avec données enrichies"""

        # Tente d'abord la DB pour données fraîches
        if has_database_connection():
            return get_taxon_db(taxon_id)

        # Sinon utilise l'API statique
        static_file = f"exports/api/taxon/{taxon_id}.json"
        if Path(static_file).exists():
            return json.loads(Path(static_file).read_text())

        raise HTTPException(status_code=404, detail="Taxon not found")

    @router.get("/taxons/{taxon_id}/occurrences")
    async def get_taxon_occurrences(
        taxon_id: int,
        bbox: Optional[str] = None,  # "minLon,minLat,maxLon,maxLat"
        limit: int = Query(1000, le=10000)
    ):
        """Occurrences d'un taxon avec filtrage spatial"""
        # Implémentation similaire avec options DB/static
        pass

    @router.post("/analysis/custom")
    async def custom_analysis(params: AnalysisParams):
        """
        Analyses dynamiques non pré-calculées
        Nécessite une connexion DB
        """
        if not has_database_connection():
            raise HTTPException(
                status_code=503,
                detail="Database required for custom analysis"
            )

        # Utilise les plugins de transformation Niamoto
        return run_custom_analysis(params)

    return router
```

### 5. Intégration avec l'Interface React

```typescript
// services/api.ts
class NiamotoAPI {
  private baseURL: string;
  private mode: 'static' | 'dynamic';

  constructor() {
    // Détecte si on a un serveur dynamique
    this.checkServerMode();
  }

  async checkServerMode() {
    try {
      const response = await fetch('/api/data/health');
      this.mode = response.ok ? 'dynamic' : 'static';
    } catch {
      this.mode = 'static';
    }
  }

  async getTaxons(params: TaxonQuery) {
    if (this.mode === 'dynamic') {
      // Utilise l'API dynamique avec tous les paramètres
      return fetch(`/api/data/taxons?${new URLSearchParams(params)}`);
    } else {
      // Charge le fichier statique et filtre côté client
      const data = await fetch('/api/all_taxons.json');
      return this.filterClientSide(data, params);
    }
  }
}
```

### 6. Avantages de cette Architecture

#### Pour le Mode Configuration
- Preview en temps réel des transformations
- Validation instantanée
- Suggestions basées sur les données
- Gestion multi-projets

#### Pour le Mode Data
- **Flexibilité** : Fonctionne avec ou sans DB
- **Performance** : Cache intelligent + fallback statique
- **Évolutivité** : Peut commencer statique, évoluer vers dynamique
- **Analyses custom** : Possibles quand DB disponible

### 7. Cas d'Usage

#### Développement Local
```bash
# Lance tout (config + data)
niamoto serve --mode both

# Interface sur http://localhost:8080/ui
# API sur http://localhost:8080/api/data
```

#### Production Statique
```bash
# Génère le site statique
niamoto export

# Sert juste les fichiers statiques
python -m http.server -d exports/web
```

#### Production Dynamique
```bash
# API dynamique avec cache Redis (si disponible)
niamoto serve --mode data --cache redis://localhost:6379

# Ou sans cache externe
niamoto serve --mode data
```

### 8. Configuration FastAPI

```python
# niamoto/api/config.py
from functools import lru_cache
from pydantic import BaseSettings

class APISettings(BaseSettings):
    # Mode de fonctionnement
    api_mode: str = "both"
    static_fallback: bool = True

    # Cache
    cache_backend: str = "memory"  # memory, redis, sqlite
    cache_ttl: int = 3600

    # Limites
    max_page_size: int = 1000
    max_export_size: int = 100000

    # CORS
    cors_origins: list = ["*"]

    # Performance
    workers: int = 1

    class Config:
        env_prefix = "NIAMOTO_API_"

@lru_cache()
def get_settings():
    return APISettings()
```

### 9. Endpoints Spéciaux pour l'Interface

```python
@router.get("/config/suggestions/columns")
async def suggest_columns(file_path: str):
    """
    Analyse un CSV uploadé et suggère les mappings
    Utilise le ML pour détecter les types de colonnes
    """
    columns = analyze_csv(file_path)
    return {
        "suggestions": {
            "taxonomy": detect_taxonomy_columns(columns),
            "geography": detect_geo_columns(columns),
            "measures": detect_measurement_columns(columns)
        }
    }

@router.post("/config/test-pipeline")
async def test_pipeline(config: PipelineConfig):
    """
    Exécute un mini-pipeline pour validation
    Limite à 100 enregistrements
    """
    result = run_test_pipeline(config, limit=100)
    return {
        "success": result.success,
        "sample_output": result.sample,
        "warnings": result.warnings,
        "estimated_time": result.estimated_full_time
    }
```

## Conclusion

Cette architecture permet à FastAPI de servir intelligemment les deux besoins :

1. **Configuration** : Interface moderne pour créer/éditer les pipelines
2. **Données** : API dynamique optionnelle qui peut :
   - Servir les données statiques générées
   - Offrir des capacités dynamiques si DB disponible
   - Basculer automatiquement entre les modes

Cela reste fidèle à la philosophie Niamoto : simple par défaut (statique), puissant si nécessaire (dynamique).
