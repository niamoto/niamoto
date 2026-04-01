# Refonte UX du module Site

**Date :** 2026-03-31
**Statut :** Validé
**Approche retenue :** Full revamp — vue unifiée + first-launch experience

## Ce qu'on construit

Une refonte UX du module Site pour éliminer la friction entre pages et navigation, proposer une expérience premier lancement fluide, et rendre le module compréhensible par un botaniste en moins de 2 minutes. Pas de changement backend, pas de modification des endpoints API — seul le GUI change.

## Pourquoi cette approche

Le module Site actuel fonctionne mais souffre de deux problèmes d'ergonomie :

1. **Confusion pages / navigation** : créer une page et l'ajouter au menu nécessite des allers-retours entre deux sections séparées. Le botaniste doit maintenir mentalement la cohérence entre "mes pages" et "mon menu".

2. **Démarrage laborieux** : configurer un nouveau site demande de créer chaque page manuellement, construire la navigation élément par élément, configurer le footer — alors que 80% de la structure est prévisible depuis les collections existantes.

La solution : fusionner pages et navigation en une vue unique (pattern Squarespace/Notion), et proposer des presets de site auto-adaptés aux données du projet.

## Décisions clés

### 1. Vue unifiée pages + navigation

La section "Pages" et la section "Navigation" fusionnent en une seule liste dans le panneau gauche :

```
📄 Accueil (index)                    [Menu ✓]
📄 Flore                              [Menu ✓]  ← page statique intro
  🌿 Taxons (collection + index)      [Menu ✓]  ← collection nestée
📄 Milieux                            [Menu ✓]
  🌿 Forêts (collection + index)      [Menu ✓]
📄 Méthodologie                       [Menu ✓]
  📄 Équipe (team)                    [Menu ✓]  ← sous-menu
  📄 Bibliographie (biblio)           [Menu ✓]
📄 Contact                            [Masqué ○]
🔗 Données ouvertes (externe)         [Menu ✓]
```

Principes :
- Créer une page = elle apparaît dans la liste (toggle menu on/off)
- L'ordre drag-and-drop = l'ordre du menu généré
- Indenter un item sous un autre = sous-menu (1 niveau max, comme aujourd'hui)
- Les collections sont draggables et nestables sous des pages statiques de présentation
- Les collections ne sont pas supprimables (elles viennent des données)
- Les liens externes restent possibles (bouton "+ Lien externe")
- La section "Navigation" séparée disparaît

### 2. Collections comme citoyens de première classe

Les collections ne sont plus un bloc séparé en bas de l'arbre. Elles s'intègrent dans la hiérarchie des pages :

- Pattern principal : une page statique de présentation + la collection nestée dessous
- La page statique fournit l'intro/contexte, la collection fournit l'index et les pages détail
- Les collections peuvent aussi être au top-level si pas besoin de page de présentation
- Drag-and-drop pour les positionner librement dans la hiérarchie

### 3. Settings et Apparence dans la toolbar

Les réglages sortent de l'arbre latéral pour libérer l'espace au contenu :

- Bouton engrenage (⚙️) → Settings (titre, logo, langues)
- Bouton palette (🎨) → Thème (couleurs, typo, effets visuels)
- L'arbre reste 100% focalisé sur la structure du site (pages + collections)

### 4. Footer auto-généré

Le footer se génère automatiquement depuis la structure du site :

- Colonnes dérivées de la hiérarchie des pages (ex: "Explorer" → collections, "À propos" → pages statiques)
- Informations projet (titre, copyright) tirées des settings
- Option de personnalisation légère si besoin (override possible mais pas nécessaire)
- Suppression de la section "Footer" comme éditeur séparé

### 5. Presets de site + auto-génération

Pour le premier lancement, le système propose des templates de site complets :

| Preset | Pages incluses | Cible |
|--------|---------------|-------|
| Minimaliste | Accueil + collections | Quick start, données d'abord |
| Scientifique | Accueil + Méthodologie + Équipe + Biblio + Contact + collections | Projet de recherche |
| Complet | Toutes les pages templates + collections | Site institutionnel |

Après le choix du preset :
1. Le système détecte les collections existantes du projet
2. Génère les pages statiques de présentation correspondantes
3. Construit la navigation automatiquement
4. Le footer se génère depuis la structure
5. Le botaniste personnalise le résultat

### 6. Wizard onboarding

Pour les nouveaux projets, un wizard pas-à-pas :

1. **Choisir un preset** (miniatures visuelles de chaque template)
2. **Vérifier la structure** (le système montre ce qu'il a généré)
3. **Personnaliser le thème** (couleurs, logo)
4. **Preview** (aperçu du site avant la première publication)

Le wizard est optionnel — le botaniste peut le fermer et configurer manuellement.

### 7. Miniatures visuelles des templates

Quand on crée une nouvelle page ou qu'on choisit un preset, les templates sont présentés avec des miniatures (wireframes/screenshots simplifiés) au lieu de simples icônes + noms. Aide le botaniste à comprendre ce qu'il va obtenir.

### 8. Ce qui ne change PAS

| Élément | Raison |
|---------|--------|
| Vocabulaire (Pages, Settings, etc.) | Termes déjà universels et compris |
| Panneau preview droite | Fonctionne bien, pas de changement |
| Routes URL (`/site/*`) | Pas de breaking change |
| Endpoints API backend | Hors scope GUI |
| Templates de pages existants | Formulaires typés conservés |
| Éditeur markdown | Fonctionne bien |
| Support multilingue | Conservé tel quel |

## Périmètre

### Inclus
- Vue unifiée pages + navigation (fusion des deux sections)
- Collections draggables dans la hiérarchie des pages
- Settings et Thème déplacés dans la toolbar
- Footer auto-généré depuis la structure
- Presets de site (3 templates) avec auto-adaptation aux collections
- Wizard onboarding pour premier lancement
- Miniatures visuelles des templates
- Décomposition de SiteBuilder.tsx (1566 lignes → composants focalisés)

### Exclu
- Modification des endpoints API backend
- Modification des routes URL
- Modification des templates HTML (Jinja2)
- Changement du système de preview
- Renommage de vocabulaire
- Modification du module Publish

## Phasage

### Phase A — Structurel

La refonte architecturale du module.

- **Vue unifiée** : fusion pages + navigation en une seule liste
- **Collections dans la hiérarchie** : draggables, nestables sous pages statiques
- **Toolbar** : Settings et Thème en boutons dans la barre d'outils
- **Footer auto-généré** : dérivé de la structure des pages
- **Presets de site** : 3 templates pour le premier lancement
- **Décomposition SiteBuilder.tsx** : extraction en composants ciblés
- **Tests** : build compile, navigation fonctionne, preview ok

### Phase B — First-launch experience

L'expérience premier lancement polie.

- **Wizard onboarding** : stepper pas-à-pas pour la première configuration
- **Auto-génération intelligente** : analyse des collections pour pré-remplir le site
- **Miniatures templates** : wireframes/screenshots pour chaque template de page
- **Smart defaults** : pré-remplissage intelligent des formulaires de pages
- **Tests** : wizard complet, auto-génération correcte, miniatures affichées

## Impacts cross-modules identifiés

| Module | Impact |
|--------|--------|
| App.tsx | Routes site possiblement simplifiées (les 5 routes actuelles) |
| navigationStore.ts | Breadcrumb labels si routes changent |
| DashboardView.tsx | Lien vers le module Site (inchangé) |
| OnboardingView.tsx | Intégration avec le wizard de Phase B |
| i18n (site.json) | Nouvelles clés pour vue unifiée, toolbar, wizard |
| SiteBuilder.tsx (1566 lignes) | Décomposition majeure |
| SiteTreeView.tsx | Remplacé par la vue unifiée |
| NavigationBuilder.tsx | Absorbé dans la vue unifiée |
| FooterSectionsEditor.tsx | Simplifié (auto-gen + override léger) |

## Inspirations

| Pattern | Source | Application Niamoto |
|---------|--------|---------------------|
| Liste pages = navigation | Squarespace, Notion Sites | Vue unifiée |
| Presets de site | Framer, Squarespace | Templates premier lancement |
| Footer auto-généré | Notion Sites | Dérivé de la structure |
| Settings dans toolbar | Framer | Engrenage + palette |
| Miniatures templates | Squarespace, Framer | Choix visuel des templates |
| Wizard onboarding | Webflow | Premier lancement guidé |

## Questions résolues

| Question | Réponse |
|----------|---------|
| Vocabulaire à changer ? | Non, les termes actuels sont universels |
| Pages et Nav séparés ou fusionnés ? | Fusionnés en vue unifiée |
| Collections dans l'arbre ? | Oui, draggables et nestables |
| Settings où ? | Toolbar (boutons engrenage + palette) |
| Footer ? | Auto-généré, override possible |
| Preview à améliorer ? | Non, fonctionne bien |
| Statut publish dans le module Site ? | Non, reste dans le module Publish |
| Combien de phases ? | 2 (structurel + first-launch) |
| Presets de site ? | 3 (minimaliste, scientifique, complet) + adaptation aux collections |

## Questions ouvertes (non bloquantes)

- Le wizard onboarding réutilise-t-il l'OnboardingView existant ou c'est un composant séparé ?
- Les miniatures de templates : screenshots statiques ou wireframes générés dynamiquement ?
- Footer auto-généré : quelles colonnes par défaut pour chaque preset ?
- Quand le site n'a aucune collection, le preset "Minimaliste" a-t-il du sens ?
