# Architecture : Gestion Multi-Projets & Ressources Partagées - Niamoto Desktop

**Version :** 1.0
**Date :** 16 novembre 2024
**Auteurs :** Architecture Niamoto Desktop
**Status :** Spécification détaillée

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture système](#2-architecture-système)
3. [Modèles de données](#3-modèles-de-données)
4. [Interfaces & API](#4-interfaces--api)
5. [Flux de données](#5-flux-de-données)
6. [Composants UI détaillés](#6-composants-ui-détaillés)
7. [Résolution des ressources](#7-résolution-des-ressources)
8. [Cas d'usage](#8-cas-dusage)
9. [Sécurité & Performance](#9-sécurité--performance)
10. [Plan de tests](#10-plan-de-tests)

---

## 1. Vue d'ensemble

### 1.1 Contexte

**Situation actuelle :**
- Niamoto est une application CLI où les utilisateurs naviguent (`cd`) dans un répertoire projet
- Interface web lancée avec `niamoto gui` pour le répertoire courant
- Application desktop Tauri récemment créée, mais sans gestion de projets multiples

**Problématique :**
- Applications desktop n'ont pas de concept de "répertoire courant"
- Utilisateurs ont plusieurs instances Niamoto indépendantes à gérer
- Plugins et templates sont dupliqués entre projets

### 1.2 Objectifs

**Fonctionnels :**
1. Permettre la gestion de multiples projets Niamoto dans une seule application
2. Partager plugins et templates entre projets avec système de priorités
3. UX intuitive inspirée des meilleures pratiques (Notion, VS Code)

**Non-fonctionnels :**
1. Performance : Switch projet < 5s
2. Facilité : Utilisable par des non-techniciens (botanistes)
3. Compatibilité : CLI et Desktop partagent les mêmes ressources (~/.niamoto/)
4. Évolutivité : Architecture permettant features futures (multi-window, cloud sync)

### 1.3 Principes d'architecture

**1. Résolution en cascade (Cascade Override Pattern)**
```
Project (local) → User (global) → System (built-in)
```
Les ressources locales au projet ont priorité sur les globales.

**2. Single Window avec État Partagé**
- Une seule fenêtre Tauri
- Changement de projet = redémarrage serveur FastAPI
- État UI réinitialisé à chaque switch

**3. Persistance légère**
- Configuration JSON simple dans `~/.niamoto/`
- Répertoire global partagé entre CLI et Desktop
- Pas de base de données complexe
- Migration facile entre machines

---

## 2. Architecture système

### 2.1 Vue d'ensemble des composants

```
┌─────────────────────────────────────────────────────────────┐
│                    Niamoto Desktop App                      │
│                     (Tauri Window)                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │           React UI (WebView)                       │    │
│  │  ┌──────────────┐  ┌──────────────────────────┐   │    │
│  │  │ TopBar       │  │ Main Content             │   │    │
│  │  │ - Switcher   │  │ - Dashboard              │   │    │
│  │  │ - Search     │  │ - Import/Transform       │   │    │
│  │  └──────────────┘  └──────────────────────────┘   │    │
│  │                                                    │    │
│  │  Tauri API Bindings (invoke commands)             │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↕                                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │           Rust Backend (Tauri Core)                │    │
│  │                                                    │    │
│  │  • AppConfig (config.rs)                          │    │
│  │  • ProjectManager (lib.rs)                        │    │
│  │  • Commands (commands.rs)                         │    │
│  │  • ServerState (process management)               │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↕                                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │       FastAPI Server (Python subprocess)           │    │
│  │                                                    │    │
│  │  Lancé avec: --instance /path/to/project          │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↕                                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │         Python Core (Niamoto)                      │    │
│  │                                                    │    │
│  │  • ResourcePaths (resource_paths.py)              │    │
│  │  • PluginLoader (plugin_loader.py)                │    │
│  │  • Database (project-specific .niamoto/)          │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

Filesystem:
├── ~/.niamoto/                  ← User-global config & resources (shared CLI/Desktop)
│   ├── desktop-config.json      ← Desktop app configuration
│   ├── plugins/                 ← Global plugins (available to all projects)
│   └── templates/               ← Global templates (available to all projects)
│
└── /path/to/project/            ← Project-specific
    ├── .niamoto/                ← Project data
    │   ├── db/
    │   ├── plugins/             ← Local plugins (override global)
    │   └── templates/
    ├── import.yml
    ├── transform.yml
    └── export.yml
```

### 2.2 Couches d'architecture

**Couche 1 : Présentation (React UI)**
- Responsabilité : Affichage, interactions utilisateur
- Technologie : React 19 + TypeScript + shadcn/ui
- Communication : Tauri IPC (invoke/emit)

**Couche 2 : Application (Rust Backend)**
- Responsabilité : Logique métier desktop, gestion état, process management
- Technologie : Rust + Tauri 2.x
- Communication : Tauri commands, events

**Couche 3 : Serveur (FastAPI)**
- Responsabilité : API REST, serveur de l'UI React buildée
- Technologie : Python 3.11+ FastAPI
- Communication : HTTP (localhost)

**Couche 4 : Core (Python Niamoto)**
- Responsabilité : Logique métier écologique, plugins, database
- Technologie : Python 3.11+
- Communication : Import direct

### 2.3 Stockage des données

**Configuration globale : `~/.niamoto/desktop-config.json`**
```json
{
  "version": "1.0",
  "lastOpenedProject": "/Users/.../test-instance/niamoto-nc",
  "openLastOnStartup": true,
  "recentProjects": [
    {
      "path": "/Users/.../test-instance/niamoto-nc",
      "name": "niamoto-nc",
      "lastOpened": "2024-11-16T10:30:00Z",
      "isPinned": false
    }
  ],
  "preferences": {
    "theme": "light",
    "maxRecentProjects": 10
  },
  "window": {
    "width": 1200,
    "height": 800,
    "x": 100,
    "y": 100
  }
}
```

**Ressources globales : `~/.niamoto/plugins/` et `templates/`**
- Structure identique aux plugins/templates locaux
- Découverts automatiquement par le système de résolution
- Partagés entre CLI et Desktop

**Données projet : `/path/to/project/.niamoto/`**
- Inchangé par rapport à la version CLI
- Database, cache, logs spécifiques au projet

### 2.4 Intégration CLI / Desktop

**Principe de partage `~/.niamoto/`**

Le répertoire `~/.niamoto/` est un espace global partagé entre :
- **CLI Niamoto** : ligne de commande traditionnelle
- **Desktop App** : application Tauri

**Structure du répertoire :**
```
~/.niamoto/
├── desktop-config.json    ← Configuration spécifique desktop (projets récents, préférences UI)
├── plugins/                ← Plugins globaux (CLI + Desktop)
│   ├── my_transformer.py
│   └── custom_stats.py
└── templates/              ← Templates globaux (CLI + Desktop)
    ├── default.yml
    └── nc_flora.yml
```

**Modifications CLI requises :**

Pour que la CLI bénéficie de la résolution en cascade, le module `plugin_loader.py` devra :
1. Utiliser `ResourcePaths.get_plugin_paths()` au lieu de chercher uniquement dans le projet courant
2. Supporter la même logique de priorité (Project > User > System)
3. Logger la provenance des plugins chargés (scope: project/user/system)

**Exemple d'usage CLI avec plugins globaux :**
```bash
# L'utilisateur installe un plugin global
mkdir -p ~/.niamoto/plugins
cp my_custom_transformer.py ~/.niamoto/plugins/

# Le plugin est maintenant disponible dans TOUS les projets
cd /path/to/project1
niamoto transform --plugin my_custom_transformer  # ✓ Fonctionne

cd /path/to/project2
niamoto transform --plugin my_custom_transformer  # ✓ Fonctionne aussi

# L'utilisateur peut override localement
cp my_custom_transformer_v2.py project2/.niamoto/plugins/my_custom_transformer.py
niamoto transform --plugin my_custom_transformer  # ✓ Utilise la version locale
```

**Avantages de cette approche :**
- ✅ Pas de duplication de plugins entre projets
- ✅ Plugins partagés entre CLI et Desktop
- ✅ Possibilité d'override local pour tests
- ✅ Cohérence de l'expérience utilisateur

### 2.5 Stratégie de compatibilité et surfaçage des conflits

**IMPORTANT : Les modifications doivent être implémentées simultanément dans CLI et Desktop pour éviter toute divergence.**

#### 2.5.1 Implémentation simultanée obligatoire

**Principe :** CLI et Desktop utilisent **exactement le même code** pour la résolution de ressources.

**Code partagé :**
- `src/niamoto/common/resource_paths.py` : Module unique utilisé par CLI et Desktop
- `src/niamoto/core/plugins/plugin_loader.py` : Modifié pour utiliser `ResourcePaths.get_plugin_paths()`
- Même logique, mêmes priorités, même ordre de résolution

**Garantie de cohérence :**
```python
# plugin_loader.py (utilisé par CLI ET Desktop)
from niamoto.common.resource_paths import ResourcePaths

def discover_plugins(project_path: Optional[Path] = None) -> Dict[str, PluginInfo]:
    """
    Découvre tous les plugins dans l'ordre de priorité.

    ⚠️  Cette fonction est utilisée par :
        - CLI : niamoto transform, niamoto export, etc.
        - Desktop : FastAPI server lancé par Tauri

    Les deux chemins DOIVENT charger les mêmes plugins dans le même ordre.
    """
    all_plugins = {}

    # Récupérer emplacements (MÊME CODE pour CLI et Desktop)
    locations = ResourcePaths.get_plugin_paths(project_path)

    # Parcourir en ordre inverse pour que haute priorité écrase basse
    for location in reversed(locations):
        if not location.exists:
            continue

        plugins = _scan_directory_for_plugins(location.path)

        for name, plugin_class in plugins.items():
            if name in all_plugins:
                # CONFLIT DÉTECTÉ : logger avec détails
                logger.warning(
                    f"Plugin '{name}' from {location.scope} ({location.path}) "
                    f"overrides previous from {all_plugins[name].scope}"
                )

            all_plugins[name] = PluginInfo(
                name=name,
                plugin_class=plugin_class,
                scope=location.scope,
                path=location.path,
                priority=location.priority
            )

    return all_plugins
```

#### 2.5.2 Surfaçage des conflits à l'utilisateur

**1. Logging détaillé (CLI et Desktop)**

```python
# Exemple de logs lors du chargement
INFO  | Scanning project plugins: /path/to/project/.niamoto/plugins
INFO  | Scanning user plugins: ~/.niamoto/plugins
INFO  | Scanning system plugins: <bundle>/niamoto/plugins
INFO  | Loaded plugin 'basic_stats' from project (priority: 100)
WARN  | Plugin 'custom_transformer' from user (priority: 50) overrides system version
INFO  | Total plugins loaded: 15 (3 project, 5 user, 7 system)
```

**2. UI Desktop : Indicateur visuel dans la liste des plugins**

```tsx
// Dans l'interface Transform/Export
<PluginCard plugin={plugin}>
  <Badge variant={plugin.scope === 'project' ? 'default' : 'secondary'}>
    {plugin.scope}
  </Badge>

  {plugin.isOverriding && (
    <Tooltip content={`Overrides ${plugin.scope === 'project' ? 'user/system' : 'system'} version`}>
      <AlertCircle className="text-orange-500" />
    </Tooltip>
  )}
</PluginCard>
```

**3. CLI : Commande dédiée pour inspecter les plugins**

```bash
# Nouvelle commande pour diagnostiquer les plugins chargés
$ niamoto plugins list --verbose

Plugins loaded for project: /path/to/project
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
basic_stats (v2.0)
  ├─ Scope: project
  ├─ Path: /path/to/project/.niamoto/plugins/basic_stats.py
  ├─ Priority: 100
  └─ ⚠️  Overrides: system version (v1.5)

custom_transformer (v1.0)
  ├─ Scope: user
  ├─ Path: ~/.niamoto/plugins/custom_transformer.py
  ├─ Priority: 50
  └─ ✓ No conflicts

occurrence_map (v3.1)
  ├─ Scope: system
  ├─ Path: <bundle>/niamoto/plugins/occurrence_map.py
  └─ Priority: 10
```

#### 2.5.3 Workflow de développement et test de plugins

**Développement d'un plugin global :**

```bash
# 1. Créer le plugin dans ~/.niamoto/plugins/
$ mkdir -p ~/.niamoto/plugins
$ nvim ~/.niamoto/plugins/my_new_plugin.py

# 2. Tester sur un projet sans polluer le projet
$ cd /path/to/test-project
$ niamoto plugins list  # Vérifier qu'il est chargé (scope: user)

# 3. Tester l'exécution
$ niamoto transform --plugin my_new_plugin --config test-config.yml

# 4. Itérer (modifier le fichier, relancer)
# Pas besoin de copier dans chaque projet !
```

**Test d'override local (avant de déployer en global) :**

```bash
# 1. Développer en local dans le projet
$ cp ~/.niamoto/plugins/my_plugin.py ./.niamoto/plugins/my_plugin_v2.py

# 2. Modifier la version locale
$ nvim ./.niamoto/plugins/my_plugin_v2.py

# 3. Tester
$ niamoto transform --plugin my_plugin_v2

# 4. Une fois validé, déployer en global
$ cp ./.niamoto/plugins/my_plugin_v2.py ~/.niamoto/plugins/my_plugin.py

# 5. Nettoyer la version locale (optionnel)
$ rm ./.niamoto/plugins/my_plugin_v2.py
```

**Hot reload (Desktop uniquement) :**

Pour le développement, un watcher de fichiers peut recharger les plugins :

```python
# Dans le serveur FastAPI (mode --reload)
from watchfiles import watch

async def watch_plugins():
    """Watch user and project plugin directories for changes"""
    watch_paths = [
        Path.home() / ".niamoto" / "plugins",
        current_project_path / ".niamoto" / "plugins"
    ]

    async for changes in watch(*watch_paths):
        logger.info(f"Plugin files changed: {changes}")
        # Recharger les plugins
        reload_plugin_registry()
```

**Tests automatisés :**

```python
# tests/test_resource_cascade.py
def test_cli_and_desktop_load_same_plugins(tmp_path):
    """
    Garantit que CLI et Desktop chargent les mêmes plugins.

    Cette test est CRITIQUE pour éviter les divergences de comportement.
    """
    # Setup: créer des plugins dans les 3 scopes
    project_path = tmp_path / "project"
    setup_test_plugins(project_path)

    # Charger via CLI
    cli_plugins = discover_plugins(project_path)

    # Charger via Desktop (même fonction!)
    desktop_plugins = discover_plugins(project_path)

    # Vérifier que les deux listes sont identiques
    assert cli_plugins == desktop_plugins

    # Vérifier l'ordre de priorité
    assert cli_plugins["basic_stats"].scope == "project"  # Override
    assert cli_plugins["custom_transformer"].scope == "user"
```

#### 2.5.4 Checklist de compatibilité

**Avant toute release, vérifier :**

- [ ] `ResourcePaths.get_plugin_paths()` utilisé par CLI et Desktop
- [ ] Logs de chargement identiques (CLI et Desktop)
- [ ] Tests automatisés passent (same plugins loaded)
- [ ] Commande `niamoto plugins list` fonctionne
- [ ] UI Desktop affiche les scopes et overrides
- [ ] Documentation utilisateur mise à jour
- [ ] Pas de code dupliqué (même logique partout)

**Indicateurs de divergence (à surveiller) :**

- ⚠️ Un plugin se charge en Desktop mais pas en CLI
- ⚠️ Ordre de priorité différent entre CLI et Desktop
- ⚠️ Logs différents pour le même projet
- ⚠️ Tests qui passent en CLI mais échouent en Desktop (ou inverse)

---

## 3. Modèles de données

### 3.1 Rust (Backend)

#### AppConfig
```rust
/// Configuration globale de l'application desktop
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AppConfig {
    /// Version du format de config
    pub version: String,

    /// Dernier projet ouvert (peut être None au premier lancement)
    pub last_opened_project: Option<PathBuf>,

    /// Ouvrir automatiquement le dernier projet au démarrage
    pub open_last_on_startup: bool,

    /// Liste des projets récents (max 10, ordre FIFO)
    pub recent_projects: Vec<ProjectInfo>,

    /// Préférences utilisateur
    pub preferences: UserPreferences,

    /// État de la fenêtre (position, taille)
    pub window: WindowState,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            version: "1.0".to_string(),
            last_opened_project: None,
            open_last_on_startup: true,
            recent_projects: Vec::new(),
            preferences: UserPreferences::default(),
            window: WindowState::default(),
        }
    }
}
```

#### ProjectInfo
```rust
/// Informations sur un projet Niamoto
#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub struct ProjectInfo {
    /// Chemin absolu vers le projet
    pub path: PathBuf,

    /// Nom du projet (déduit du nom du dossier)
    pub name: String,

    /// Date/heure dernière ouverture (ISO 8601)
    pub last_opened: String,

    /// Est-il épinglé (reste en haut de liste)
    pub is_pinned: bool,

    /// Métadonnées additionnelles (optionnel)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<ProjectMetadata>,
}

/// Métadonnées optionnelles d'un projet
#[derive(Debug, Serialize, Deserialize, Clone, PartialEq)]
pub struct ProjectMetadata {
    /// Description du projet
    pub description: Option<String>,

    /// Tags (ex: "production", "test", "archive")
    pub tags: Vec<String>,

    /// Couleur d'icône (hex color)
    pub color: Option<String>,

    /// Taille du projet (en bytes, mis à jour périodiquement)
    pub size_bytes: Option<u64>,

    /// Date de création
    pub created_at: Option<String>,
}
```

#### UserPreferences
```rust
/// Préférences utilisateur
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct UserPreferences {
    /// Thème de l'interface ("light", "dark", "auto")
    pub theme: String,

    /// Nombre max de projets récents
    pub max_recent_projects: usize,
}

impl Default for UserPreferences {
    fn default() -> Self {
        Self {
            theme: "light".to_string(),
            max_recent_projects: 10,
        }
    }
}
```

#### WindowState
```rust
/// État de la fenêtre Tauri
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct WindowState {
    pub width: u32,
    pub height: u32,
    pub x: i32,
    pub y: i32,
    pub is_maximized: bool,
}

impl Default for WindowState {
    fn default() -> Self {
        Self {
            width: 1200,
            height: 800,
            x: 100,
            y: 100,
            is_maximized: false,
        }
    }
}
```

### 3.2 TypeScript (Frontend)

#### ProjectInfo (miroir du Rust)
```typescript
export interface ProjectInfo {
  path: string
  name: string
  lastOpened: string  // ISO 8601
  isPinned: boolean
  metadata?: ProjectMetadata
}

export interface ProjectMetadata {
  description?: string
  tags: string[]
  color?: string
  sizeBytes?: number
  createdAt?: string
}
```

#### AppState (contexte React)
```typescript
export interface AppState {
  // Projet actuellement ouvert
  currentProject: ProjectInfo | null

  // Liste des projets récents
  recentProjects: ProjectInfo[]

  // État de chargement
  isLoading: boolean
  isSwitching: boolean

  // Erreurs
  error: string | null
}
```

### 3.3 Python (Core)

#### ResourcePath (nouveau module)
```python
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

@dataclass
class ResourceLocation:
    """Localisation d'une ressource (plugin/template)"""

    # Type de localisation ("project", "user", "system")
    scope: str

    # Chemin absolu vers la ressource
    path: Path

    # Priorité (plus élevé = prioritaire)
    priority: int

    # Est-ce que cette ressource existe réellement ?
    exists: bool

    def __post_init__(self):
        self.exists = self.path.exists()

class ResourcePaths:
    """Gestionnaire de chemins de ressources avec résolution en cascade"""

    SCOPE_PROJECT = "project"
    SCOPE_USER = "user"
    SCOPE_SYSTEM = "system"

    @staticmethod
    def get_plugin_paths(project_path: Optional[Path] = None) -> List[ResourceLocation]:
        """
        Retourne tous les chemins de recherche de plugins, ordonnés par priorité.

        Args:
            project_path: Chemin du projet actuel (optionnel)

        Returns:
            Liste de ResourceLocation, ordre décroissant de priorité
        """
        locations = []

        # 1. Project-local (priorité 100)
        if project_path:
            locations.append(ResourceLocation(
                scope=ResourcePaths.SCOPE_PROJECT,
                path=project_path / ".niamoto" / "plugins",
                priority=100
            ))

        # 2. User-global (priorité 50)
        user_dir = Path.home() / ".niamoto"
        locations.append(ResourceLocation(
            scope=ResourcePaths.SCOPE_USER,
            path=user_dir / "plugins",
            priority=50
        ))

        # 3. System built-in (priorité 10)
        from niamoto.common.bundle import get_resource_path, is_frozen
        if is_frozen():
            system_path = get_resource_path("niamoto/plugins")
        else:
            system_path = Path(__file__).parent.parent / "plugins"

        locations.append(ResourceLocation(
            scope=ResourcePaths.SCOPE_SYSTEM,
            path=system_path,
            priority=10
        ))

        return locations

    @staticmethod
    def get_template_paths(project_path: Optional[Path] = None) -> List[ResourceLocation]:
        """Même logique que plugins, pour les templates"""
        # Implémentation similaire
        pass
```

---

## 4. Interfaces & API

### 4.1 API Rust → Python (Process Launch)

#### Commande de lancement serveur
```rust
// Avant (actuel)
Command::new(&exe_path)
    .args(&["gui", "--port", "8080", "--no-browser"])
    .spawn()

// Après (avec projet)
Command::new(&exe_path)
    .args(&[
        "gui",
        "--instance", project_path.to_str().unwrap(),
        "--port", &port.to_string(),
        "--no-browser",
        "--host", "127.0.0.1"
    ])
    .spawn()
```

#### Argument CLI FastAPI
```python
# src/niamoto/cli/commands/gui.py

@click.command()
@click.option('--instance',
              type=click.Path(exists=True),
              help='Path to Niamoto instance (project directory)')
@click.option('--port', default=8080)
@click.option('--host', default='127.0.0.1')
@click.option('--no-browser', is_flag=True)
def gui(instance: Optional[str], port: int, host: str, no_browser: bool):
    """Launch Niamoto GUI"""

    # Si --instance fourni, l'utiliser comme projet actif
    if instance:
        os.environ['NIAMOTO_HOME'] = instance
        logger.info(f"Using project instance: {instance}")

    # Suite du code existant
    ...
```

### 4.2 API Tauri Commands (Rust ↔ TypeScript)

#### get_recent_projects
```rust
#[tauri::command]
async fn get_recent_projects() -> Result<Vec<ProjectInfo>, String> {
    let config = AppConfig::load().map_err(|e| e.to_string())?;
    Ok(config.recent_projects)
}
```

```typescript
import { invoke } from '@tauri-apps/api/core'

const projects = await invoke<ProjectInfo[]>('get_recent_projects')
```

#### get_current_project
```rust
#[tauri::command]
async fn get_current_project() -> Result<Option<ProjectInfo>, String> {
    let config = AppConfig::load().map_err(|e| e.to_string())?;

    if let Some(path) = config.last_opened_project {
        // Retrouver dans recent_projects
        let project = config.recent_projects.iter()
            .find(|p| p.path == path)
            .cloned();
        Ok(project)
    } else {
        Ok(None)
    }
}
```

```typescript
const current = await invoke<ProjectInfo | null>('get_current_project')
```

#### switch_project
```rust
#[tauri::command]
async fn switch_project(
    path: String,
    app_handle: tauri::AppHandle,
    state: tauri::State<'_, ServerState>,
) -> Result<(), String> {
    let project_path = PathBuf::from(&path);

    // Validation
    if !project_path.exists() {
        return Err(format!("Project path does not exist: {}", path));
    }

    if !is_niamoto_project(&project_path) {
        return Err("Not a valid Niamoto project".to_string());
    }

    // 1. Arrêter serveur actuel
    if let Some(mut process) = state.process.lock().unwrap().take() {
        let _ = process.kill();
        let _ = process.wait();
    }

    // 2. Mettre à jour config
    let mut config = AppConfig::load().map_err(|e| e.to_string())?;
    let name = project_path.file_name()
        .unwrap_or_default()
        .to_string_lossy()
        .to_string();
    config.add_recent_project(project_path.clone(), name);
    config.save().map_err(|e| e.to_string())?;

    // 3. Relancer serveur
    let port = find_free_port();
    let new_process = launch_fastapi_server(&app_handle, &project_path, port)
        .map_err(|e| e.to_string())?;

    *state.process.lock().unwrap() = Some(new_process);

    // 4. Attendre que serveur soit prêt
    let max_attempts = 60;
    for _ in 0..max_attempts {
        if is_server_ready(port) {
            break;
        }
        std::thread::sleep(std::time::Duration::from_millis(500));
    }

    Ok(())
}
```

```typescript
await invoke('switch_project', { path: '/path/to/project' })
// Puis recharger UI
window.location.reload()
```

#### open_project_dialog
```rust
#[tauri::command]
async fn open_project_dialog(
    app_handle: tauri::AppHandle,
) -> Result<Option<String>, String> {
    use tauri::api::dialog::blocking::FileDialogBuilder;

    let result = FileDialogBuilder::new()
        .set_title("Select Niamoto Project Folder")
        .pick_folder();

    if let Some(path) = result {
        // Valider que c'est un projet Niamoto
        if is_niamoto_project(&path) {
            Ok(Some(path.to_string_lossy().to_string()))
        } else {
            Err("Selected folder is not a Niamoto project".to_string())
        }
    } else {
        Ok(None)  // User cancelled
    }
}
```

```typescript
const path = await invoke<string | null>('open_project_dialog')
if (path) {
  await invoke('switch_project', { path })
}
```

#### create_new_project
```rust
#[tauri::command]
async fn create_new_project(
    path: String,
    name: String,
) -> Result<String, String> {
    let project_path = PathBuf::from(&path).join(&name);

    // Exécuter `niamoto init --path` pour créer le projet
    // NOTE: Requiert que la CLI supporte l'option --path (dépendance critique)
    let exe_path = get_niamoto_server_path()?;

    let output = std::process::Command::new(&exe_path)
        .args(&["init", "--path", project_path.to_str().unwrap()])
        .output()
        .map_err(|e| format!("Failed to initialize project: {}", e))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(format!("Init failed: {}", stderr));
    }

    Ok(project_path.to_string_lossy().to_string())
}
```

```typescript
const newProjectPath = await invoke<string>('create_new_project', {
  path: '/Users/me/Documents',
  name: 'my-new-project'
})
```

### 4.3 API Python (Interne)

#### ResourcePaths API
```python
from niamoto.common.resource_paths import ResourcePaths

# Dans plugin_loader.py
def discover_plugins(project_path: Optional[Path] = None) -> Dict[str, Type[BasePlugin]]:
    """
    Découvre tous les plugins dans l'ordre de priorité.

    Returns:
        Dict[plugin_name, PluginClass] où les locaux ont override les globaux
    """
    all_plugins = {}

    # Récupérer tous les emplacements (ordre priorité décroissante)
    locations = ResourcePaths.get_plugin_paths(project_path)

    # Parcourir en ordre inverse pour que haute priorité écrase basse
    for location in reversed(locations):
        if not location.exists:
            logger.debug(f"Plugin path does not exist: {location.path}")
            continue

        logger.info(f"Scanning {location.scope} plugins: {location.path}")
        plugins = _scan_directory_for_plugins(location.path)

        for name, plugin_class in plugins.items():
            if name in all_plugins:
                logger.debug(
                    f"Plugin '{name}' from {location.scope} overrides previous"
                )
            all_plugins[name] = plugin_class

    return all_plugins
```

#### Template loader (similaire)
```python
def get_available_templates(project_path: Optional[Path] = None) -> List[str]:
    """Liste tous les templates disponibles"""
    templates = []

    for location in ResourcePaths.get_template_paths(project_path):
        if location.exists:
            template_files = location.path.glob("*.yml")
            templates.extend([t.stem for t in template_files])

    return list(set(templates))  # Dédupliquer
```

---

## 5. Flux de données

### 5.1 Premier lancement (aucun projet)

```
┌──────────────┐
│ User clicks  │
│ Niamoto.app  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────┐
│ Rust: setup() in lib.rs      │
│ 1. Load config               │
│    → config.json n'existe pas│
│    → Create default          │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Rust: select_project()       │
│ 1. config.last_opened = None │
│ 2. No recent projects        │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ React: WelcomeScreen         │
│                              │
│ Display:                     │
│ - "Open Existing Project"    │
│ - "Create New Project"       │
│                              │
│ User clicks "Open Existing"  │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Rust: open_project_dialog()  │
│ File picker opens            │
│ User selects niamoto-nc/     │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Rust: switch_project()       │
│ 1. Validate path             │
│ 2. Update config             │
│ 3. Save config.json          │
│ 4. Launch FastAPI server     │
│    with --instance           │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Python: FastAPI starts       │
│ 1. Read NIAMOTO_HOME         │
│ 2. Load plugins (cascade)    │
│ 3. Connect to DB             │
│ 4. Start Uvicorn             │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Rust: Wait for health check  │
│ Poll /api/health until ready │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ React: Load main UI          │
│ 1. Fetch current project     │
│ 2. Render ProjectSwitcher    │
│ 3. Load dashboard            │
└──────────────────────────────┘
```

### 5.2 Lancement suivant (projet déjà connu)

```
┌──────────────┐
│ User clicks  │
│ Niamoto.app  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────┐
│ Rust: setup()                │
│ 1. Load config.json          │
│ 2. last_opened = niamoto-nc  │
│ 3. open_last = true          │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Rust: select_project()       │
│ 1. Use last_opened           │
│ 2. Validate still exists     │
│ 3. Return path directly      │
│    → NO user interaction     │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Show loading screen          │
│ "Opening niamoto-nc..."      │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Launch server + wait ready   │
│ (même flux que premier       │
│  lancement)                  │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Main UI loaded directly      │
└──────────────────────────────┘
```

### 5.3 Switch de projet (runtime)

```
┌──────────────────────────────┐
│ User clicks dropdown         │
│ Selects "niamoto-test"       │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ React: invoke switch_project │
│ await invoke('switch_project'│
│   { path: '...' })           │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Rust: switch_project()       │
│ 1. Kill current server       │
│    process.kill()            │
│    process.wait()            │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ 2. Update config             │
│    add_recent_project()      │
│    save()                    │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ 3. Launch new server         │
│    launch_fastapi_server(    │
│      new_project_path        │
│    )                         │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ 4. Wait health check         │
│    Poll /api/health          │
│    Max 30s                   │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Rust: Return Ok(())          │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ React: Reload window         │
│ window.location.reload()     │
│                              │
│ → UI reloads with new        │
│   project context            │
└──────────────────────────────┘
```

### 5.4 Résolution plugin (cascade)

```
Python: discover_plugins(project_path="/path/to/niamoto-nc")
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ ResourcePaths.get_plugin_paths()                     │
│                                                      │
│ Returns:                                             │
│ [                                                    │
│   ResourceLocation(                                  │
│     scope="project",                                 │
│     path="/path/to/niamoto-nc/.niamoto/plugins",    │
│     priority=100                                     │
│   ),                                                 │
│   ResourceLocation(                                  │
│     scope="user",                                    │
│     path="~/.niamoto/plugins",                      │
│     priority=50                                      │
│   ),                                                 │
│   ResourceLocation(                                  │
│     scope="system",                                  │
│     path="<bundle>/niamoto/plugins",                │
│     priority=10                                      │
│   )                                                  │
│ ]                                                    │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ Iterate in REVERSE order (system → user → project)  │
│                                                      │
│ all_plugins = {}                                     │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ 1. Scan system plugins                               │
│    Find: ["basic_stats", "occurrence_map"]           │
│    all_plugins = {                                   │
│      "basic_stats": SystemBasicStats,                │
│      "occurrence_map": SystemOccurrenceMap           │
│    }                                                 │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ 2. Scan user plugins                                 │
│    Find: ["my_custom_transformer"]                   │
│    all_plugins = {                                   │
│      "basic_stats": SystemBasicStats,                │
│      "occurrence_map": SystemOccurrenceMap,          │
│      "my_custom_transformer": UserCustom  ← NEW      │
│    }                                                 │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ 3. Scan project plugins                              │
│    Find: ["basic_stats", "project_specific"]         │
│    all_plugins = {                                   │
│      "basic_stats": ProjectBasicStats,  ← OVERRIDE   │
│      "occurrence_map": SystemOccurrenceMap,          │
│      "my_custom_transformer": UserCustom,            │
│      "project_specific": ProjectPlugin   ← NEW       │
│    }                                                 │
└──────┬───────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────┐
│ Return all_plugins                                   │
│                                                      │
│ Result: Project "basic_stats" a écrasé la version    │
│         système, les autres coexistent               │
└──────────────────────────────────────────────────────┘
```

---

## 6. Composants UI détaillés

### 6.1 ProjectSwitcher (Dropdown)

**Localisation :** `src/niamoto/gui/ui/src/components/ProjectSwitcher.tsx`

**Props :**
```typescript
interface ProjectSwitcherProps {
  // Optionnel: callback après switch
  onProjectChanged?: (project: ProjectInfo) => void
}
```

**État interne :**
```typescript
const [currentProject, setCurrentProject] = useState<ProjectInfo | null>(null)
const [recentProjects, setRecentProjects] = useState<ProjectInfo[]>([])
const [isLoading, setIsLoading] = useState(false)
const [isSwitching, setIsSwitching] = useState(false)
const [error, setError] = useState<string | null>(null)
```

**Structure DOM :**
```tsx
<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="ghost" className="gap-2 min-w-[200px]">
      <FolderOpen className="h-4 w-4" />
      <span className="flex-1 text-left truncate">
        {currentProject?.name || 'Select Project'}
      </span>
      <ChevronDown className="h-4 w-4 text-muted-foreground" />
    </Button>
  </DropdownMenuTrigger>

  <DropdownMenuContent align="start" className="w-80">
    {/* Section: Search */}
    <div className="p-2">
      <Input
        placeholder="Search projects..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="h-8"
      />
    </div>

    <DropdownMenuSeparator />

    {/* Section: Recent Projects */}
    <DropdownMenuLabel>Recent Projects</DropdownMenuLabel>
    {filteredRecent.map((project) => (
      <DropdownMenuItem
        key={project.path}
        onClick={() => handleSwitchProject(project.path)}
        className="cursor-pointer"
      >
        <div className="flex items-center gap-2 w-full">
          {project.isPinned && <Pin className="h-3 w-3" />}
          <div className="flex-1 min-w-0">
            <div className="font-medium truncate">{project.name}</div>
            <div className="text-xs text-muted-foreground truncate">
              {project.path}
            </div>
          </div>
          {currentProject?.path === project.path && (
            <Check className="h-4 w-4 text-primary" />
          )}
        </div>
      </DropdownMenuItem>
    ))}

    <DropdownMenuSeparator />

    {/* Section: Actions */}
    <DropdownMenuItem onClick={handleOpenProjectDialog}>
      <FolderOpen className="mr-2 h-4 w-4" />
      Open Other Project...
    </DropdownMenuItem>

    <DropdownMenuItem onClick={handleCreateNew}>
      <Plus className="mr-2 h-4 w-4" />
      Create New Project...
    </DropdownMenuItem>

    <DropdownMenuSeparator />

    <DropdownMenuItem onClick={handleManageProjects}>
      <Settings className="mr-2 h-4 w-4" />
      Manage Projects...
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

**Méthodes principales :**
```typescript
const handleSwitchProject = async (path: string) => {
  setIsSwitching(true)
  setError(null)

  try {
    // Invoke Tauri command
    await invoke('switch_project', { path })

    // Callback optionnel
    onProjectChanged?.(project)

    // Reload UI
    window.location.reload()

  } catch (err) {
    setError(err.message)
    setIsSwitching(false)
  }
}

const handleOpenProjectDialog = async () => {
  try {
    const path = await invoke<string | null>('open_project_dialog')
    if (path) {
      await handleSwitchProject(path)
    }
  } catch (err) {
    setError(err.message)
  }
}

const handleCreateNew = async () => {
  // Ouvrir dialog pour choisir parent folder + nom
  // Puis invoke create_new_project
  // Puis switch vers le nouveau projet
}

const handleManageProjects = () => {
  // Navigate to /settings/projects
  navigate('/settings/projects')
}
```

### 6.2 WelcomePage (Écran premier lancement)

**Localisation :** `src/niamoto/gui/ui/src/pages/Welcome.tsx`

**Structure :**
```tsx
<div className="flex h-screen items-center justify-center bg-gradient-to-br from-background to-muted">
  <Card className="w-full max-w-2xl shadow-2xl">
    <CardHeader className="text-center">
      <div className="mx-auto mb-4 text-6xl">🌿</div>
      <CardTitle className="text-4xl font-bold">Niamoto Desktop</CardTitle>
      <CardDescription className="text-lg">
        Manage your ecological data projects
      </CardDescription>
    </CardHeader>

    <CardContent className="space-y-6">
      {/* Main Actions */}
      <div className="grid grid-cols-2 gap-4">
        <Button
          size="lg"
          onClick={handleOpenExisting}
          className="h-24 flex-col"
        >
          <FolderOpen className="h-8 w-8 mb-2" />
          <span>Open Existing Project</span>
        </Button>

        <Button
          size="lg"
          variant="outline"
          onClick={handleCreateNew}
          className="h-24 flex-col"
        >
          <Plus className="h-8 w-8 mb-2" />
          <span>Create New Project</span>
        </Button>
      </div>
    </CardContent>
  </Card>
</div>
```

### 6.3 ProjectManagement (Settings page)

**Localisation :** `src/niamoto/gui/ui/src/pages/settings/Projects.tsx`

**Vue en liste avec actions :**
```tsx
<div className="space-y-6">
  <div className="flex items-center justify-between">
    <h2 className="text-2xl font-bold">Manage Projects</h2>
    <Button onClick={handleAddProject}>
      <Plus className="mr-2 h-4 w-4" />
      Add Project
    </Button>
  </div>

  <Table>
    <TableHeader>
      <TableRow>
        <TableHead>Project Name</TableHead>
        <TableHead>Path</TableHead>
        <TableHead>Last Opened</TableHead>
        <TableHead>Size</TableHead>
        <TableHead className="text-right">Actions</TableHead>
      </TableRow>
    </TableHeader>
    <TableBody>
      {projects.map((project) => (
        <TableRow key={project.path}>
          <TableCell className="font-medium">
            <div className="flex items-center gap-2">
              {project.isPinned && (
                <Pin className="h-4 w-4 text-primary" />
              )}
              {project.name}
            </div>
          </TableCell>
          <TableCell className="text-sm text-muted-foreground">
            {project.path}
          </TableCell>
          <TableCell className="text-sm">
            {formatRelativeTime(project.lastOpened)}
          </TableCell>
          <TableCell className="text-sm">
            {formatBytes(project.metadata?.sizeBytes)}
          </TableCell>
          <TableCell className="text-right">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => openProject(project)}>
                  Open
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => togglePin(project)}>
                  {project.isPinned ? 'Unpin' : 'Pin'}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => showInFinder(project)}>
                  Show in Finder
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  className="text-destructive"
                  onClick={() => removeProject(project)}
                >
                  Remove from List
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
</div>
```

---

## 7. Résolution des ressources

### 7.1 Algorithme de résolution

**Pseudo-code :**
```
function resolve_resource(resource_type, resource_name, project_path):
    locations = get_search_paths(resource_type, project_path)

    # Trier par priorité décroissante
    locations.sort(key=lambda l: l.priority, reverse=True)

    for location in locations:
        resource_path = location.path / resource_name
        if resource_path.exists():
            return (resource_path, location.scope)

    return None  # Not found
```

**Exemple concret :**
```python
# Chercher le plugin "basic_stats"
result = resolve_resource("plugin", "basic_stats", "/path/to/niamoto-nc")

# Recherche dans l'ordre:
# 1. /path/to/niamoto-nc/.niamoto/plugins/basic_stats.py (FOUND)
#    → Return ("/path/to/niamoto-nc/.niamoto/plugins/basic_stats.py", "project")

# Si pas trouvé en 1:
# 2. ~/.niamoto/plugins/basic_stats.py
#    → Return ("~/.niamoto/plugins/basic_stats.py", "user")

# Si pas trouvé en 1 et 2:
# 3. <system>/niamoto/plugins/basic_stats.py
#    → Return ("<system>/niamoto/plugins/basic_stats.py", "system")
```

### 7.2 Gestion des conflits

**Cas 1 : Même nom, différentes versions**
```
System: basic_stats v1.0
User:   basic_stats v2.0 (custom fork)
Project: basic_stats v1.5 (project-specific)

Résultat: Project v1.5 est utilisé (priorité la plus haute)
```

**Cas 2 : Dépendances entre plugins**

Si `plugin_A` (project) dépend de `plugin_B`:
```python
# Dans plugin_A
class PluginA(TransformerPlugin):
    dependencies = ["plugin_B"]

    def transform(self, data, config):
        # Plugin B sera résolu selon cascade normale
        plugin_b = registry.get("plugin_B")
        ...
```

**Logging pour debug :**
```python
logger.info(f"Loading plugin 'basic_stats' from {scope}: {path}")
logger.debug(f"Plugin 'custom_transformer' available only in user scope")
logger.warning(f"Plugin 'deprecated_plugin' overridden by project version")
```

### 7.3 Validation et santé

**Vérifications au chargement :**
```python
def validate_resource(path: Path, resource_type: str) -> bool:
    """Valide qu'une ressource est correcte"""

    if resource_type == "plugin":
        # Vérifier que c'est un fichier Python valide
        if not path.suffix == ".py":
            return False

        # Vérifier qu'il contient une classe avec @register
        try:
            spec = importlib.util.spec_from_file_location("temp", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # Chercher décorateur @register
            return hasattr(module, '__plugin_registered__')
        except Exception as e:
            logger.error(f"Invalid plugin {path}: {e}")
            return False

    elif resource_type == "template":
        # Vérifier YAML valide
        try:
            with open(path) as f:
                yaml.safe_load(f)
            return True
        except:
            return False

    return True
```

---

## 8. Cas d'usage

### 8.1 UC-01 : Premier lancement

**Acteur :** Utilisateur
**Préconditions :**
- Application desktop jamais lancée

**Flux principal :**
1. Utilisateur double-clique sur Niamoto.app
2. App démarre, charge config (vide)
3. App affiche WelcomePage avec 2 options:
   - "Open Existing Project"
   - "Create New Project"
4. Utilisateur clique "Open Existing Project"
5. Sélecteur de fichiers s'ouvre
6. Utilisateur navigue vers et sélectionne `test-instance/niamoto-nc/`
7. App valide que c'est un projet Niamoto
8. App lance serveur FastAPI avec `--instance test-instance/niamoto-nc`
9. Interface principale s'affiche avec niamoto-nc chargé

**Postconditions :**
- `config.json` créé avec 1 projet récent
- `last_opened_project = niamoto-nc`
- Serveur tourne sur port aléatoire
- UI affichée avec projet actif

**Flux alternatifs :**
- 4a. Utilisateur clique "Create New" → Dialog de création (voir UC-03)
- 7a. Dossier sélectionné n'est pas un projet Niamoto → Erreur affichée
- 8a. Serveur ne démarre pas → Erreur affichée, retour à WelcomePage

### 8.2 UC-02 : Switch de projet (runtime)

**Acteur :** Utilisateur travaillant sur un projet
**Préconditions :**
- App lancée avec niamoto-nc ouvert
- 5 projets dans la liste récents

**Flux principal :**
1. Utilisateur clique sur dropdown "niamoto-nc ▼"
2. Menu déroulant s'affiche avec liste de 5 projets
3. Utilisateur clique sur "niamoto-test"
4. Loading overlay s'affiche "Switching to niamoto-test..."
5. Serveur actuel (niamoto-nc) est arrêté proprement
6. Config mise à jour (niamoto-test en tête de liste)
7. Nouveau serveur lancé avec `--instance niamoto-test`
8. App attend health check (max 30s)
9. UI recharge avec contexte niamoto-test

**Postconditions :**
- niamoto-test est le projet actif
- Config sauvegardée avec niamoto-test en last_opened
- Serveur précédent (niamoto-nc) complètement arrêté
- Nouveau serveur (niamoto-test) écoute sur nouveau port

**Flux alternatifs :**
- 5a. Erreur à l'arrêt serveur → Force kill après 5s
- 8a. Health check timeout → Erreur, rollback vers niamoto-nc
- 3a. Utilisateur annule → Rien ne change

### 8.3 UC-03 : Création nouveau projet

**Acteur :** Utilisateur démarrant nouveau projet
**Préconditions :**
- App lancée

**Flux principal :**
1. Utilisateur clique sur dropdown
2. Clique "Create New Project..."
3. Dialog s'ouvre:
   - Parent folder: ~/Documents/Niamoto/
   - Project name: [my-new-project]
   - Template: [Default / Custom template]
4. Utilisateur remplit:
   - Name: "Etude Parc Provincial"
   - Template: "New Caledonia Flora"
5. Utilisateur clique "Create"
6. App exécute `niamoto init --path ~/Documents/Niamoto/Etude\ Parc\ Provincial --template "New Caledonia Flora"`
7. Init réussit, structure créée
8. App switch automatiquement vers nouveau projet
9. Interface s'ouvre sur dashboard vide du nouveau projet

**Postconditions :**
- Nouveau projet créé sur disque
- Ajouté à recent_projects
- Projet actif dans l'app

**Flux alternatifs :**
- 5a. Nom invalide → Erreur validation
- 7a. Init échoue → Erreur affichée, dossier nettoyé
- 4a. Utilisateur annule → Rien créé

### 8.4 UC-04 : Utilisation plugin global

**Acteur :** Scientifique utilisant plugin custom
**Préconditions :**
- Utilisateur a développé plugin "species_distribution_analysis"
- Plugin placé dans `~/.niamoto/plugins/`
- 2 projets ouverts: niamoto-nc, niamoto-test

**Flux principal :**
1. Utilisateur ouvre niamoto-nc
2. Va dans Transform
3. Liste des transformers affiche "species_distribution_analysis" (scope: user)
4. Utilisateur sélectionne et configure
5. Exécute transformation → Fonctionne
6. Utilisateur switch vers niamoto-test
7. Va dans Transform
8. Liste affiche aussi "species_distribution_analysis" (scope: user)
9. Exécute sur niamoto-test → Fonctionne

**Postconditions :**
- Plugin utilisable dans tous les projets
- Pas besoin de le dupliquer

**Flux alternatifs :**
- 8a. niamoto-test a override local du même plugin
  → Version locale utilisée, user global ignoré
  → UI indique "(local override)" à côté du nom

### 8.5 UC-05 : Override plugin local

**Acteur :** Développeur testant nouvelle version
**Préconditions :**
- Plugin "basic_stats" existe en version système
- Projet niamoto-nc actif

**Flux principal :**
1. Utilisateur copie `basic_stats.py` modifié dans `niamoto-nc/.niamoto/plugins/`
2. Utilisateur redémarre serveur (ou hot-reload si implémenté)
3. System détecte nouveau plugin en scope project
4. Lors de `discover_plugins()`:
   - Trouve basic_stats (system, priority 10)
   - Trouve basic_stats (project, priority 100)
   - Garde version project (priorité plus haute)
5. Log affiche: "Plugin 'basic_stats' overridden by project version"
6. Utilisateur exécute transform
7. Version locale est utilisée

**Postconditions :**
- Version locale utilisée uniquement pour niamoto-nc
- Autres projets utilisent toujours version système
- Log clair sur l'override

---

## 9. Sécurité & Performance

### 9.1 Sécurité

**Validation des chemins :**
```rust
fn is_niamoto_project(path: &Path) -> bool {
    // Vérifier que le chemin est valide et safe
    if !path.exists() || !path.is_dir() {
        return false;
    }

    // Vérifier présence de marqueurs Niamoto
    let has_niamoto_dir = path.join(".niamoto").exists();
    let has_config = path.join("import.yml").exists()
                  || path.join("niamoto.yml").exists();

    has_niamoto_dir || has_config
}
```

**Sanitization des entrées utilisateur :**
```rust
fn sanitize_project_name(name: &str) -> String {
    // Supprimer caractères dangereux
    name.chars()
        .filter(|c| c.is_alphanumeric() || *c == '-' || *c == '_' || *c == ' ')
        .collect()
}
```

**Permissions fichiers :**
```rust
// Créer ~/.niamoto/ avec permissions restrictives
std::fs::create_dir_all(&user_dir)?;
#[cfg(unix)]
{
    use std::os::unix::fs::PermissionsExt;
    let mut perms = std::fs::metadata(&user_dir)?.permissions();
    perms.set_mode(0o700);  // rwx------
    std::fs::set_permissions(&user_dir, perms)?;
}
```

### 9.2 Performance

**Lazy loading des projets :**
```typescript
// Ne charger métadonnées que quand dropdown ouvert
const ProjectSwitcher = () => {
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    if (isOpen) {
      // Charger liste complète seulement maintenant
      loadProjectsWithMetadata()
    }
  }, [isOpen])
}
```

**Optimisation switch projet :**
```rust
// Kill avec timeout, puis force kill
fn stop_server_gracefully(process: &mut Child) -> Result<()> {
    // Envoyer SIGTERM
    process.kill()?;

    // Attendre max 5s
    let timeout = Duration::from_secs(5);
    let start = Instant::now();

    loop {
        match process.try_wait()? {
            Some(_) => return Ok(()),  // Terminé
            None => {
                if start.elapsed() > timeout {
                    // Force kill
                    #[cfg(unix)]
                    {
                        use nix::sys::signal::{kill, Signal};
                        use nix::unistd::Pid;
                        kill(Pid::from_raw(process.id() as i32), Signal::SIGKILL)?;
                    }
                    return Ok(());
                }
                std::thread::sleep(Duration::from_millis(100));
            }
        }
    }
}
```

**Throttling de sauvegarde config :**
```rust
// Ne sauvegarder config que toutes les 5s max
struct ConfigSaver {
    pending_config: Option<AppConfig>,
    last_save: Instant,
}

impl ConfigSaver {
    fn save_debounced(&mut self, config: AppConfig) {
        self.pending_config = Some(config);

        if self.last_save.elapsed() > Duration::from_secs(5) {
            self.flush();
        }
    }

    fn flush(&mut self) {
        if let Some(config) = self.pending_config.take() {
            config.save().ok();
            self.last_save = Instant::now();
        }
    }
}
```

---

## 10. Plan de tests

### 10.1 Tests unitaires

**Rust :**
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_load_default() {
        let config = AppConfig::default();
        assert!(config.recent_projects.is_empty());
        assert_eq!(config.version, "1.0");
    }

    #[test]
    fn test_add_recent_project() {
        let mut config = AppConfig::default();
        config.add_recent_project(
            PathBuf::from("/tmp/test"),
            "test".to_string()
        );

        assert_eq!(config.recent_projects.len(), 1);
        assert_eq!(config.last_opened_project, Some(PathBuf::from("/tmp/test")));
    }

    #[test]
    fn test_recent_projects_max_10() {
        let mut config = AppConfig::default();

        for i in 0..15 {
            config.add_recent_project(
                PathBuf::from(format!("/tmp/test{}", i)),
                format!("test{}", i)
            );
        }

        assert_eq!(config.recent_projects.len(), 10);
    }

    #[test]
    fn test_is_niamoto_project() {
        // Créer projet temporaire valide
        let temp = tempdir().unwrap();
        let project = temp.path().join("test-project");
        std::fs::create_dir_all(project.join(".niamoto")).unwrap();

        assert!(is_niamoto_project(&project));
    }
}
```

**Python :**
```python
def test_resource_paths_cascade():
    """Test résolution en cascade"""
    project_path = Path("/tmp/test-project")

    locations = ResourcePaths.get_plugin_paths(project_path)

    # Doit avoir 3 emplacements
    assert len(locations) == 3

    # Ordre de priorité correct
    assert locations[0].scope == "project"
    assert locations[0].priority == 100
    assert locations[1].scope == "user"
    assert locations[1].priority == 50
    assert locations[2].scope == "system"
    assert locations[2].priority == 10

def test_plugin_override():
    """Test qu'un plugin local override global"""
    # Setup: créer plugin dans system et project
    # Vérifier que project version est chargée
    pass
```

### 10.2 Tests d'intégration

**Test E2E : Premier lancement → Switch projet**
```python
@pytest.mark.e2e
async def test_first_launch_and_switch():
    # 1. Simuler premier lancement
    app = await launch_app(clean_config=True)

    # 2. Vérifier welcome screen affiché
    welcome = await app.find_element("welcome-page")
    assert welcome.is_visible()

    # 3. Ouvrir premier projet
    await app.click("open-existing-button")
    project1_path = "/tmp/test-project-1"
    await app.select_folder(project1_path)

    # 4. Attendre chargement
    await app.wait_for_server_ready(timeout=30)

    # 5. Vérifier UI principale
    dashboard = await app.find_element("dashboard")
    assert dashboard.is_visible()

    # 6. Switch vers autre projet
    await app.click("project-switcher")
    await app.click("open-other-project")
    project2_path = "/tmp/test-project-2"
    await app.select_folder(project2_path)

    # 7. Vérifier switch réussi
    await app.wait_for_server_ready(timeout=30)
    current = await app.invoke("get_current_project")
    assert current.path == project2_path
```

### 10.3 Tests de performance

**Test : Switch projet < 5s**
```python
def test_switch_performance():
    app = launch_app()

    start = time.time()
    app.switch_project("/path/to/other-project")
    app.wait_for_ready()
    elapsed = time.time() - start

    assert elapsed < 5.0, f"Switch took {elapsed}s, expected < 5s"
```

### 10.4 Tests de régression

**Checklist avant release :**
- [ ] CLI `niamoto gui` fonctionne toujours
- [ ] Plugins se chargent correctement (résolution cascade)
- [ ] Config YAML (import.yml, transform.yml) fonctionnent
- [ ] API REST endpoints fonctionnent
- [ ] Performance (import/transform/export) acceptable

---

## Annexes

### A. Prérequis CLI (dépendances critiques)

**IMPORTANT : Ces modifications CLI doivent être implémentées EN PREMIER**

#### 1. Option `--path` pour `niamoto init` (PRIORITAIRE)

**Problème actuel :**
```bash
niamoto init project_name  # Crée dans le répertoire courant seulement
```

**Besoin pour Desktop :**
```bash
niamoto init --path /absolute/path/to/project  # Création à chemin absolu
```

**Implémentation requise dans `src/niamoto/cli/commands/initialize.py` :**
```python
@click.command(name="init")
@click.argument("project_name", required=False)
@click.option("--path", type=click.Path(), help="Absolute path where to create the project")
@click.option("--template", help="Template to use for initialization")
# ... autres options existantes
def init_environment(project_name: str, path: str, template: str, ...) -> None:
    """
    Initialize a Niamoto project.

    If --path is provided, creates project at that location.
    If project_name is provided without --path, creates in current directory.
    """
    if path:
        target_path = Path(path).resolve()
    elif project_name:
        target_path = Path.cwd() / project_name
    else:
        target_path = Path.cwd()

    # Créer le projet à target_path
    ...
```

**Utilisé par :**
- Commande Tauri `create_new_project` (src-tauri/src/commands.rs)
- Cas d'usage UC-03 (Création nouveau projet)

**Sans cette modification, la fonctionnalité "Create New Project" du Desktop ne peut pas fonctionner.**

---

### B. Dépendances à ajouter

**Rust (Cargo.toml) :**
```toml
[dependencies]
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
dirs = "5.0"           # Pour home_dir()
chrono = "0.4"         # Pour timestamps
```

**Python (requirements.txt) :**
```
# Aucune nouvelle dépendance nécessaire
# (pathlib, typing sont dans stdlib)
```

**TypeScript (package.json) :**
```json
{
  "dependencies": {
    "@tauri-apps/api": "^2.0.0",
    "@tauri-apps/plugin-dialog": "^2.0.0"
  }
}
```

### C. Checklist UX

**Expérience utilisateur :**
- [ ] Welcome screen clair et guidant
- [ ] Sélection de projet intuitive (file picker)
- [ ] Création de nouveau projet simple
- [ ] Switch de projet fluide (< 5s)
- [ ] Messages d'erreur explicites
- [ ] CLI et Desktop cohabitent sans conflit

### D. Évolutions futures (hors scope Phase 1)

**Phase 2 :**
- Command Palette (Cmd+P)
- Project templates avancés
- Project health monitoring
- Favoris/tags/couleurs

**Phase 3 :**
- Multi-window support
- Cloud sync des configs
- Team collaboration
- Plugin marketplace

---

**Fin du document d'architecture**

Version 1.0 - 16 novembre 2024
