# UI Density Compaction

**Date**: 2026-04-12
**Status**: Ready for planning

## What We're Building

Compacter l'ensemble des primitives UI de Niamoto pour passer d'une densité "dashboard SaaS" à une densité "outil desktop pro" (référence : VS Code, Figma, DataGrip, Grafana).

Le problème n'est pas le layout (sidebars, grilles) mais l'échelle visuelle des composants eux-mêmes : boutons, inputs, cartes, titres, espacements — tout est dimensionné pour du web responsive alors que l'app est un outil desktop Tauri.

## Why This Approach

**Changement direct des primitives** plutôt que système de thème ou CSS variables :
- Le problème est que les valeurs par défaut sont trop grosses, pas qu'on a besoin de deux modes
- Pas de raison de maintenir les anciennes valeurs si elles sont mauvaises
- Plus simple à implémenter et maintenir qu'une couche d'abstraction de densité
- Le système de thèmes (ThemeTokens) ne contrôle pas les tailles — il faudrait l'étendre significativement pour gérer la densité, ce qui est over-engineered pour ce besoin

## Key Decisions

### 1. Niveau de densité : Dense/pro

| Composant | Actuel | Cible |
|-----------|--------|-------|
| Button (default) | h-10 (40px) | h-7 (28px) |
| Button (sm) | h-9 (36px) | h-6 (24px) |
| Button (lg) | h-11 (44px) | h-8 (32px) |
| Button (icon) | h-10 w-10 | h-7 w-7 |
| Input | h-9 (36px) | h-7 (28px) |
| Select | h-9 (36px) | h-7 (28px) |
| Tabs list | h-9 (36px) | h-7 (28px) |
| Card padding | p-6 (24px) | p-3 (12px) |
| Card gap | gap-6 (24px) | gap-3 (12px) |
| Section gap | space-y-6 (24px) | space-y-3 (12px) |
| Page padding | p-6 (24px) | p-4 (16px) |

### 2. Échelle typographique

| Usage | Actuel | Cible |
|-------|--------|-------|
| Body / données | text-sm (14px) | text-[13px] |
| Labels / méta | text-sm (14px) | text-xs (12px) |
| Titres de page | text-3xl (30px) | text-lg (18px) |
| Titres de section | text-xl (20px) | text-base (16px) |
| Métriques hero | text-3xl (30px) | text-xl (20px) |

**Note technique** : Tailwind n'a pas de classe native pour 13px. Options :
- `text-[13px]` (arbitrary value, simple)
- Définir un token custom dans le CSS (`--text-body: 13px`)
- Utiliser `text-sm` (14px) si 1px de différence ne justifie pas la complexité

### 3. Déploiement progressif en 3 phases

**Phase 1 — Primitives UI** (composants shadcn/ui)
- button.tsx, card.tsx, input.tsx, select.tsx, tabs.tsx, label.tsx, badge.tsx, dialog.tsx
- Fichiers dans `src/niamoto/gui/ui/src/shared/components/ui/`

**Phase 2 — Écrans pilotes** (3 écrans de test)
- Dashboard (DashboardView.tsx) — vue d'accueil, métriques, navigation
- Data Explorer (DataExplorer.tsx) — tableaux, filtres, données denses
- Settings (Settings.tsx) — formulaires, sections, contrôles

**Phase 3 — Propagation**
- Tous les modules restants (Data, Site Builder, Publish, Collections, Enrichment)
- Vérification visuelle écran par écran
- Ajustements spécifiques si nécessaire

## Scope — Ce qui est inclus et exclu

**Inclus :**
- Tailles des composants primitifs (hauteur, padding, gap)
- Échelle typographique (titres, body, labels)
- Espacements inter-sections

**Exclu (pas dans ce chantier) :**
- Layout (largeur sidebars, ratios de panneaux, breakpoints)
- Couleurs, thèmes, ombres, radius
- Fenêtre par défaut Tauri (tauri.conf.json) — sujet séparé
- Responsive / mobile
- Ajout de tokens de densité au système de thèmes

## Risques

- **Régression visuelle large** : changer les primitives impacte tous les écrans d'un coup. Mitigation : phase 2 avec 3 écrans pilotes avant propagation.
- **Trop serré pour certains contextes** : des écrans comme l'onboarding ou les états vides pourraient souffrir d'une densité trop forte. Il faudra peut-être garder des variantes plus grandes pour ces cas.
- **13px body** : valeur custom qui ajoute un cas particulier. Si ça ne vaut pas le coup, text-sm (14px) est acceptable.

## Open Questions

1. Faut-il aussi toucher à la taille de la fenêtre par défaut (1280x900) dans tauri.conf.json, ou c'est un sujet séparé ?
2. Les états vides et l'onboarding doivent-ils garder une échelle plus large ?
3. Dialog / modales : mêmes réductions ou traitement séparé ?
