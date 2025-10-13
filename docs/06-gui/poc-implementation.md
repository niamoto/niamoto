# Documentation du POC - Interface GUI Niamoto

## État actuel du Proof of Concept

Cette page documente l'implémentation actuelle du POC de l'interface graphique Niamoto, ses fonctionnalités, limitations et architecture.

## Fonctionnalités implémentées

### 1. Backend API (FastAPI)

#### Endpoints disponibles

- **GET `/api/config/`** : Récupère la configuration actuelle du projet
  - Charge automatiquement les fichiers YAML existants
  - Retourne un objet avec les sections import, transform, export

- **POST `/api/config/validate`** : Valide une configuration
  - Vérifie la présence des sections requises
  - Validation basique de la structure
  - Retourne les erreurs détaillées

- **POST `/api/config/generate`** : Génère les fichiers YAML
  - Formate correctement les configurations
  - Retourne les YAML générés pour preview

- **GET `/api/config/templates`** : Liste les templates disponibles
  - Templates hardcodés pour le POC
  - Inclut : Flore simple, Inventaire forestier, Aires protégées

- **GET `/api/health`** : Vérification de santé du serveur

#### Architecture API

```text
src/niamoto/gui/
├── api/
│   ├── app.py          # Application FastAPI principale
│   ├── models.py       # Modèles Pydantic pour validation
│   └── routers/
│       └── config.py   # Routes de configuration
```

### 2. Frontend React

#### Composants principaux

- **App.tsx** : Composant principal avec gestion d'état
  - Chargement de la configuration existante
  - Formulaires pour Import/Transform/Export
  - Génération et preview des YAML

#### Fonctionnalités UI

1. **Section Import**
   - Champs pour chemins CSV taxonomie et occurrences
   - Option pour inclure les données de parcelles

2. **Section Transform**
   - Checkbox pour activer l'analyse "Top Species"
   - Checkbox pour générer les cartes de distribution

3. **Section Export**
   - Configuration du titre du site
   - Personnalisation de la couleur principale
   - Activation de la génération du site statique

4. **Génération YAML**
   - Validation avant génération
   - Preview formaté des fichiers YAML
   - Instructions pour l'utilisation

### 3. Intégration CLI

#### Commande `niamoto gui`

```text
# src/niamoto/cli/commands/gui.py
- Lance le serveur FastAPI
- Ouvre automatiquement le navigateur
- Options : --port, --host, --no-browser, --reload
```

#### Installation

```bash
# Dépendances ajoutées dans pyproject.toml
[project.optional-dependencies]
gui = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
]
```

## Limitations actuelles

### Backend
- Validation basique seulement (structure, pas contenu)
- Templates hardcodés (pas de système dynamique)
- Pas de gestion d'upload de fichiers
- Pas de preview des transformations
- Détection de projet limitée

### Frontend
- Interface basique (pas d'éditeur visuel)
- Champs de configuration limités
- Pas de validation côté client avancée
- Pas de gestion d'erreurs sophistiquée
- Style minimal

### Général
- Pas de persistence de session
- Pas de gestion multi-projets
- Pas d'authentification
- Pas de WebSocket pour updates temps réel

## Structure des fichiers

```
src/niamoto/gui/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── app.py              # FastAPI app
│   ├── models.py           # Pydantic models
│   └── routers/
│       ├── __init__.py
│       └── config.py       # Config endpoints
├── frontend/
│   ├── src/
│   │   ├── App.tsx         # Main component
│   │   ├── App.css         # Styles
│   │   ├── main.tsx        # Entry point
│   │   └── index.css       # Global styles
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── static/                 # Built frontend (generated)
└── README.md              # GUI documentation
```

## Configuration requise

### Python
- Python 3.10+
- FastAPI 0.115.0+
- Uvicorn 0.34.0+
- Pydantic (déjà dans Niamoto)

### Node.js (pour développement frontend)
- Node.js 18+
- React 18.3.1
- TypeScript 5.5.3
- Vite 5.3.1

## Utilisation du POC

### Mode production
```bash
# Installer les dépendances
pip install -e ".[gui]"

# Lancer l'interface
niamoto gui
```

### Mode développement
```bash
# Terminal 1 - Backend
cd src/niamoto/gui
uvicorn api.app:app --reload

# Terminal 2 - Frontend
cd src/niamoto/gui/frontend
npm install
npm run dev
```

## Tests manuels recommandés

1. **Chargement de configuration existante**
   - Lancer depuis un projet avec configs
   - Vérifier que les valeurs sont chargées

2. **Création nouvelle configuration**
   - Remplir les formulaires
   - Générer les YAML
   - Vérifier la validité du format

3. **Validation**
   - Tester avec configurations invalides
   - Vérifier les messages d'erreur

4. **Templates**
   - Charger un template
   - Vérifier le contenu

## Prochaines étapes

1. **Upload de fichiers**
   - Endpoint pour upload CSV
   - Analyse automatique des colonnes
   - Stockage temporaire

2. **Éditeur visuel**
   - Intégration React Flow
   - Drag & drop des composants
   - Connexions visuelles

3. **Preview avancé**
   - Exécution partielle du pipeline
   - Affichage des résultats
   - Graphiques de preview

4. **Amélioration UX**
   - Wizard guidé pour débutants
   - Plus de champs de configuration
   - Meilleure gestion d'erreurs

Cette implémentation POC pose les bases solides pour l'évolution vers une interface complète et intuitive.
