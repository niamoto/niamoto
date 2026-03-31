# Simplification du module Groupes → Collections

**Date :** 2026-03-31
**Statut :** Validé
**Approche retenue :** Renommage cosmétique (GUI uniquement)

## Ce qu'on construit

Une refonte UX du module "Groupes" dans le GUI Niamoto. L'objectif est de rendre le module compréhensible par un botaniste de terrain en moins de 2 minutes. Pas de changement backend, pas de modification des fichiers YAML ni des modèles Pydantic — seul le GUI change.

## Pourquoi cette approche

Le botaniste ne touche jamais les fichiers YAML : le GUI les génère. Renommer l'interface suffit à résoudre le problème d'ergonomie sans introduire de breaking change ni nécessiter de migration de config existante. Si un alignement YAML est souhaité plus tard, ce sera une release dédiée.

## Nouveau vocabulaire

| Ancien (technique) | Nouveau (botaniste) | Scope |
|--------------------|---------------------|-------|
| Groupes (module)   | **Collections**     | GUI label, navigation |
| Un groupe          | **Une collection**  | GUI label |
| Page par entité    | **Une fiche**       | GUI label |
| Widgets            | **Blocs**           | GUI label |

Le vocabulaire YAML (`group_by`, `widgets_data`, etc.) reste inchangé.

## Décisions clés

### 1. Réorganisation des onglets (4 → 3)

| Ancien                     | Nouveau      | Contenu                                    |
|----------------------------|--------------|--------------------------------------------|
| Sources (onglet dédié)     | *(supprimé)* | Sources auxiliaires déplacées dans Blocs    |
| Contenu                    | **Blocs**    | Configuration des blocs + lien discret sources aux. |
| Index                      | **Liste**    | Configuration page de listing (inchangé)   |
| API                        | **Export**   | Exports JSON, DarwinCore (inchangé)        |

### 2. Vue d'ensemble enrichie

La page d'accueil du module Collections affiche des cartes enrichies pour chaque collection, avec :

- **Compteurs** : nombre d'entités, nombre de blocs configurés, nombre d'exports
- **Statut de fraîcheur** : fiches à jour (vert) ou à recalculer (orange)
- **Aperçu miniature** : preview des blocs d'une fiche type
- **Dernière exécution** : date du dernier calcul (transform)
- **Raccourcis directs** : boutons Blocs / Liste / Export pour accéder directement à l'onglet voulu

### 3. Navigation

- **Vue d'ensemble** : grille de cartes enrichies (point d'entrée du module)
- **Vue collection** : sidebar légère à gauche listant les collections pour switcher rapidement, contenu principal avec les 3 onglets (Blocs / Liste / Export)
- **Bouton retour** vers la vue d'ensemble

### 4. Onglet Blocs — sources auxiliaires

Les sources auxiliaires (CSV stats pré-calculées) restent accessibles via un lien ou bouton discret dans l'onglet Blocs. Ce n'est plus un concept central, c'est une option avancée.

### 5. Layout interne — pas de changement

- Onglet Blocs : layout deux panneaux (liste à gauche, config/preview à droite) — conservé
- Liste des blocs : aspect actuel conservé
- Onglets Liste et Export : contenu actuel conservé, seul le nom change

## Périmètre

### Inclus
- Renommage des labels et titres dans le GUI (Collections, Blocs, Fiches, Liste, Export)
- Suppression de l'onglet Sources (fusion dans Blocs)
- Nouvelle vue d'ensemble avec cartes enrichies (compteurs, statut, aperçu, raccourcis)
- Sidebar légère de navigation entre collections
- Mise à jour de la navigation (routes, breadcrumbs)

### Exclu
- Modification des fichiers YAML (import.yml, transform.yml, export.yml)
- Modification des modèles Pydantic backend
- Modification des endpoints API (les noms techniques restent côté API)
- Modification du comportement des onglets Liste et Export (contenu inchangé)
- Refonte du layout de l'onglet Blocs

## Questions résolues

| Question | Réponse |
|----------|---------|
| Public cible ? | Le botaniste de terrain |
| Renommage backend aussi ? | Non, GUI uniquement (Approche A) |
| Combien d'onglets ? | 3 (Blocs, Liste, Export) |
| Où vont les sources aux. ? | Lien discret dans Blocs |
| Navigation 2 niveaux ? | Oui : vue d'ensemble + vue collection avec sidebar légère |
| Layout onglet Blocs ? | Deux panneaux, inchangé |

## Questions ouvertes à trancher

### Résolues

1. **Routes URL** : on garde `/groups` dans les URLs. Le botaniste ne voit pas la barre d'adresse. ✅
2. **Sources auxiliaires dans Blocs** : bouton discret "Sources" dans le header de l'onglet Blocs → ouvre un dialog overlay avec le contenu actuel de l'onglet Sources. ✅
3. **Page API Settings** : accessible depuis un bouton "Réglages globaux" dans l'onglet Export. ✅
4. **1 seule collection** : toujours afficher la vue d'ensemble, même avec 1 seule collection.
5. **Données des cartes enrichies** : N appels frontend acceptables, optimisation backend si besoin plus tard.
6. **Source primaire (read-only)** : affichée dans le header de la collection (à côté du kind et du nombre d'entités).
7. **Renommage des fichiers de code** : oui, `features/groups/` → `features/collections/`, dans un commit séparé.
8. **Aperçu miniature** sur les cartes : badges/icônes des types de blocs configurés (léger, pas de preview rendu).

### Ouvertes (non bloquantes)

- Le terme "Fiche" : doit-il apparaître dans le GUI ou c'est juste un concept mental ?
- Documentation (docs/) : faut-il mettre à jour les labels dans la doc aussi ?

## Impacts cross-modules identifiés

Les modules suivants référencent "groups" et devront être mis à jour (labels user-facing uniquement) :

- **Dashboard** : `DashboardView.tsx`, `GroupsSummary.tsx` — labels pipeline et navigation
- **Import** : `DataModule.tsx` — callbacks `onOpenGroups()`, `onOpenGroup()`
- **Onboarding** : `OnboardingView.tsx` — étape "Configure groups"
- **Pipeline** : `StalenessBanner.tsx` — messages mentionnant "groups"
- **Navigation** : `navigationStore.ts` — item sidebar id `'groups'`
- **i18n** : `en/sources.json`, `fr/sources.json`, `en/common.json`, `fr/common.json` — ~50+ clés
- **Routes** : `App.tsx` — définition des routes (si renommage URL décidé)

## Phasage suggéré

1. **Phase A** — Renommage labels + restructuration onglets (4→3) : livre l'essentiel de la valeur UX
2. **Phase B** — Vue d'ensemble enrichie avec cartes (compteurs, statut, aperçu, raccourcis)
3. **Phase C** — Fusion sources dans Blocs (dialog overlay)
