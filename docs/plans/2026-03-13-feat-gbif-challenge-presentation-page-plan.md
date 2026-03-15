---
title: "Page HTML de présentation du plan GBIF Ebbe Nielsen Challenge 2026"
type: feat
date: 2026-03-13
---

# Page HTML de présentation du plan GBIF Ebbe Nielsen Challenge 2026

## Overview

Créer une page HTML standalone de présentation du rapport d'opportunité pour la participation de Niamoto au GBIF Ebbe Nielsen Challenge 2026. La page doit reprendre le style visuel des pages statiques générées par Niamoto (vert forêt, widgets modernes, typographie claire) tout en étant un fichier autonome déployable sur GitHub Pages.

**Objectif** : un support de présentation à l'équipe, lisible, visuel et ergonomique, qui transforme le rapport markdown dense en une expérience web structurée et navigable.

## Problème / Motivation

Le rapport d'opportunité (`docs/plans/2026-03-11-feat-gbif-ebbe-nielsen-challenge-2026-opportunity-report.md`) fait ~740 lignes de markdown avec des tableaux, diagrammes ASCII, et analyses détaillées. Le présenter tel quel à l'équipe ne permet pas une lecture efficace. Une page HTML soignée avec navigation latérale, sections visuelles et mise en forme adaptée facilite la prise de décision collective.

## Solution proposée

Un fichier HTML unique (`docs/presentation/gbif-challenge-2026.html`) avec :

- **Design Niamoto** — palette verte (#228b22 / #4caf50), widgets modernes, typographie Inter/system-ui
- **Self-contained** — Tailwind CSS via CDN, Lucide Icons via CDN, tout le CSS custom embarqué
- **Navigation latérale sticky** — TOC auto-générée depuis les h2/h3, highlight actif au scroll
- **Responsive** — mobile-first, sidebar se replie en menu sur petit écran

### Structure de la page

```
┌─────────────────────────────────────────────────────────────┐
│  NAV BAR (vert Niamoto, logo, titre "Niamoto Challenge")   │
├─────────────────────────────────────────────────────────────┤
│  HERO SECTION                                               │
│  "GBIF Ebbe Nielsen Challenge 2026"                         │
│  Sous-titre + badge "20 000 €" + countdown "26 juin 2026"   │
│  Verdict badge: "Opportunité réaliste et atteignable"       │
├─────────────────────────────────────────────────────────────┤
│  STATS BAR (4 cards horizontales)                           │
│  [20 000 €] [26 juin] [15 semaines] [Open source]           │
├──────────┬──────────────────────────────────────────────────┤
│ SIDEBAR  │  CONTENU PRINCIPAL                               │
│ TOC      │                                                  │
│ sticky   │  § Le Challenge                                  │
│          │    - Critères d'évaluation (tableau stylé)        │
│ ▸ Résumé │    - Soumissions acceptées (liste icônes)         │
│ ▸ Chall. │                                                  │
│ ▸ Gagn.  │  § Analyse des gagnants (2019-2025)              │
│ ▸ Niamoto│    - Tableau récap avec badges année              │
│ ▸ Propos.│    - Patterns identifiés (cards icônes)           │
│ ▸ Archi. │    - Faille IA cloud (highlight box rouge/vert)   │
│ ▸ SWOT   │                                                  │
│ ▸ Roadmap│  § Capacités Niamoto                              │
│ ▸ Budget │    - Ce qui existe (tableau vert ✅)               │
│          │    - Ce qui manque (tableau orange ⚠️)             │
│          │                                                  │
│          │  § Proposition retenue ⭐                         │
│          │    - Pipeline diagram (styled ASCII → CSS boxes)  │
│          │    - Pitch (blockquote accent vert)               │
│          │    - Tableau comparatif vs gagnants               │
│          │    - Principe déterministe/non-déterministe       │
│          │      (deux blocs visuels vert/orange)             │
│          │    - Alignement critères (score cards)            │
│          │    - Arguments stratégiques (numbered cards)      │
│          │                                                  │
│          │  § Architecture technique                         │
│          │    - 5 niveaux (accordion/tabs)                   │
│          │    - Tableau budget disque                        │
│          │    - Code snippets (dark theme pre)               │
│          │                                                  │
│          │  § SWOT (4 quadrants colorés)                     │
│          │                                                  │
│          │  § Roadmap (timeline verticale avec phases)       │
│          │    - Phases 1-9 avec icônes criticité             │
│          │    - Checkpoint 30 avril marqué                   │
│          │                                                  │
│          │  § Prochaines étapes (call-to-action cards)       │
├──────────┴──────────────────────────────────────────────────┤
│  FOOTER (style Niamoto, liens GitHub + GBIF)                │
└─────────────────────────────────────────────────────────────┘
```

### Composants visuels spécifiques

#### 1. Hero Section
- Gradient vert forêt → vert foncé (comme `index.html` hero)
- Titre Arial Black majuscule avec text-shadow
- Badges : montant du prix, date limite, statut
- Pas d'image de fond (gradient suffit)

#### 2. Stats Bar
Reprend le pattern `index.html` stats section :
```html
<div class="stats-grid">  <!-- 4 colonnes, fond blanc, border-radius 1rem -->
  <div class="stat-card">
    <div class="stat-icon">💰</div>  <!-- ou Lucide icon -->
    <div class="stat-value">20 000 €</div>
    <div class="stat-label">Prix total</div>
  </div>
  <!-- x4 -->
</div>
```

#### 3. Pipeline Diagram
Les diagrammes ASCII du rapport seront convertis en blocs CSS :
```html
<div class="pipeline">
  <div class="pipeline-step">
    <div class="step-icon">📄</div>
    <div class="step-title">CSV/Excel/DwC-A brut</div>
  </div>
  <div class="pipeline-arrow">↓</div>
  <div class="pipeline-step has-badge">
    <div class="step-title">Détection de schéma</div>
    <div class="step-badge">scikit-learn (local)</div>
  </div>
  <!-- ... -->
</div>
```

#### 4. Tableau comparatif (Niamoto vs gagnants)
Tableau avec colonnes stylées, checkmarks ✅/❌ colorées, colonne Niamoto mise en avant (fond vert clair, bordure épaisse).

#### 5. SWOT
Grille 2x2 avec couleurs distinctes :
- Forces : vert (#ecfdf5 / #16a34a)
- Faiblesses : orange (#fff7ed / #ea580c)
- Opportunités : bleu (#eff6ff / #2563eb)
- Menaces : rouge (#fef2f2 / #dc2626)

#### 6. Timeline/Roadmap
Timeline verticale CSS avec :
- Ligne verticale verte
- Cercles numérotés par phase
- Badges criticité : 🔴 Essentielle / 🟡 Importante / 🟢 Bonus
- Barre de progression semaines
- Marqueur spécial pour le checkpoint 30 avril

#### 7. Architecture déterministe/non-déterministe
Deux blocs visuels empilés :
- Bloc vert (déterministe) : fond vert pâle, bordure verte, grille de composants
- Bloc orange (non-déterministe) : fond ambre pâle, bordure orange, mention "optionnel"

### Dépendances CDN (self-contained)

| Ressource | CDN | Usage |
|-----------|-----|-------|
| Tailwind CSS v4 | `cdn.tailwindcss.com` | Framework CSS utilitaire |
| Lucide Icons | `unpkg.com/lucide` | Icônes SVG |
| Inter font | Google Fonts | Typographie |

Pas de Plotly, Leaflet ou autre bibliothèque lourde — page de présentation pure.

## Acceptance Criteria

### Contenu
- [ ] Toutes les sections du rapport sont présentes et lisibles
- [ ] Les tableaux sont stylés et responsive (scroll horizontal sur mobile si nécessaire)
- [ ] Les diagrammes ASCII sont convertis en composants CSS visuels
- [ ] Le pitch est mis en avant visuellement (blockquote stylé)
- [ ] La timeline/roadmap est visuelle avec indicateurs de criticité

### Design
- [ ] Palette de couleurs Niamoto (vert #228b22, gris #f9fafb/#1f2937)
- [ ] Navigation bar verte fixe avec titre
- [ ] Sidebar TOC sticky avec highlight actif au scroll (IntersectionObserver)
- [ ] Responsive : mobile (sidebar repliée), tablet, desktop
- [ ] Transitions fluides (150ms cubic-bezier)
- [ ] Footer style Niamoto

### Technique
- [ ] Fichier HTML unique, self-contained (CSS embarqué + CDN)
- [ ] Fonctionne directement dans un navigateur (pas de build step)
- [ ] Compatible GitHub Pages (pas de dépendance serveur)
- [ ] Code propre et bien commenté

### Déploiement
- [ ] Fichier placé dans `docs/presentation/gbif-challenge-2026.html`
- [ ] Testable en ouvrant directement le fichier dans un navigateur

## Références

### Fichiers de style Niamoto (source de vérité)
- `src/niamoto/publish/templates/_base.html` — Variables CSS, structure de base
- `src/niamoto/publish/templates/index.html` — Hero, stats bar, features
- `src/niamoto/publish/templates/article.html` — Sidebar TOC, markdown content styling
- `src/niamoto/publish/templates/_nav.html` — Navigation bar verte
- `src/niamoto/publish/templates/_footer.html` — Footer sombre
- `src/niamoto/publish/assets/css/niamoto.css` — Widgets, grille, tooltips

### Contenu source
- `docs/plans/2026-03-11-feat-gbif-ebbe-nielsen-challenge-2026-opportunity-report.md` — Rapport complet

### Design tokens Niamoto extraits
```css
:root {
  --color-primary: #228b22;
  --color-secondary: #4caf50;
  --color-nav-bg: #228b22;
  --color-background: #f9fafb;
  --color-text: #111827;
  --color-link: #228b22;
  --color-footer-bg: #1f2937;
  --border-radius: 8px;
  --border-radius-sm: 4px;
  --border-radius-lg: 12px;
  --font-family: 'Inter', system-ui, sans-serif;
}
```
