---
title: Refonte documentation Niamoto — surface publique desktop-first
type: refactor
date: 2026-04-17
status: active
brainstorm: docs/brainstorms/2026-04-17-doc-refonte-brainstorm.md
---

# Refonte documentation Niamoto — surface publique desktop-first

## Overview

Refonte de la surface publique de Niamoto pour refléter le pivot desktop-first
déjà visible dans le produit, mais encore mal raconté sur GitHub, PyPI et
ReadTheDocs. Le chantier couvre `README.md`, la structure publique de `docs/`,
la configuration Sphinx/ReadTheDocs, les métadonnées PyPI et les assets
visuels.

Cette version corrige le premier plan sur trois points structurants :

- elle part de la **topologie réelle du repo**, pas d'une arborescence cible
  supposée déjà en place ;
- elle **ne renomme pas `docs/09-architecture` ni `docs/10-roadmaps` dans ce
  sprint**, pour éviter du churn de chemins sans gain produit direct ;
- elle **ne pousse pas `docs/06-gui/` en archive en bloc** : les pages encore
  actives sont redistribuées vers `02-user-guide/`, `06-reference/` et
  `09-architecture/`.

## Problem Statement

L'état actuel envoie encore un signal CLI-first alors que l'app desktop est
devenue la porte d'entrée principale :

- `README.md` ouvre avec « A powerful CLI tool » et déroule presque tout le
  parcours via `pip install niamoto` et `niamoto ...`.
- `docs/README.md` affiche encore « Last updated: December 2024 » et documente
  une taxonomie devenue partiellement obsolète.
- `docs/conf.py` utilise déjà `furo`, mais n'exclut pas encore
  `plans/`, `brainstorms/` et `ideation/` de la surface publique.
- `.readthedocs.yaml` cible Python `3.11`, alors que `pyproject.toml` exige
  `>=3.12,<4`.
- `pyproject.toml` a une `description` vide, un seul `keyword`, et un
  classifier `Development Status :: 1 - Planning` qui ne correspond plus à
  l'état du produit.
- `docs/` racine contient encore `modules.rst` et les `niamoto*.rst` générés,
  ce qui pollue la navigation.
- `docs/06-gui/` contient des docs encore valides sur l'architecture GUI et la
  preview API ; les archiver en bloc casserait de la documentation active.

Le problème n'est donc pas seulement rédactionnel. C'est un problème
d'**architecture documentaire publique** : chemins, hiérarchie, index,
redirects, métadonnées et actifs visuels ne racontent plus la même histoire.

## Scope

### In scope

- Réécriture de `README.md`, `docs/README.md` et `docs/index.rst`
- Réorganisation de la surface publique de `docs/`
- Création des nouvelles sections `02-user-guide/`, `03-cli-automation/`,
  `06-reference/` et `99-troubleshooting/`
- Archivage propre des sections devenues legacy via `git mv`
- Mise à jour de `docs/conf.py`, `.readthedocs.yaml`, `docs/requirements.txt`,
  `pyproject.toml` et ajout d'une CI docs
- Production des assets visuels nécessaires au README public

### Out of scope

- Migration de thème Sphinx (`furo` reste en place)
- Refonte du logo ou du branding global
- Réécriture exhaustive de toutes les pages profondes en un seul sprint
- Automatisation des réglages GitHub Settings et ReadTheDocs
- Renumérotation de `09-architecture` en `07-architecture` et de
  `10-roadmaps` en `08-roadmaps`

## Decisions

### Décisions conservées du brainstorm

- Positionnement public explicitement desktop-first
- README court, visuel, orienté personas
- Surface docs organisée par cycle de vie plutôt que par pure taxonomie CLI
- Réutilisation maximale des captures existantes dans `docs/plans/caps/`
- Passe anti-slop manuelle guidée par un `docs/STYLE_GUIDE.md`

### Décisions corrigées par rapport au premier plan

- **Furo conservé** : aucune migration Shibuya dans ce sprint
- **Convention d'entrée unique** : chaque section publique utilise un
  `README.md` comme page d'index ; `docs/index.rst` pointe vers ces `README`
  et non vers des `index.md`/`index.rst` hétérogènes
- **Redirects seulement vers des pages publiques actives** : aucune redirection
  ne doit cibler `docs/_archive/`
- **`docs/06-gui/` éclaté au lieu d'être archivé en bloc**
- **`docs/09-architecture/` et `docs/10-roadmaps/` conservés** pour limiter le
  churn de chemins publics dans ce sprint

## Target Public Tree

La surface publique visée à la fin du sprint est :

```text
docs/
├─ 01-getting-started/
├─ 02-user-guide/
├─ 03-cli-automation/
├─ 04-plugin-development/
├─ 05-ml-detection/
├─ 06-reference/
│  └─ api/
├─ 09-architecture/
├─ 10-roadmaps/
├─ 99-troubleshooting/
├─ _archive/
├─ plans/
├─ brainstorms/
└─ ideation/
```

`plans/`, `brainstorms/` et `ideation/` restent en place dans le repo, mais
sortent de la navigation publique.

## Migration Matrix

### Sections racine

| Source actuelle | Action | Destination publique |
|-----------------|--------|----------------------|
| `docs/01-getting-started/` | conserver et réécrire partiellement | `docs/01-getting-started/` |
| `docs/02-data-pipeline/` | archiver après extraction des pages utiles | `docs/02-user-guide/` + `docs/06-reference/` |
| `docs/03-ml-detection/` | conserver, corriger les liens | `docs/03-ml-detection/` |
| `docs/04-plugin-development/` | conserver, normaliser les index et exemples | `docs/04-plugin-development/` |
| `docs/05-api-reference/` | fusionner | `docs/06-reference/` |
| `docs/06-gui/` | éclater | `docs/02-user-guide/` + `docs/06-reference/` + `docs/09-architecture/` |
| `docs/07-tutorials/` | trier : conserver les cas d'usage utiles, archiver le reste | `docs/02-user-guide/tutorials/` + `docs/_archive/07-tutorials/` |
| `docs/08-configuration/` | fusionner la référence stable, archiver le reste | `docs/06-reference/` + `docs/_archive/08-configuration/` |
| `docs/09-architecture/` | conserver | `docs/09-architecture/` |
| `docs/10-roadmaps/` | conserver | `docs/10-roadmaps/` |
| `docs/11-development/` | archiver après extraction des règles docs utiles | `docs/_archive/11-development/` |
| `docs/12-troubleshooting/` | migrer | `docs/99-troubleshooting/` |
| `docs/modules.rst` + `docs/niamoto*.rst` | déplacer | `docs/06-reference/api/` |

### Split explicite de `docs/06-gui/`

| Fichier source | Action | Destination |
|----------------|--------|-------------|
| `docs/06-gui/operations/import.md` | fusionner | `docs/02-user-guide/import.md` |
| `docs/06-gui/operations/transform.md` | fusionner | `docs/02-user-guide/transform.md` |
| `docs/06-gui/operations/export.md` | fusionner | `docs/02-user-guide/export.md` |
| `docs/06-gui/operations/desktop-smoke-tests.md` | conserver comme doc opératoire | `docs/99-troubleshooting/desktop-smoke-tests.md` ou `docs/03-cli-automation/desktop-smoke-tests.md` après audit |
| `docs/06-gui/architecture/overview.md` | déplacer | `docs/09-architecture/gui-overview.md` |
| `docs/06-gui/architecture/backend-frontend-runtime.md` | déplacer | `docs/09-architecture/gui-runtime.md` |
| `docs/06-gui/architecture/preview-system.md` | déplacer | `docs/09-architecture/gui-preview-system.md` |
| `docs/06-gui/reference/preview-api.md` | déplacer | `docs/06-reference/gui-preview-api.md` |
| `docs/06-gui/reference/transform-plugins.md` | déplacer | `docs/06-reference/transform-plugins.md` |
| `docs/06-gui/reference/widgets-and-transform-workflow.md` | déplacer | `docs/06-reference/widgets-and-transform-workflow.md` |

Le point important est que **les contenus GUI actifs restent publics**, même si
le dossier `06-gui/` lui-même devient legacy.

## Public URL Policy

Les redirects doivent être définis **après** la matrice finale de migration,
avec cette règle simple :

- ancienne URL publique importante -> nouvelle page publique active ;
- aucune redirect -> `docs/_archive/` ;
- le contenu uniquement historique reste accessible depuis git et via des
  liens legacy explicites, mais n'est pas une cible de navigation publique.

Exemples de redirections attendues :

- `02-data-pipeline/index` -> `02-user-guide/README.html`
- `05-api-reference/index` -> `06-reference/README.html`
- `05-api-reference/cli-commands` -> `06-reference/cli-commands.html`
- `06-gui/index` -> `02-user-guide/README.html`
- `06-gui/reference/preview-api` -> `06-reference/gui-preview-api.html`
- `12-troubleshooting/common-issues` -> `99-troubleshooting/common-issues.html`

## Implementation Phases

### Phase 1 — Fondations et contrat de chemins

**Objectif** : stabiliser la structure cible et le contrat public avant toute
réécriture lourde.

**Fichiers et répertoires concernés :**

- `docs/conf.py`
- `.readthedocs.yaml`
- `docs/requirements.txt`
- `pyproject.toml`
- `.github/workflows/docs.yml`
- `CONTRIBUTING.md`
- `docs/_archive/`
- `docs/02-user-guide/`
- `docs/03-cli-automation/`
- `docs/06-reference/api/`
- `docs/99-troubleshooting/`

**Travail attendu :**

- auditer les liens croisés vers les anciennes sections publiques ;
- créer la nouvelle arborescence cible ;
- préparer le déplacement des `.rst` autogénérés vers `docs/06-reference/api/` ;
- mettre à jour `docs/conf.py` :
  - `exclude_patterns` pour `plans/`, `brainstorms/`, `ideation/`
  - extensions docs utiles si retenues
  - redirects uniquement vers des pages publiques actives ;
- aligner `.readthedocs.yaml` sur Python `3.12` ;
- ajouter une CI docs sur PR pour le build Sphinx ;
- mettre à jour `CONTRIBUTING.md` pour refléter la nouvelle logique docs.

**Critères d'acceptation :**

- `sphinx-build -W -b html docs docs/_build` passe localement
- la CI docs existe et cible au minimum `docs/**`, `README.md`,
  `pyproject.toml`, `.readthedocs.yaml`, `CONTRIBUTING.md`
- `docs/` racine ne contient plus `modules.rst` ni les `niamoto*.rst`
- un mapping de redirects existe pour les anciennes pages publiques critiques

### Phase 2 — Surface publique racine

**Objectif** : faire raconter la même histoire par GitHub, RTD et PyPI.

**Fichiers concernés :**

- `README.md`
- `docs/README.md`
- `docs/index.rst`
- `docs/STYLE_GUIDE.md`
- `pyproject.toml`

**Travail attendu :**

- réécrire `README.md` autour d'un positionnement desktop-first ;
- conserver les badges utiles, mais sortir de la logique purement CLI ;
- structurer le README par personas et par cycle de vie produit ;
- réécrire `docs/README.md` comme porte d'entrée interne cohérente avec la
  surface publique ;
- réécrire `docs/index.rst` pour pointer vers les `README.md` des sections
  publiques ;
- créer `docs/STYLE_GUIDE.md` avec règles de voix, lexique banni, lexique
  préféré, règles de style et rappel sur les diacritiques français ;
- corriger `pyproject.toml` :
  - `description` non vide
  - `keywords` enrichis
  - classifier de maturité réaliste
  - `project.urls.Documentation` vers RTD
  - `project.urls.Changelog` et `project.urls.Issues` si absents.

**Critères d'acceptation :**

- `README.md`, `docs/README.md` et `docs/index.rst` sont alignés sur la même
  hiérarchie publique
- `README.md` ne présente plus Niamoto comme un produit principalement CLI
- `docs/STYLE_GUIDE.md` existe et sert de référence explicite
- `pyproject.toml` expose des métadonnées publiques cohérentes

### Phase 3 — Migration de contenu par section

**Objectif** : remplir la nouvelle topo sans trous publics et sans archiver des
docs encore actives.

**Unités de travail :**

1. **`docs/01-getting-started/`**
   - conserver le dossier ;
   - réécrire `README.md` selon le pattern `03-ml-detection` ;
   - garder `installation.md`, `first-project.md`/`quickstart.md`,
     `concepts.md` avec un récit desktop-first.

2. **`docs/02-user-guide/`**
   - créer `README.md` ;
   - créer `import.md`, `transform.md`, `preview.md`, `export.md` ;
   - y fusionner les contenus pertinents issus de `02-data-pipeline/`,
     `06-gui/operations/` et des anciens tutoriels utiles ;
   - créer éventuellement `tutorials/` pour `biodiversity-site.md` et
     `forest-plot-analysis.md` si ces guides restent pertinents.

3. **`docs/03-cli-automation/`**
   - créer `README.md` ;
   - cadrer la CLI comme surface avancée pour automation, CI, scripts et
     debugging ;
   - y regrouper recettes CI/CD, usage shell et docs opératoires si elles ne
     relèvent pas de `99-troubleshooting/`.

4. **`docs/04-plugin-development/`**
   - conserver ;
   - réécrire l'index au pattern cible ;
   - normaliser les liens et exemples ;
   - rapatrier `docs/examples/plugins/` si cela améliore la lisibilité.

5. **`docs/05-ml-detection/`**
   - conserver le contenu ;
   - corriger les liens internes qui pointent encore vers
     `02-data-pipeline/`, `05-api-reference/` et `08-configuration/`.

6. **`docs/06-reference/`**
   - créer `README.md` ;
   - y fusionner `05-api-reference/` ;
   - y accueillir `api/`, `cli-commands.md`, la référence GUI stable et les
     schémas/configurations stables.

7. **`docs/09-architecture/`**
   - conserver le chemin ;
   - réécrire l'index selon le pattern cible ;
   - intégrer la documentation d'architecture GUI encore valide issue de
     `06-gui/architecture/`.

8. **`docs/10-roadmaps/`**
   - conserver le chemin ;
   - ajouter un `README.md` qui cadre le statut des plans et des sous-dossiers
     `gui/` / `gui-finalization/`.

9. **`docs/99-troubleshooting/`**
   - créer `README.md` ;
   - migrer `common-issues.md` et les problèmes desktop réellement fréquents.

10. **Archives**
   - déplacer via `git mv` les sections legacy dans `docs/_archive/` ;
   - marquer tout lien vers archive comme `legacy`.

**Critères d'acceptation :**

- chaque section publique possède un `README.md`
- aucune page publique active ne dépend d'un chemin archivé non signalé
- les pages GUI encore valides restent publiques après la migration
- `docs/03-ml-detection/README.md` ne contient plus de liens morts vers
  l'ancienne topo

### Phase 4 — Assets visuels

**Objectif** : fournir les assets minimaux nécessaires au README public sans
  dépendre d'une recapture complète.

**Fichiers concernés :**

- `assets/screenshots/hero-split.png`
- `assets/screenshots/workflow.gif`
- `assets/social-preview-1280x640.png`
- `assets/_archive/screenshots/`
- `scripts/dev/build_readme_hero.sh` si un script dédié est utile

**Travail attendu :**

- composer un hero split-view à partir des captures existantes ;
- produire un GIF de workflow court si la qualité reste acceptable ;
- produire une social preview GitHub ;
- archiver les screenshots portail obsolètes (`taxon-index.png`,
  `taxon-detail.png`) ;
- ne recapturer que si les assets existants ne suffisent pas.

**Critères d'acceptation :**

- hero split disponible et exploitable dans `README.md`
- GIF workflow disponible ou explicitement remplacé par un asset statique si la
  taille/qualité le justifie
- social preview prête pour GitHub Settings
- les anciens screenshots obsolètes sont archivés

### Phase 5 — Validation finale et suivi manuel

**Objectif** : fermer le sprint avec une surface cohérente et des actions
manuelles clairement séparées.

**Vérifications dans le repo :**

- build Sphinx sans warning ;
- link check sur `README.md`, `docs/README.md` et les pages publiques ;
- spot-check des redirects importants ;
- revue du diff complet contre le style guide ;
- mise à jour de `CHANGELOG.md` si la politique de release l'exige.

**Actions manuelles hors repo :**

- lancer un build manuel ReadTheDocs ;
- mettre à jour GitHub Settings :
  - description
  - website URL
  - topics
  - social preview ;
- vérifier l'affichage PyPI à la prochaine release.

**Critères d'acceptation :**

- tout ce qui est vérifiable depuis le repo est validé avant merge ;
- les actions manuelles restantes sont listées dans le PR comme checklist ;
- aucune action manuelle externe n'est confondue avec un critère de build local.

## Verification Matrix

### Vérifiable dans le repo

- `sphinx-build -W -b html docs docs/_build`
- CI docs verte
- absence de `niamoto*.rst` et `modules.rst` à la racine de `docs/`
- liens internes critiques valides
- cohérence `README.md` / `docs/index.rst` / `docs/README.md`

### Vérifiable manuellement hors repo

- build ReadTheDocs vert
- social preview GitHub correcte
- description/topics GitHub alignés
- rendu PyPI correct à la prochaine publication

## Risks & Mitigations

| Risque | Niveau | Mitigation |
|--------|--------|------------|
| Redirects faux ou incomplets | Élevé | Construire la table de redirects après le mapping réel des pages, puis tester les URLs prioritaires |
| Archivage accidentel de docs GUI encore actives | Élevé | Utiliser la matrice de split `06-gui/` comme source de vérité, pas un `git mv` global |
| Duplication entre `03-cli-automation/` et `06-reference/` | Moyen | Une seule source de vérité par sujet ; `03-cli-automation/` reste narratif, `06-reference/` reste canonique |
| README plus joli mais incohérent avec la doc | Moyen | Réécrire `README.md`, `docs/README.md` et `docs/index.rst` dans la même phase |
| Screenshots vite obsolètes | Moyen | Réutiliser les captures d'avril 2026 et limiter les nouvelles captures au strict nécessaire |
| Actions GitHub/RTD oubliées après merge | Faible | Checklist explicite dans le PR et dans la phase finale |

## Alternative Approaches Rejected

| Approche | Pourquoi rejetée |
|----------|------------------|
| Renommer immédiatement `09-architecture` en `07-architecture` et `10-roadmaps` en `08-roadmaps` | Churn de chemins trop élevé pour ce sprint ; bénéfice surtout cosmétique |
| Archiver `docs/06-gui/` en bloc | Perte immédiate de docs GUI encore actives |
| Rediriger les anciennes URLs vers `_archive/` | Contradiction avec une surface publique propre ; l'archive n'est pas une destination produit |
| Migrer Furo vers Shibuya | YAGNI dans ce sprint |
| Réécriture exhaustive de toutes les pages profondes | Scope trop large ; mieux vaut nettoyer la surface publique d'abord |

## Final Acceptance Criteria

- [ ] La hiérarchie publique finale est cohérente avec la topologie réelle du repo
- [ ] `README.md` raconte Niamoto comme produit desktop-first
- [ ] `docs/index.rst` pointe vers des `README.md` publics homogènes
- [ ] `docs/06-gui/` n'est pas archivé en bloc ; ses pages actives sont remappées
- [ ] `docs/03-ml-detection/README.md` ne pointe plus vers l'ancienne topo
- [ ] Les redirects publics ne ciblent jamais `_archive/`
- [ ] Les vérifications repo sont toutes automatisables ou exécutables avant merge
- [ ] Les actions manuelles GitHub/RTD/PyPI sont séparées dans une checklist de suivi

## References

- Brainstorm source : `docs/brainstorms/2026-04-17-doc-refonte-brainstorm.md`
- Pattern d'index : `docs/03-ml-detection/README.md`
- Configuration Sphinx : `docs/conf.py`
- Configuration RTD : `.readthedocs.yaml`
- Métadonnées package : `pyproject.toml`
- Surface docs actuelle : `docs/README.md`, `docs/index.rst`
- Docs GUI actives à redistribuer : `docs/06-gui/`
- Roadmaps et architecture conservées : `docs/09-architecture/`,
  `docs/10-roadmaps/`
