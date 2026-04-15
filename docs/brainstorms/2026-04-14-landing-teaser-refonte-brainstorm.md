---
date: 2026-04-14
topic: landing-teaser-refonte
parent: docs/brainstorms/2026-04-14-landing-teaser-video-brainstorm.md
---

# Landing Teaser — Refonte au design système réel

## Problem Frame

Le teaser `LandingTeaser` livré le 14/04 (cf. `docs/plans/2026-04-14-feat-landing-teaser-video-plan.md`) reproduit l'UI Niamoto en JSX à partir d'un `docs/DESIGN_SYSTEM.md` qui décrit en réalité la palette du **demo video** (light/airy/steel-blue éditorial), pas celle du **vrai produit publié** (header vert `#15803D` dense, sidebar taxonomique, vraies cartes Plotly bubbles sur la topologie NC, bar charts denses style scientifique).

Conséquence visible :
- la **carte** dans `CollectionMosaic.tsx` est un SVG abstrait sans rapport avec le vrai rendu Plotly,
- les **charts** sont des mini-donuts / mini-gauges, alors que le vrai produit utilise des bar charts, des distributions DBH, des calendriers de phénologie,
- l'**alignement** et la **densité d'info** des cards ne ressemblent pas au site publié,
- la **typographie** et les espacements donnent une impression "maquette" et non "produit".

Le brief original (R3 du plan) demandait un ton « sobre, crédible, scientifique, éditorial ». Le résultat actuel atteint l'éditorial mais rate la crédibilité scientifique parce qu'il ne ressemble pas à Niamoto.

## What We're Building

Une refonte complète des 5 scènes du teaser pour qu'elles parlent visuellement le même langage que le vrai site Niamoto publié, sans renoncer à la liberté de motion offerte par Remotion.

Concrètement :
- Aligner le **theme** (`media/demo-video/src/shared/theme.ts`) sur la palette réelle du produit (vert `#15803D`, accents verts, surfaces blanches, typographie produit).
- Mettre à jour `docs/DESIGN_SYSTEM.md` pour qu'il décrive cette palette comme source de vérité.
- Refondre **AppWindow** pour ressembler au vrai IDE Niamoto (cf. `media/demo-video/public/reference/site-pages-editor.png` : sidebar gauche dense avec icônes, fil d'Ariane, bouton Save vert).
- Remplacer les widgets fabriqués (mini-donut, mini-gauge, AbstractMapGraphic) par de **vraies librairies de charts** rendues dans Remotion :
  - `recharts` ou `visx` pour les bar charts, distributions DBH, phénologie ;
  - **Leaflet via `@remotion/maps`** ou export Plotly statique animé pour la carte NC ;
  - données factices générées à partir des taxons réels (Olea paniculata visible sur `site-taxon.png`).
- Refondre la **mosaïque collection** (`CollectionMosaic.tsx`, 711 lignes) en une vraie page collection style Niamoto avec sidebar taxonomique + 4-6 widgets vrais charts.
- Refondre le **payoff publish** pour s'approcher visuellement de `site-taxon.png` (header vert + cards à bandeau vert + 4-6 charts denses).

## Why This Approach

L'utilisateur a explicitement choisi cette voie après comparaison de 4 options :
1. screenshot-first cinématique, 2. hybride device-frame, 3. capture screencast, **4. refonte mocks au DS réel** ← retenu.

Raison :
- Garder la liberté de motion frame-par-frame (springs, masking, parallaxe) que les screenshots statiques ne permettent pas aussi finement.
- Les vraies librairies chart dans Remotion permettent d'animer les barres, les bubbles map, les bins de distribution **frame par frame** plutôt que masquer/révéler une image figée.
- À long terme, les mocks deviennent réutilisables pour d'autres vidéos (social cuts, screencasts produit) et restent maintenables dans le temps.

## Key Decisions

| Décision | Choix |
|----------|-------|
| Cause racine adressée | Mocks UI désalignés vs vrai produit |
| Référence visuelle cible | Vrai produit Niamoto — vert dense scientifique |
| Approche rendu widgets | Vraies libs chart dans Remotion (recharts prioritaire, Leaflet/Mapbox pour map) |
| Ampleur | Full overhaul des 5 scènes |
| `DESIGN_SYSTEM.md` | À mettre à jour comme source de vérité de la nouvelle palette |
| Composition existante (`MarketingLandscape`) | Non touchée — c'est uniquement le teaser |
| Brief R1-R15 du plan original | Préservé (durée ~45s, curseur sur 2 interactions, endcard sans CTA, etc.) |

## Open Questions (pour la phase plan)

1. **Lib chart précise** : `recharts` vs `visx` vs `nivo` ? Premier candidat = `recharts` (léger, React-native, exemples Remotion existants). À valider via prototype.
2. **Carte NC** : 3 candidats — (a) Leaflet via `@remotion/maps`, (b) Mapbox via `@remotion/maps`, (c) export PNG du vrai Plotly + animation des bubbles en SVG par-dessus. Le (c) est le plus simple et le plus fidèle visuellement ; le (a/b) le plus authentique en motion mais lourd à mettre en place hors-ligne.
3. **Données factices** : extraire de l'instance test `test-instance/niamoto-test/` (taxons réels, distributions DBH calculées) ou inventer des valeurs plausibles ? La première option garantit la crédibilité scientifique mais exige un script d'export.
4. **Perf rendering Remotion** : recharts re-render à chaque frame peut être coûteux. Faut-il memoïser via `React.memo` + n'animer que les valeurs interpolées ?
5. **Ordre de bataille** : refonte du theme + AppWindow d'abord (changements qui touchent toutes les scènes), puis scène par scène ? Ou prototyper d'abord la `CollectionMosaic` refondue car c'est elle qui valide l'approche libs-chart-réelles ?
6. **`DESIGN_SYSTEM.md` v2** : on l'écrit avant la refonte (spec pilote l'implémentation) ou après (extraction de la réalité une fois le code stabilisé) ? Recommandation : **avant**, en l'extrayant des screenshots du vrai produit.
7. **Render time** : passer aux vraies libs chart va probablement multiplier le temps de render. Acceptable jusqu'à quelle limite (actuellement 44s de vidéo en X minutes de render) ?
8. **Conformité brief original** : la refonte doit-elle préserver tel quel le storyboard (5 scènes, mêmes durées, mêmes copy lines) ou est-on aussi ouvert à revoir le rythme ?

## Success Criteria

- Quelqu'un qui a déjà utilisé Niamoto reconnaît l'app au premier coup d'œil sur chaque scène.
- La carte ressemble visuellement à `collections-nc-map-card.png`.
- La page payoff (Publish) ressemble visuellement à `site-taxon.png`.
- Aucun chart de type "donut" ou "gauge" — uniquement les types réellement présents dans le produit.
- `docs/DESIGN_SYSTEM.md` reflète la palette réelle, pas la palette du demo video éditorial.
- Brief R1-R15 du plan original toujours respecté (durée ~45s, curseur sur 2 interactions, endcard logo+wordmark, etc.).
