---
title: "fix: Tauri onboarding pre-release polish"
type: fix
date: 2026-04-02
brainstorm: docs/brainstorms/2026-04-02-tauri-onboarding-audit-brainstorm.md
---

# fix: Tauri onboarding pre-release polish

## Overview

Corrections ciblées du parcours desktop Tauri avant release. L'objectif n'est pas une refonte de l'onboarding, mais un durcissement du boot desktop et un polish UX minimal pour que les états invalides deviennent explicites, récupérables, et cohérents entre le WelcomeScreen et le ProjectSwitcher.

Le scope reste volontairement petit:

- sécuriser le démarrage quand `desktop-config.json` pointe vers un projet supprimé
- supprimer les projets fantômes cliquables
- unifier la vérification de `reload-project`
- améliorer la lisibilité de l'onboarding quand aucun projet récent valide n'est disponible

## Problem Statement

1. **Version hardcodée** — `WelcomeScreen.tsx` affiche `0.7.4` alors que la version réelle vient déjà de `tauri.conf.json` via `__APP_VERSION__`
2. **Projets fantômes dans les récents** — `get_recent_projects()` expose les chemins du config desktop sans validation. Les projets supprimés restent cliquables dans l'UI
3. **`current_project` invalide au démarrage** — le boot desktop peut encore partir d'un projet supprimé, car le flow actuel ne traite pas explicitement l'état "projet courant invalide"
4. **Contrat `reload-project` trop faible** — `POST /api/health/reload-project` est appelé depuis plusieurs endroits, mais chaque appelant ne vérifie qu'une partie du résultat, et `response.ok` ne suffit pas
5. **État backend potentiellement stale** — `reload_project_from_desktop_config()` ne nettoie pas explicitement `_working_directory` quand le projet courant n'est plus valide
6. **UX incohérente entre surfaces** — le WelcomeScreen et le ProjectSwitcher n'affichent pas les projets invalides de manière uniforme
7. **Double erreur au browse** — `browse_project_folder` affiche à la fois un dialog natif Rust et une erreur React
8. **Empty state à confirmer** — le dashboard semble déjà afficher `OnboardingView` pour un projet vide, mais cela doit devenir un critère de régression explicite

## Proposed Solution

7 interventions ciblées, sans changement d'architecture:

1. afficher la version réelle dans le WelcomeScreen
2. durcir le contrat backend de `reload-project`
3. séquencer correctement l'initialisation desktop dans `App.tsx`
4. centraliser la vérification de reload côté frontend
5. valider les projets récents en batch dans `useProjectSwitcher`
6. aligner le rendu des projets invalides dans le WelcomeScreen et le ProjectSwitcher
7. retirer le dialog natif d'erreur au browse et verrouiller l'empty state comme scénario de test

## Out of Scope

Hors scope pour ce correctif pré-release:

- refonte du wizard de création de projet
- sample project embarqué
- redesign global du dashboard
- nettoyage automatique en arrière-plan des anciens projets invalides

## Acceptance Criteria

- [ ] WelcomeScreen affiche la version via `__APP_VERSION__`
- [ ] Démarrage sans projet courant valide → WelcomeScreen
- [ ] Démarrage avec projet courant valide → recharge correctement le contexte desktop puis affiche l'app
- [ ] Démarrage avec `current_project` supprimé → pas de dashboard stale, retour propre sur le WelcomeScreen avec message explicite
- [ ] Les projets récents invalides sont marqués visuellement dans le WelcomeScreen et dans le ProjectSwitcher
- [ ] Cliquer sur un projet invalide ne déclenche ni switch ni erreur serveur
- [ ] Le bouton de suppression reste disponible pour retirer un projet invalide
- [ ] Si tous les projets récents sont invalides, l'onboarding reste clair: ouvrir un autre dossier ou créer un projet reste le chemin principal
- [ ] `switchProject`, `createProject` et l'initialisation desktop utilisent la même vérification de `reload-project`
- [ ] `reload-project` distingue au minimum les états `loaded`, `welcome`, et `invalid-project`
- [ ] `reload_project_from_desktop_config()` nettoie `_working_directory` quand aucun projet valide n'est disponible
- [ ] `browse_project_folder` ne montre plus de dialog natif d'erreur
- [ ] Un projet fraîchement créé affiche `OnboardingView`
- [ ] `pnpm build`, `pnpm test`, les tests Python ciblés et le check Rust passent

## Implementation

### Step 1: Fix version hardcodée

**Fichier:** `src/niamoto/gui/ui/src/features/welcome/views/WelcomeScreen.tsx`

La version est déjà injectée par Vite depuis `src-tauri/tauri.conf.json`. Il suffit d'utiliser `__APP_VERSION__` au lieu de la valeur hardcodée.

```tsx
declare const __APP_VERSION__: string

<p className="mt-12 text-xs text-muted-foreground/60">
  {t('welcome.version', 'Version')} {typeof __APP_VERSION__ !== 'undefined' ? __APP_VERSION__ : ''}
</p>
```

### Step 2: Durcir le contrat backend de reload desktop

**Fichiers:**

- `src/niamoto/gui/api/context.py`
- `src/niamoto/gui/api/routers/health.py`

Deux corrections sont nécessaires:

1. `reload_project_from_desktop_config()` doit remettre `_working_directory = None` quand:
   - `desktop-config.json` est absent
   - `current_project` est absent
   - `current_project` pointe vers un chemin invalide
2. `POST /api/health/reload-project` doit renvoyer un état exploitable par le frontend, pas seulement un booléen générique

Contrat recommandé:

```json
{
  "success": true,
  "state": "loaded | welcome | invalid-project",
  "project": "/abs/path/or/null",
  "message": "optional human-readable message"
}
```

Sémantique attendue:

- `loaded`: un projet valide est chargé
- `welcome`: aucun projet courant n'est sélectionné, c'est un état normal
- `invalid-project`: le config desktop pointait vers un projet devenu invalide, l'app doit revenir sur l'onboarding sans conserver d'état stale

Le job store doit être synchronisé avec cet état:

- `loaded` → re-résoudre le job store
- `welcome` et `invalid-project` → vider `job_store` et `job_store_work_dir`

### Step 3: Attendre la décision d'onboarding avant le bootstrap desktop

**Fichier:** `src/niamoto/gui/ui/src/app/App.tsx`

Aujourd'hui, l'effet d'initialisation appelle `reload-project` avant que `useWelcomeScreen()` ait fini de décider s'il faut montrer l'onboarding. Il faut inverser cet ordre.

Changement attendu:

- ne rien faire tant que `welcomeLoading` est vrai
- si `showWelcome` est vrai, ne pas appeler `reload-project`
- sinon, appeler le helper partagé de reload puis `refetchProjectInfo()`

Le boot de l'app devient ainsi dépendant de la décision onboarding, au lieu de la court-circuiter.

### Step 4: Centraliser la vérification de `reload-project` côté frontend

**Fichiers:**

- `src/niamoto/gui/ui/src/shared/desktop/projectReload.ts` ou équivalent
- `src/niamoto/gui/ui/src/shared/hooks/useProjectSwitcher.ts`
- `src/niamoto/gui/ui/src/features/welcome/hooks/useWelcomeScreen.ts`
- `src/niamoto/gui/ui/src/app/App.tsx`

Le même endpoint est appelé depuis plusieurs endroits:

- switch projet
- création de projet
- bootstrap desktop initial

Il faut éviter trois implémentations divergentes. Ajouter un petit helper partagé qui:

- fait le `POST /api/health/reload-project`
- parse le payload
- vérifie la combinaison `state` / `project`
- retourne un résultat typé ou lève une erreur claire

Règles d'usage:

- `switchProject(projectPath)` accepte uniquement `state === 'loaded'` avec `project === projectPath`
- `createProject(projectPath)` accepte uniquement `state === 'loaded'` avec `project === projectPath`
- `App.tsx` accepte `loaded`, `welcome`, ou `invalid-project`, mais doit traiter `invalid-project` comme un retour vers l'onboarding, pas comme un boot réussi du dashboard

### Step 5: Valider les projets récents en batch dans le hook partagé

**Fichiers:**

- `src-tauri/src/commands.rs`
- `src-tauri/src/lib.rs`
- `src/niamoto/gui/ui/src/shared/hooks/useProjectSwitcher.ts`

Ajouter une commande Tauri batch pour éviter des validations séquentielles depuis React:

```rust
#[derive(Serialize)]
pub struct RecentProjectStatus {
    pub path: String,
    pub valid: bool,
}

#[tauri::command]
pub fn validate_recent_projects(
    state: State<ConfigState>,
) -> Result<Vec<RecentProjectStatus>, String> {
    // map sur recent_projects + validate_project_path
}
```

Dans `useProjectSwitcher`:

- ajouter `invalidProjects: Set<string>`
- charger `currentProject` + `recentProjects`
- appeler `validate_recent_projects`
- dériver localement `currentProject` comme invalide si son chemin est dans `invalidProjects`
- exposer `invalidProjects` au reste de l'UI

Important:

- ne plus considérer qu'un simple `currentProject` non nul suffit à masquer l'onboarding
- si le projet courant est invalide, l'UI doit se comporter comme si aucun projet n'était chargé

### Step 6: Aligner WelcomeScreen et ProjectSwitcher

**Fichiers:**

- `src/niamoto/gui/ui/src/features/welcome/hooks/useWelcomeScreen.ts`
- `src/niamoto/gui/ui/src/features/welcome/views/WelcomeScreen.tsx`
- `src/niamoto/gui/ui/src/components/common/ProjectSwitcher.tsx`

Le WelcomeScreen doit cesser d'être un cas spécial incomplet. Il doit exploiter les mêmes informations que le switcher.

#### 6.1 `useWelcomeScreen`

- utiliser `invalidProjects` fourni par `useProjectSwitcher`
- si `auto_load_last_project` pointe sur un projet invalide, afficher le WelcomeScreen avec un message guidant l'utilisateur
- ne jamais faire `showWelcome = false` uniquement parce que `currentProject` est non nul; il doit aussi être valide
- faire passer `createProject()` par le helper partagé de reload au lieu d'un `fetch()` ad hoc

#### 6.2 WelcomeScreen

Ajouts UX faibles risques:

- marquer les projets invalides avec une icône warning
- désactiver leur ouverture
- laisser le bouton de suppression accessible
- afficher un message du type:
  - "Le dernier projet ouvert n'est plus disponible."
  - "Supprimez-le de la liste ou ouvrez un autre dossier."

Si tous les projets récents sont invalides, la liste reste informative, mais les CTA "Create New Project" et "Open Project" doivent rester la voie la plus évidente.

#### 6.3 ProjectSwitcher

Même logique visuelle que le WelcomeScreen:

- warning icon
- style atténué
- item non ouvrable
- suppression toujours possible

Le texte de chargement doit rester cohérent pendant un switch en cours.

### Step 7: Retirer le dialog natif d'erreur de browse

**Fichier:** `src-tauri/src/commands.rs`

Dans `browse_project_folder`, retirer l'appel `app.dialog().message(...)` dans la branche d'erreur et retourner directement `Err(e)`.

But:

- une seule surface d'erreur
- même ton et même rendu que le reste de l'onboarding React

### Step 8: Verrouiller l'empty state comme régression, pas comme hypothèse

**Fichier à vérifier:** `src/niamoto/gui/ui/src/features/dashboard/views/ProjectHub.tsx`

`ProjectHub` retourne déjà `OnboardingView` quand il n'y a ni datasets ni references configurés. Aucun changement n'est forcément nécessaire ici, mais cela doit devenir un scénario de validation explicite.

À confirmer manuellement:

- créer un projet neuf
- laisser `db/` vide et les YAML minimaux
- vérifier que `OnboardingView` s'affiche bien après le premier chargement

## Files to Modify

| File | Change |
|------|--------|
| `src/niamoto/gui/ui/src/features/welcome/views/WelcomeScreen.tsx` | Version dynamique + rendu des projets invalides + message onboarding |
| `src/niamoto/gui/ui/src/features/welcome/hooks/useWelcomeScreen.ts` | Décision d'onboarding basée sur la validité réelle du projet courant + création via helper partagé |
| `src/niamoto/gui/ui/src/components/common/ProjectSwitcher.tsx` | Même traitement visuel et fonctionnel des projets invalides |
| `src/niamoto/gui/ui/src/shared/hooks/useProjectSwitcher.ts` | Validation batch des récents + exposition `invalidProjects` + switch robuste |
| `src/niamoto/gui/ui/src/shared/desktop/projectReload.ts` | Helper unique de vérification de `reload-project` |
| `src/niamoto/gui/ui/src/app/App.tsx` | Bootstrap desktop séquencé après la décision welcome |
| `src-tauri/src/commands.rs` | Nouvelle commande `validate_recent_projects` + retrait du dialog natif dans `browse_project_folder` |
| `src-tauri/src/lib.rs` | Enregistrement de `validate_recent_projects` |
| `src/niamoto/gui/api/context.py` | Nettoyage de `_working_directory` quand le projet courant est invalide |
| `src/niamoto/gui/api/routers/health.py` | Contrat `reload-project` enrichi avec `state` et `message` |
| `tests/gui/api/test_context.py` | Cas de test pour cleanup de `_working_directory` sur projet invalide |
| `tests/gui/api/routers/test_health.py` | Cas de test pour `loaded`, `welcome`, `invalid-project` |
| `src/niamoto/gui/ui/src/.../*.test.ts(x)` | Tests ciblés sur helper de reload et décision d'onboarding si ajoutés |

## Dependencies & Risks

- **Risque principal** — la séquence de boot desktop change légèrement. Il faut vérifier qu'on ne réintroduit pas de flash de chargement ou de faux positif au démarrage
- **Contrat frontend/backend** — l'endpoint `reload-project` est utilisé par plusieurs call sites; il faut les migrer ensemble
- **Risque faible côté web** — le comportement reste spécifique au mode desktop Tauri
- **Risque UX faible** — les améliorations proposées restent additives: warning, messages, désactivation des projets invalides
- **Dépendance Rust** — la nouvelle commande Tauri nécessite un check/build Rust pour valider l'enregistrement des commandes

## Verification Plan

```bash
# Frontend
cd src/niamoto/gui/ui && pnpm build
cd src/niamoto/gui/ui && pnpm test

# Backend Python ciblé
pytest tests/gui/api/test_context.py tests/gui/api/routers/test_health.py

# Tauri / Rust
cd src-tauri && cargo check
```

Scénarios manuels à exécuter:

1. Lancer l'app sans projet courant → WelcomeScreen
2. Lancer l'app avec projet courant valide → l'app charge normalement
3. Lancer l'app avec `current_project` supprimé dans `desktop-config.json` → WelcomeScreen avec message explicite, sans dashboard stale
4. WelcomeScreen: un projet récent invalide est marqué, non ouvrable, supprimable
5. WelcomeScreen: si tous les récents sont invalides, les CTA principaux restent évidents
6. ProjectSwitcher: même comportement que sur le WelcomeScreen
7. Switch vers un projet valide → reload accepté puis refresh UI
8. Création d'un projet → reload accepté puis affichage de `OnboardingView`
9. Browse d'un dossier invalide → erreur React uniquement, aucun dialog natif supplémentaire

## Recommendation

Ce plan reste adapté à une release proche: il corrige les bugs réels de boot et de switch projet, tout en ajoutant un petit polish d'onboarding qui améliore la compréhension sans ouvrir un chantier UX plus large.
