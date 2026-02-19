---
title: Publication v1 — App Desktop Fonctionnelle
type: feat
date: 2026-02-19
deadline: 2026-02-28
---

# Publication v1 — App Desktop Fonctionnelle

## Overview

Niamoto doit être publié d'ici fin février 2026 comme une application desktop fonctionnelle permettant à un utilisateur d'installer l'app (macOS/Windows/Linux), d'importer ses données, de configurer ses traitements, de les exécuter, et de publier un site statique sur un hébergement de son choix (Cloudflare, Netlify, hébergement perso).

**État actuel** : La chaîne CLI est fonctionnelle. L'interface GUI est largement implémentée (60+ pages React, 19 routers FastAPI). L'état de travail actuel contient **56 fichiers modifiés** (72 entrées `git status --short`) sur `feature/enhanced-user-experience`, incluant des breaking changes qui restent à valider manuellement côté métier/E2E.

**Deadline** : 28 février 2026 (~9 jours)

## Problem Statement

### Ce qui fonctionne ✅
- Pipeline CLI complet : Import → Transform → Export
- GUI : 60+ pages React, 19 routers FastAPI opérationnels
- Phase 1 (Transform/Export GUI) : 86 tests validés
- Phase 2 (Offline support) : commité et implémenté
- Suite GUI API actuelle verte : `uv run pytest tests/gui/api` → **147 tests passés**
- Pipeline CI/CD : builds cross-platform configurés
- Documentation : 12 sections, 60+ fichiers

### Ce qui est déjà sécurisé pendant cette session ✅
- Durcissement SQL appliqué sur les routers/services critiques GUI (queries paramétrées + identifiants quotés)
- `table_resolver` centralisé et propagé sur plusieurs routeurs (templates/stats/enrichment/recipes/sources/config/etc.)
- `transform_config_models` déplacé dans `niamoto.common` avec compatibilité contrôlée
- CORS resserré (suppression du wildcard permissif)
- Cache `has_table()` côté `Database` pour réduire la pression catalog/inspector
- Data Explorer sécurisé avec parseur `WHERE` restreint et testé (`AND/OR`, parenthèses, `IN/NOT IN`, `IS NULL`, `BETWEEN/NOT BETWEEN`)
- Direction architecture confirmée : **configuration over code** (suppression progressive des hypothèses hardcodées sur noms de tables/colonnes/entités)

### Ce qui n'est pas validé ⚠️
- **56 fichiers modifiés non commités** avec breaking changes majeurs :
  - `table_resolver` centralisé (nouveau module)
  - `transform_config_models` Pydantic strict (nouveau module)
  - Format `transform.yml` : dict → liste stricte
  - Matching configs : case-sensitive strict
  - Migration npm → pnpm
  - Types TypeScript : `EntityKind.flat` → `EntityKind.generic`
- **Interface de configuration des pages statiques** : non validée manuellement
- **Lancement et gestion des traitements dans l'app** : non validé bout en bout
- **App Tauri** : structure en place mais parcours utilisateur non testé
- **Builds cross-platform** : workflow CI/CD non testé avec les changements récents

### Ce qui manque 🔴
- Validation manuelle complète du parcours utilisateur
- Deploy multi-plateforme (actuellement Cloudflare uniquement)
- Tests d'installation sur les 3 OS
- Release process bout en bout
- Décision Go/No-Go formalisée avant tag final

---

## Proposed Solution

### Approche : Stabilisation progressive en 4 phases

La stratégie est de **stabiliser par couches** : d'abord valider le code non commité, puis le parcours utilisateur, puis le build/deploy, puis la release.

**Priorité absolue** : Un utilisateur peut installer l'app, importer des données CSV, configurer des transformations via l'interface, lancer les traitements, et publier un site statique.

---

## Technical Approach

### Phase 1 : Triage & Validation du Code Non Commité (Jours 1-2)

**Objectif** : Valider ou corriger tout le code modifié, commiter en chunks logiques.

#### 1.1 Exécuter les tests existants

```bash
# Backend Python
uv run pytest tests/ -v --tb=short

# Frontend TypeScript
cd src/niamoto/gui/ui && pnpm install && pnpm run build && pnpm test
```

- [ ] Tous les tests Python passent (`tests/core/`, `tests/gui/`, `tests/e2e/`)
- [ ] Le build frontend React réussit sans erreur
- [ ] Les tests TypeScript passent (config generator, validator)

**Déjà fait (session courante)** :
- `uv run pytest tests/gui/api` : 147 passed
- Nouveaux tests ciblés ajoutés/validés (`test_data_explorer.py`, `test_stats.py`, tests routers/templates)

#### 1.2 Valider les breaking changes

| Breaking Change | Fichier(s) | Validation | Action |
|---|---|---|---|
| `_filter_configs()` strict | `src/niamoto/core/services/transformer.py` | Tester avec instance test-instance/niamoto-test/ | Vérifier que les configs existantes matchent exactement |
| Format `transform.yml` dict → liste | `src/niamoto/gui/api/routers/templates.py` | Charger les configs existantes | Valider le fallback minimal transitoire, puis converger vers liste stricte |
| `EntityKind.flat` → `EntityKind.generic` | `src/niamoto/gui/ui/src/lib/config/import-config-types.ts` | Vérifier les dropdowns UI | Tester le formulaire d'import |
| `npm` → `pnpm` | `package.json`, scripts | `pnpm install && pnpm run build` | Vérifier que rien ne casse |
| `table_resolver` centralisé | `src/niamoto/common/table_resolver.py` | Tester résolution tables avec données réelles | Vérifier fallback registry + conventions |
| Cache `table_names` (2s TTL) | `src/niamoto/common/database.py` | Stress test import+query | Vérifier invalidation |

#### 1.2 bis Verrouiller le contrat de configuration v1

- [ ] Définir un **schéma v1 unique** pour `import.yml` et `transform.yml` (format canonique UI-first)
- [ ] Interdire les alias implicites et comportements ambigus (noms/stratégies legacy) dans les chemins critiques
- [ ] Ajouter une validation stricte pré-exécution (backend) + feedback explicite dans l'UI
- [ ] Documenter le format cible dans un guide unique (source de vérité)

#### 1.3 Commiter en chunks logiques

```
Commit 1: feat(common): table resolver centralisé et transform config models
  - src/niamoto/common/table_resolver.py
  - src/niamoto/common/transform_config_models.py
  - src/niamoto/core/services/transform_config_models.py
  - src/niamoto/common/config.py
  - src/niamoto/common/database.py

Commit 2: refactor(api): migration routers vers table resolver générique
  - src/niamoto/gui/api/routers/*.py (10 fichiers)
  - src/niamoto/gui/api/services/**/*.py

Commit 3: refactor(ui): types et config generator mis à jour
  - src/niamoto/gui/ui/src/lib/config/*.ts
  - src/niamoto/gui/ui/src/components/**/*.tsx
  - src/niamoto/gui/ui/src/hooks/*.ts

Commit 4: refactor(build): migration npm → pnpm
  - src/niamoto/gui/ui/package.json
  - src/niamoto/gui/ui/pnpm-lock.yaml
  - scripts/dev/*.sh, scripts/build/*.sh, build_scripts/*

Commit 5: test: nouveaux tests e2e et GUI
  - tests/e2e/test_reference_reproduction.py
  - tests/gui/api/routers/test_data_explorer.py
  - tests/gui/api/routers/test_stats.py
  - tests/gui/api/services/

Commit 6: docs: mise à jour roadmaps et architecture
  - docs/**/*.md
  - .github/RELEASE.md
```

---

### Phase 2 : Validation du Parcours Utilisateur (Jours 2-4)

**Objectif** : Tester manuellement le parcours complet de bout en bout.

#### 2.1 Scénario de test principal

Un utilisateur part de zéro :

```
1. Installation → Premier lancement → WelcomeScreen
2. Création/Sélection projet → ProjectSwitcher
3. Import de données CSV → Upload wizard → Auto-config → Exécution
4. Visualisation des données importées → Data Explorer
5. Configuration des transformations → GroupPanel → Suggestions → Formulaires
6. Lancement des transformations → Progress tracking → Résultats
7. Configuration du site statique → SiteBuilder → Pages → Navigation
8. Export/Build du site → BuildPhase → Preview
9. Déploiement → DeployPhase → URL finale
```

#### 2.2 Tests par module

**Import (`/sources`)** :
- [ ] Upload fichier CSV → détection auto colonnes
- [ ] Configuration entité (dataset/reference)
- [ ] Exécution import → barre de progression → succès
- [ ] Dashboard post-import → statistiques affichées
- [ ] Import de référence hiérarchique (taxonomie)

**Transform (`/groups/:name`)** :
- [ ] Affichage des groupes configurés
- [ ] Onglets Sources/Content/Index fonctionnels
- [ ] Suggestions de widgets pertinentes
- [ ] Ajout/suppression de widget via formulaire
- [ ] Sauvegarde config → round-trip `transform.yml`
- [ ] Lancement transformation → progression → résultats
- [ ] Vérification que les résultats sont cohérents

**Parité projet de référence (anti-régression métier)** :
- [ ] Exécuter le scénario `niamoto-test` (piloté UI) puis comparer la sortie avec `niamoto-nc` (référence)
- [ ] Vérifier au minimum : taxons, plots, shapes (widgets + transformations associées)
- [ ] Produire un rapport de diff simple (OK/KO par domaine) archivable en artefact CI

**Site Builder (`/site/pages`)** :
- [ ] Arborescence de pages visible
- [ ] Éditeur Markdown fonctionnel
- [ ] Configuration navigation
- [ ] Templates multilingues (FR/EN)
- [ ] Preview live du site

**Export/Publish (`/publish/*`)** :
- [ ] Build du site → génération HTML statique
- [ ] Preview locale du site généré
- [ ] Deploy Cloudflare (si credentials disponibles)
- [ ] Vérifier que les graphiques Plotly fonctionnent offline
- [ ] Vérifier les cartes (Leaflet) avec fallback offline

**App Desktop** :
- [ ] Premier lancement → WelcomeScreen cohérent
- [ ] Sélection dossier projet via file picker natif
- [ ] Persistance projet récent
- [ ] Indicateur réseau (online/offline)
- [ ] Fonctionnement complet sans connexion internet

#### 2.3 Bugs et corrections

Chaque bug trouvé doit être :
1. Documenté (description + reproduction)
2. Corrigé immédiatement si bloquant
3. Noté pour correction ultérieure si cosmétique

---

### Phase 3 : Build, Test d'Installation et Deploy (Jours 5-7)

**Objectif** : S'assurer que l'app peut être installée et fonctionne sur les 3 OS.

#### 3.1 Build local

```bash
# 1. Build React frontend
cd src/niamoto/gui/ui && pnpm install && pnpm run build

# 2. Build PyInstaller binaire
cd build_scripts && bash build_desktop.sh

# 3. Test du binaire localement
./dist/niamoto --version
./dist/niamoto gui  # Doit lancer FastAPI + ouvrir navigateur/Tauri
```

- [ ] Build React réussit
- [ ] Build PyInstaller réussit sur macOS
- [ ] Binaire fonctionne (lancement, import, transform, export)
- [ ] Taille du binaire raisonnable (~50-60 MB compressé)

#### 3.2 Test CI/CD

```bash
# Créer un tag de test (pré-release)
uv run bump2version patch --dry-run  # Vérifier le bump
uv run bump2version patch            # 0.7.5 → 0.7.6 (ou 0.8.0 si majeur)
git tag v0.8.0-rc1
git push origin v0.8.0-rc1
```

- [ ] GitHub Actions se déclenche sur le tag
- [ ] Build macOS arm64 réussit
- [ ] Build Linux x86_64 réussit
- [ ] Build Windows x86_64 réussit
- [ ] Release GitHub créée avec les 3 artefacts
- [ ] Artefacts téléchargeables et fonctionnels

#### 3.3 Test d'installation sur chaque OS

**macOS** :
- [ ] Télécharger l'artefact
- [ ] Extraire et lancer
- [ ] Gatekeeper/signature : documenter le processus
- [ ] Parcours complet fonctionne

**Linux** (VM ou machine de test) :
- [ ] Télécharger l'artefact
- [ ] Extraire et lancer
- [ ] Permissions et dépendances OK
- [ ] Parcours complet fonctionne

**Windows** (VM ou machine de test) :
- [ ] Télécharger l'artefact
- [ ] Extraire et lancer
- [ ] Antivirus/SmartScreen : documenter le processus
- [ ] Parcours complet fonctionne

#### 3.4 Deploy multi-plateforme du site statique

**Actuellement implémenté** : Cloudflare uniquement

**À valider/documenter** :
- [ ] Export en local (`niamoto export`) → dossier `output/` avec HTML/CSS/JS
- [ ] Upload manuel sur Netlify (drag & drop) → fonctionne
- [ ] Upload manuel sur hébergement perso (FTP/SSH) → fonctionne
- [ ] Documentation du processus pour chaque cible

**Nice to have (si temps disponible)** :
- [ ] Intégration deploy Netlify dans l'interface
- [ ] Intégration deploy GitHub Pages dans l'interface

---

### Phase 4 : Release et Communication (Jours 8-9)

**Objectif** : Publication officielle.

#### 4.1 Préparation release

- [ ] CHANGELOG mis à jour avec tous les changements depuis dernière release
- [ ] Version bump finale (`uv run bump2version minor` → 0.8.0)
- [ ] README vérifié (installation, quickstart, screenshots)
- [ ] Documentation en ligne à jour (ReadTheDocs rebuild)

#### 4.2 Publication

```bash
# 1. Commit final
git add -A && git commit -m "release: v0.8.0"

# 2. Tag
git tag v0.8.0

# 3. Push
git push origin feature/enhanced-user-experience
git push origin v0.8.0

# 4. Merge dans main (après CI verte)
git checkout main && git merge feature/enhanced-user-experience
git push origin main

# 5. PyPI
bash scripts/publish.sh

# 6. GitHub Release (automatique via tag)
```

- [ ] CI/CD builds passent
- [ ] PyPI publication réussie
- [ ] GitHub Release avec notes et binaires
- [ ] Site documentation à jour

#### 4.3 Documentation utilisateur minimale

- [ ] Guide d'installation (macOS/Windows/Linux)
- [ ] Guide de démarrage rapide (premier projet en 5 minutes)
- [ ] FAQ / Troubleshooting courant

---

## Acceptance Criteria

### Functional Requirements

- [ ] Un utilisateur peut installer le binaire sur macOS, Windows et Linux
- [ ] Le premier lancement affiche un écran d'accueil cohérent
- [ ] L'import de données CSV fonctionne de bout en bout
- [ ] La configuration des transformations via l'interface est fonctionnelle
- [ ] Le lancement et suivi des traitements (import/transform/export) fonctionne
- [ ] La configuration du site statique est utilisable
- [ ] Le site statique généré fonctionne correctement (graphiques, cartes, navigation)
- [ ] Le déploiement du site est documenté pour au moins 2 plateformes

### Non-Functional Requirements

- [ ] Le binaire ne dépasse pas 80 MB compressé
- [ ] L'app fonctionne offline (sauf enrichissement et deploy)
- [ ] Le temps de lancement est < 10 secondes
- [ ] Les traitements affichent leur progression

### Quality Gates

- [ ] Tous les tests Python passent
- [ ] Le build React réussit sans warning critique
- [ ] Le build PyInstaller réussit sur les 3 OS
- [ ] Parcours utilisateur complet testé manuellement
- [ ] Aucun hardcode métier bloquant détecté (noms d'entités/tables/colonnes dépendants d'une instance spécifique)
- [ ] Gate Go/No-Go validé sur scénario de référence (`niamoto-test` vs `niamoto-nc`) :
  - taxons ✅
  - plots ✅
  - shapes ✅
  - publication/export ✅

---

## Dependencies & Prerequisites

| Dépendance | Statut | Impact |
|---|---|---|
| Code non commité validé | 🟠 En cours (API backend largement validée) | Bloquant Phase 1 |
| pnpm installé | ✅ OK | Build frontend |
| Instance de test (`test-instance/`) | ✅ Disponible | Validation manuelle |
| Accès GitHub Actions | ✅ OK | CI/CD |
| Machine Windows pour test | ⚠️ À vérifier | Test installation |
| Machine Linux pour test | ⚠️ À vérifier | Test installation |
| Credentials Cloudflare | ⚠️ À vérifier | Test deploy |

---

## Risk Analysis & Mitigation

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Dérive "instance-specific" (hardcodes métier) | Moyenne | Élevé | Revue ciblée config-over-code + tests de parité référence/test |
| Breaking changes cassent des configs existantes | Moyenne | Élevé | Tester avec instance test, verrouiller format cible UI (liste stricte) |
| Régression sécurité SQL sur endpoints restants | Faible à moyenne | Élevé | Checklist SQL + revue ciblée + tests query API |
| Build CI/CD échoue sur un OS | Moyenne | Élevé | Tester localement d'abord, avoir un plan B (build manuel) |
| Parcours utilisateur a des bugs bloquants | Élevée | Élevé | Commencer la validation manuelle immédiatement |
| Manque de temps pour les 3 OS | Moyenne | Moyen | Prioriser macOS (principal), Linux, puis Windows |
| Deploy multi-plateforme trop complexe | Faible | Moyen | Documenter l'export local + upload manuel comme MVP |
| Tauri app pas assez stable | Moyenne | Élevé | Fallback : publier en mode web (navigateur) si Tauri bloque |

---

## Planning Jour par Jour

| Jour | Date | Phase | Activités |
|---|---|---|---|
| **J1** | 19/02 | Phase 1 | Tests auto, triage breaking changes |
| **J2** | 20/02 | Phase 1-2 | Commits, début validation manuelle |
| **J3** | 21/02 | Phase 2 | Validation parcours import → transform |
| **J4** | 22/02 | Phase 2 | Validation parcours site builder → publish, corrections |
| **J5** | 24/02 | Phase 3 | Build local, test PyInstaller |
| **J6** | 25/02 | Phase 3 | Test CI/CD, builds cross-platform |
| **J7** | 26/02 | Phase 3 | Tests d'installation, deploy multi-plateforme |
| **J8** | 27/02 | Phase 4 | CHANGELOG, README, docs, version bump |
| **J9** | 28/02 | Phase 4 | Publication finale, release |

---

## Future Considerations

Ces éléments sont explicitement **hors scope** pour cette release mais documentés pour v0.9.0+ :

- Jobs persistants (SQLite jobs table) — évite perte d'état au redémarrage
- Deploy intégré Netlify/GitHub Pages — actuellement Cloudflare uniquement
- Centre de notifications centralisé
- Tests e2e frontend (Playwright)
- Auto-update mechanism pour l'app desktop
- `transform_chain` interface dédiée
- System tray integration

---

## Documentation Plan

| Document | Action | Priorité |
|---|---|---|
| Guide d'installation (3 OS) | Créer | P0 |
| Guide démarrage rapide | Mettre à jour `docs/01-getting-started/` | P0 |
| CHANGELOG | Mettre à jour | P0 |
| README | Vérifier screenshots et quickstart | P1 |
| Release notes GitHub | Rédiger | P1 |
| FAQ/Troubleshooting | Enrichir si bugs trouvés | P2 |

---

## References & Research

### Internal References
- Plans précédents : `docs/plans/2026-02-04-feat-finalize-transform-export-gui-plan.md`
- Architecture desktop : `docs/10-roadmaps/gui/DESKTOP_APP.md`
- Process release : `.github/RELEASE.md`
- Instance test : `test-instance/niamoto-test/`
- Build scripts : `build_scripts/niamoto.spec`, `build_scripts/build_desktop.sh`
- CI/CD : `.github/workflows/build-binaries.yml`

### État du code non commité
- 56 fichiers modifiés sur `feature/enhanced-user-experience` (72 entrées `git status --short`)
- 2.762 insertions / 15.681 suppressions
- Modules clés ajoutés : `table_resolver.py`, `transform_config_models.py`
- Migration npm → pnpm effectuée
- Suite GUI API verte : 147 tests passés
