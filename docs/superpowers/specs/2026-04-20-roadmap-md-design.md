---
title: "ROADMAP.md à la racine — design"
type: docs
date: 2026-04-20
---

# ROADMAP.md à la racine — design

## Contexte

Le projet n'a pas de `ROADMAP.md` à la racine. Le dossier `docs/08-roadmaps/` a été volontairement allégé et ne contient plus qu'un landing minimal et la présentation standalone `gbif-challenge-2026.html`. Parallèlement, 21 brainstorms, ~48 plans et 16 specs superpowers s'accumulent depuis février 2026, avec un événement structurant à court terme : le **GBIF Ebbe Nielsen Challenge 2026** (deadline 26 juin 2026).

Un lecteur qui arrive sur le repo n'a aujourd'hui aucun moyen simple de voir où va le projet.

## Objectif

Fournir un `ROADMAP.md` à la racine du repo qui :

1. Donne à un contributeur externe une vision claire de ce qui est livré, en cours, prévu et hors-scope.
2. Met le GBIF Challenge 2026 en évidence comme contrainte court terme.
3. Sert aussi d'index interne vers les brainstorms, plans et specs existants.

## Décisions prises en brainstorming

- **Public cible hybride** : narratif en haut pour les contributeurs GitHub, liens vers brainstorms/plans/specs en fin de chaque item pour l'usage interne.
- **Structure linéaire** plutôt que matricielle thématique (la deadline GBIF ressort mieux).
- **Mix milestone + temporalité** : bloc GBIF épinglé + trois horizons temporels pour le reste.
- **Inclut "Récemment livré"** (contexte, vélocité).
- **Inclut "Non prévu"** (désamorce les demandes récurrentes).

## Structure du fichier

```
# Niamoto Roadmap

[badge / dernière mise à jour]

## Vision
2-3 phrases : plateforme ecologique generique, local-first, plugins.

## Recently shipped
5-6 items majeurs, 2-3 derniers mois.

## GBIF Ebbe Nielsen Challenge 2026 ⭐
Pitch "Local-First Intelligence" + livrables concrets + deadline 26 juin 2026.
Lien vers le rapport d'opportunité complet et la présentation HTML.

## Horizons
### Maintenant (avril - juin 2026)
Items en cours ou imminents.

### Bientôt (été 2026)
Items planifiés mais non démarrés.

### Plus tard (H2 2026 et après)
Items identifiés en ideation, non planifiés.

## Non prévu
Désamorce les demandes récurrentes.

## Comment contribuer
Lien vers CONTRIBUTING.md + brainstorms/plans/specs.

## Dernière mise à jour
Date + rythme de revue.
```

## Contenu proposé par section

### Vision

> Niamoto est une plateforme générique de données écologiques. Elle transforme des données hétérogènes en portails web publiables via un pipeline configurable Import → Transform → Export, localement, sans dépendance cloud. L'interface desktop (Tauri) et la CLI partagent le même moteur et les mêmes plugins.

### Recently shipped (tri chronologique inverse)

- **Pipeline macOS signing & notarization stable** (v0.15.5, avril 2026)
- **Système de feedback in-app** (plan 2026-04-04)
- **Enrichissement riche multi-sources** : GBIF, CoL, iNaturalist, BHL, GN TaxRef, Tropicos, spatial v1 (specs 2026-04-09/10)
- **Refonte sources dashboard + mission control** (plan 2026-04-01, spec 2026-03-29)
- **Parallélisation transform & export** (specs 2026-03-27)
- **Refonte frontend** vers `src/app`, `src/features`, `src/shared` (plan 2026-03-25)
- **Automatisation release** via skill `niamoto-release` (plan 2026-03-25)

### GBIF Ebbe Nielsen Challenge 2026 ⭐

**Deadline : 26 juin 2026 (≈67 jours à partir d'aujourd'hui)**

**Pitch** : _Niamoto — Local-First Intelligence_. Combinaison de curation intelligente locale (ML classique + fuzzy matching + SLM optionnel) et génération automatique de portails web depuis les données GBIF, **sans dépendance cloud** — angle différenciant face aux gagnants 2024-2025 qui s'appuient sur LLM distants.

**Livrables activés pour le challenge** :
1. **GBIF Rich Enrichment** — enrichissement taxonomique et spatial via API GBIF [plan](docs/plans/2026-04-09-feat-gbif-rich-enrichment-plan.md) · [spec](docs/superpowers/specs/2026-04-09-gbif-rich-enrichment-design.md)
2. **GBIF Registry Publication** — publication Niamoto comme outil référencé [plan](docs/plans/2026-03-13-feat-gbif-registry-publication-plan.md)
3. **Challenge Presentation Page** — landing dédiée pour la soumission [plan](docs/plans/2026-03-13-feat-gbif-challenge-presentation-page-plan.md)

**Bonus identifiés** (à activer selon budget temps) :
- Validation BDQ (12 tests Tier-1) — couvre ~60% des problèmes de qualité réels
- Détection de schéma locale pour import Darwin Core
- SLM local optionnel (Liquid AI LFM2 ou Qwen3 via Ollama)

**Références** :
- Rapport d'opportunité complet : [docs/plans/2026-03-11-feat-gbif-ebbe-nielsen-challenge-2026-opportunity-report.md](docs/plans/2026-03-11-feat-gbif-ebbe-nielsen-challenge-2026-opportunity-report.md)
- Présentation HTML : [docs/08-roadmaps/gbif-challenge-2026.html](docs/08-roadmaps/gbif-challenge-2026.html)

### Maintenant (avril - juin 2026)

**Desktop & distribution**
- Desktop update harness & auto-updater [spec](docs/superpowers/specs/2026-04-08-desktop-update-harness-design.md)
- Audit taille binaire desktop [plan](docs/plans/2026-04-19-001-refactor-desktop-size-audit-strategy-plan.md)

**Documentation**
- Refonte documentation desktop-first + guide utilisateur + docs in-app + section équipe/partenaires (4 plans 2026-04-17/18)

**Site marketing**
- Refonte landing + teaser vidéo hybride (4 plans 2026-04-14)

**UI polish**
- Refonte enrichment tab UX [plan](docs/plans/2026-04-10-refactor-enrichment-tab-ux-redesign-plan.md)
- UI density compaction + rendering smoothness (plans 2026-04-12)

### Bientôt (été 2026)

- **Niamoto Doctor** — diagnostic unifié CLI + GUI [ideation](docs/ideation/2026-04-12-open-ideation.md#1-niamoto-doctor)
- **Starter templates** `niamoto init --template` [ideation](docs/ideation/2026-04-12-open-ideation.md#2-starter-project-templates)
- **Export contract pack** — schema JSON côté export
- **ML model regeneration pipeline** [spec](docs/superpowers/specs/2026-03-27-ml-model-regeneration-design.md)
- Transform parallelization phase 2

### Plus tard (H2 2026 et après)

- **Example & fixture certification pipeline** — docs et fixtures comme contrats exécutables
- **Suggestion explainability layer** — évidences attachées aux suggestions (matching, confiance, override)
- **Transform provenance explorer** — graphe de dépendances import → transform → export
- **Desktop v1.0** — après itérations post-GBIF

### Non prévu

Ces directions ne sont pas envisagées pour Niamoto. Elles ne sont pas des "jamais" absolus, mais elles ne sont pas en roadmap :

- **Hébergement multi-tenant cloud** — Niamoto reste local-first, la distribution desktop est le canal primaire
- **Application mobile native** — les portails générés sont responsive, pas d'app iOS/Android prévue
- **Collaboration temps réel multi-utilisateurs** — hors scope du modèle "un analyste, un instance"
- **Remplacement de DuckDB** — DuckDB reste le moteur central

### Comment contribuer

Pointeurs vers `CONTRIBUTING.md`, `docs/brainstorms/`, `docs/plans/`, `docs/superpowers/specs/`, `docs/ideation/`.

### Dernière mise à jour

Date + note : "cette roadmap est revue à chaque release mineure".

## Contraintes de rédaction

- **Anglais** (aligné avec `README.md`, audience GitHub + jury GBIF international)
- Liens relatifs vers les docs existantes (pas de liens absolus GitHub)
- Pas d'emojis décoratifs sauf l'étoile ⭐ sur le bloc GBIF
- Format Markdown GitHub standard (pas de MyST/RST)
- Fichier court : cible ≈150 lignes

## Hors scope du design

- Pas de refonte de `docs/08-roadmaps/` (reste minimal)
- Pas de modification des brainstorms / plans / specs existants
- Pas d'automatisation de mise à jour (manuel pour l'instant)
- Pas de version française parallèle (les docs internes détaillées restent en français, la roadmap publique est en anglais)

## Critère de succès

Un contributeur externe qui ouvre le repo pour la première fois peut, en 2 minutes de lecture du `ROADMAP.md`, répondre à :
- Que fait Niamoto ?
- Qu'est-ce qui a été livré récemment ?
- Quelle est la priorité court terme (GBIF) ?
- Qu'est-ce qui est prévu après ?
- Qu'est-ce qui n'est pas prévu ?
