# Checklist Opératoire J1/J2 — Stabilisation v1

Date de référence : 19/02/2026 (J1) et 20/02/2026 (J2)

## Objectif global

Sécuriser la chaîne complète **import → transform → publish** dans l'UI, en restant strictement sur le principe **configuration over code**, puis obtenir un Go/No-Go factuel.

## Périmètre de test

- Projet de référence : `/Users/julienbarbe/Dev/clients/niamoto/test-instance/niamoto-nc`
- Projet test UI : `/Users/julienbarbe/Dev/clients/niamoto/test-instance/niamoto-test`
- Cible fonctionnelle minimale : `taxons`, `plots`, `shapes`, `publication/export`

## Owners proposés

- Backend/API : CTO/Lead backend
- UI/UX + flow utilisateur : Lead frontend
- QA/parité fonctionnelle : Product + QA
- Release/CI : DevOps

## J1 — 19/02/2026 (stabilisation technique)

### 1) Baseline et hygiène repo

- [ ] Capturer l'état git courant (fichiers modifiés, non suivis, stats)
- [ ] Ajouter le plan v1 et la checklist au suivi git si validés
- [ ] Geler les changements non prioritaires jusqu'au Go/No-Go

Commandes :

```bash
cd /Users/julienbarbe/Dev/clients/niamoto
git status --short
git diff --shortstat
```

### 2) Validation backend ciblée

- [ ] Rejouer la suite API GUI
- [ ] Rejouer les tests sensibles SQL et resolver
- [ ] Vérifier absence de hardcode métier bloquant dans les routes critiques

Commandes :

```bash
cd /Users/julienbarbe/Dev/clients/niamoto
uv run pytest tests/gui/api -q
uv run pytest tests/core -k "resolver or transform or config" -q
```

### 3) Contrat de configuration v1

- [ ] Verrouiller un format canonique UI-first pour `import.yml`
- [ ] Verrouiller un format canonique UI-first pour `transform.yml`
- [ ] Interdire les alias implicites dans les chemins critiques
- [ ] S'assurer que les erreurs de validation sont explicites côté UI

### 4) Build frontend

- [ ] Installer les dépendances pnpm
- [ ] Build UI sans erreur bloquante

Commandes :

```bash
cd /Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui
pnpm install
pnpm run build
```

### Exit criteria J1

- [ ] Tests API GUI verts
- [ ] Build UI vert
- [ ] Contrat de config v1 écrit et validé en équipe
- [ ] Aucun blocant P1/P2 ouvert sur SQL/hardcode/config

## J2 — 20/02/2026 (validation produit/E2E)

### 1) Scénario E2E piloté UI

- [ ] Importer les sources nécessaires dans `niamoto-test`
- [ ] Configurer et exécuter transformations `taxons`
- [ ] Configurer et exécuter transformations `plots`
- [ ] Configurer et exécuter transformations `shapes`
- [ ] Exécuter `publication/export` depuis l'UI

### 2) Parité avec le projet de référence

- [ ] Comparer les sorties `niamoto-test` vs `niamoto-nc` pour taxons
- [ ] Comparer les sorties `niamoto-test` vs `niamoto-nc` pour plots
- [ ] Comparer les sorties `niamoto-test` vs `niamoto-nc` pour shapes
- [ ] Produire un rapport simple OK/KO par domaine

### 3) Vérification "configuration over code"

- [ ] Changer au moins un nom d'entité/colonne dans la config de test
- [ ] Vérifier que le flow continue de fonctionner sans patch code
- [ ] Refuser toute correction qui ajoute des noms métier hardcodés

### 4) Publication locale et smoke check

- [ ] Générer le site statique
- [ ] Vérifier widgets et pages générées
- [ ] Vérifier rendu offline des éléments attendus

### Exit criteria J2 (Go/No-Go v1)

- [ ] `taxons` validé
- [ ] `plots` validé
- [ ] `shapes` validé
- [ ] `publication/export` validé
- [ ] Zéro régression critique SQL/sécurité/config-over-code
- [ ] Décision Go/No-Go actée

## Artefacts attendus fin J2

- Rapport de parité (`niamoto-test` vs `niamoto-nc`)
- Liste des écarts restants classés P1/P2/P3
- Décision Go/No-Go signée (Go, Go with conditions, No-Go)
