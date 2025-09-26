# Niamoto GUI - Interface Graphique de Configuration

## Vue d'ensemble

L'interface graphique Niamoto (GUI) est une application web moderne qui simplifie la création et la gestion des pipelines de données écologiques. Elle permet aux utilisateurs de configurer visuellement leurs projets sans écrire de YAML.

## Objectifs

- **Accessibilité** : Permettre aux écologistes sans compétences techniques de créer des portails de données
- **Productivité** : Réduire le temps de configuration de 2h à 10 minutes
- **Fiabilité** : Validation en temps réel pour éviter les erreurs
- **Progressivité** : Du mode guidé pour débutants au mode expert

## Architecture

L'interface GUI est composée de deux parties :

### Backend (FastAPI)
- API REST pour la gestion des configurations
- Validation en temps réel avec Pydantic
- Génération automatique des fichiers YAML
- Support de l'upload de fichiers
- Preview des transformations

### Frontend (React + TypeScript)
- Interface moderne et réactive
- Éditeur visuel de flux (à venir avec React Flow)
- Formulaires intelligents avec validation
- Preview en temps réel des configurations

## Fonctionnalités actuelles (POC)

- ✅ Configuration basique Import/Transform/Export
- ✅ Génération de fichiers YAML
- ✅ Validation des configurations
- ✅ Intégration avec le CLI Niamoto
- ✅ Templates de base

## Fonctionnalités planifiées

- 🔄 Upload de fichiers CSV/Shapefile
- 🔄 Détection automatique des colonnes
- 🔄 Éditeur visuel de pipeline (React Flow)
- 🔄 Preview des transformations
- 🔄 Assistant de configuration guidé
- 🔄 Gestion multi-projets
- 🔄 Export/Import de configurations

## Installation

```bash
# Installer Niamoto avec les dépendances GUI
pip install niamoto[gui]

# Ou depuis les sources
pip install -e ".[gui]"
```

## Utilisation rapide

```bash
# Créer un nouveau projet avec l'interface GUI
mkdir mon-projet && cd mon-projet
niamoto init  # Lance automatiquement l'interface GUI

# Ou lancer l'interface pour un projet existant
niamoto gui

# Options disponibles
niamoto gui --port 8080      # Changer le port
niamoto gui --no-browser     # Ne pas ouvrir le navigateur
```

## Documentation

- [Guide de démarrage](getting-started.md) - Installation et premier projet
- [Parcours utilisateur](user-workflow.md) - Workflow détaillé avec exemples
- [POC actuel](poc-implementation.md) - État et limitations du prototype
- [Référence API](api-reference.md) - Documentation des endpoints
- [Guide de développement](development.md) - Architecture et workflow de développement
- [Architecture](development/architecture.md) - Détails techniques
- [Contribution](development/contributing.md) - Guide pour les développeurs
- [Roadmap](development/roadmap.md) - Évolutions prévues

## Support

Pour toute question ou problème :
- Consultez le [guide de dépannage](troubleshooting.md)
- Ouvrez une issue sur [GitHub](https://github.com/niamoto/niamoto/issues)
- Contactez l'équipe de développement

## Licence

L'interface GUI de Niamoto est distribuée sous la même licence que le projet principal (GPL-3.0-or-later).
