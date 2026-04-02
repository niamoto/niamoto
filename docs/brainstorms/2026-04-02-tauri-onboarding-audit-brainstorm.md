# Tauri Desktop App — Pre-Release Onboarding Audit

**Date:** 2026-04-02
**Status:** Ready for planning
**Context:** App Tauri sur le point d'être livrée. Audit complet du flow de lancement, onboarding et switch projet.

## What We're Building

Corrections et polish du parcours utilisateur desktop avant release :
1. Fix version hardcodée dans WelcomeScreen
2. Fix switch projet cassé (projets fantômes dans la liste)
3. Feedback visuel pendant le switch de projet
4. Vérification robuste après reload-project
5. Empty state cohérent pour un projet fraîchement créé

## Architecture actuelle

```
Tauri (Rust)                    FastAPI (Python)              React (TS)
─────────────                   ────────────────              ──────────
lib.rs                          health.py                     App.tsx
├─ loading screen               ├─ GET /api/health            ├─ isTauri detection
├─ sidecar spawn                ├─ GET /runtime-mode          ├─ useWelcomeScreen()
│  └─ NIAMOTO_HOME env          ├─ POST /reload-project       │  ├─ auto-load last project
├─ health check polling         │  └─ reads desktop-config    │  ├─ showWelcome decision
└─ window.location → React      └─ GET /diagnostic            │  └─ WelcomeScreen render
                                                              └─ ProjectSwitcher (TopBar)
commands.rs                     context.py
├─ get_current_project          ├─ _working_directory (global)
├─ set_current_project          ├─ reload_project_from_desktop_config()
├─ get_recent_projects          └─ get_database_path()
├─ validate_project
├─ create_project
└─ browse_project_folder

Config: ~/.niamoto/desktop-config.json
```

## Key Decisions

### 1. Version hardcodée → Lire depuis l'API

**Problème:** `WelcomeScreen.tsx:259` affiche `0.7.4` mais la version réelle est `0.11.0`.

**Décision:** Lire la version depuis l'endpoint `/api/config/project` qui retourne `niamoto_version`. Le WelcomeScreen n'a pas accès à l'API directement (affiché avant le projet), donc récupérer la version via un Tauri command ou la passer en prop depuis App.tsx qui a déjà `useProjectInfo()`.

**Alternative retenue:** Utiliser `__TAURI__` pour lire `package.json` version ou la version Tauri directement via `app.getVersion()`. C'est la solution la plus simple car la WelcomeScreen est affichée AVANT qu'un projet soit chargé (donc pas d'API backend disponible de façon fiable).

### 2. Switch projet cassé — Projets fantômes

**Problème:** `useProjectSwitcher.loadProjects()` charge la liste depuis le config JSON **sans valider** que les chemins existent. Quand l'utilisateur clique sur un projet supprimé/déplacé, `set_current_project` échoue car `validate_project_path` retourne une erreur.

**Décision:** Valider les projets au chargement de la liste et marquer visuellement les invalides.

**Approche:**
- Ajouter une commande Tauri `validate_recent_projects` qui vérifie tous les chemins en batch
- Dans `useProjectSwitcher.loadProjects()`, appeler cette validation après le chargement
- Dans le ProjectSwitcher UI : projets invalides grisés avec icône warning, non-cliquables, bouton X visible pour les retirer
- Auto-cleanup optionnel : retirer silencieusement les invalides après N jours

### 3. Feedback visuel pendant le switch

**Problème:** `window.location.reload()` cause un flash blanc. Le loading screen Rust ne s'affiche que au premier lancement.

**Décision:** Pas de modification complexe. Le reload est rapide (<1s) et le `switching` state sur le bouton du ProjectSwitcher suffit. Si on veut aller plus loin : injecter un loading screen CSS via Tauri avant le reload (comme pour le startup), mais c'est over-engineering pour la v1.

**Approche retenue:** S'assurer que le bouton du dropdown affiche bien "Switching..." pendant le switch (déjà implémenté via `setSwitching(true)`). Ajouter un overlay temporaire sur la page pour éviter le flash blanc.

### 4. Vérification après reload-project

**Problème:** `switchProject` fait POST `/api/health/reload-project` puis `window.location.reload()` immédiatement. Si le reload échoue côté serveur, la page se recharge avec un état incohérent.

**Décision:** Vérifier la réponse du reload ET attendre un health check réussi avant de reloader la page.

**Approche:**
```
switchProject(path)
  → set_current_project (Tauri)
  → POST /api/health/reload-project
  → Vérifier response.success === true ET response.project === path attendu
  → Seulement alors : window.location.reload()
  → Si échec : afficher erreur, ne pas reloader
```

### 5. Empty state après création de projet

**Problème:** `create_project` crée la structure de répertoires + YAML vides. Le dashboard va afficher quoi pour un projet sans données ?

**Décision:** Vérifier que le dashboard a un empty state propre. Si ce n'est pas le cas, en ajouter un minimal (message "Import your data to get started" avec lien vers Sources).

## Open Questions

1. Faut-il un mécanisme de "projet par défaut" pour la première utilisation (e.g. un sample project bundlé) ?
   - **Réponse probable : non pour la v1.** Le wizard de création + l'import suffisent.

2. Le `browse_project_folder` affiche un dialog natif d'erreur + une erreur UI — garder les deux ?
   - **Proposition :** Retirer le dialog natif, laisser l'UI gérer l'affichage d'erreur (plus cohérent).

## Files to Modify

| File | Change |
|------|--------|
| `WelcomeScreen.tsx` | Version dynamique via Tauri API |
| `useProjectSwitcher.ts` | Validation des projets récents au chargement |
| `ProjectSwitcher.tsx` | UI pour projets invalides (grisé, warning) |
| `commands.rs` | Nouvelle commande `validate_recent_projects` (batch) |
| `useProjectSwitcher.ts` | Vérification robuste après reload-project |
| `commands.rs` | Retirer le dialog natif d'erreur de `browse_project_folder` |
| Dashboard empty state | Vérifier/ajouter si nécessaire |
