---
title: Pipeline vidéo de démo Niamoto avec Remotion (MVP marketing d'abord)
type: feat
date: 2026-04-08
status: draft
owner: Julien Barbe
---

# Pipeline vidéo de démo Niamoto avec Remotion

## Overview

Produire un **projet Remotion réutilisable** pour les vidéos de démo Niamoto, avec une stratégie volontairement resserrée :

1. **MVP prioritaire** : une **vidéo marketing 16:9** pour `arsis.dev`, courte, soignée, compréhensible sans audio
2. **Suite optionnelle** : déclinaisons **social vertical** et **social carré** à partir du matériau validé
3. **Suite plus tardive** : **tutoriel onboarding** long si le besoin se confirme

La vidéo pour le **GBIF Ebbe Nielsen Challenge 2026** reste **hors scope** de ce plan. Elle pourra réutiliser l'infrastructure créée ici, mais ne doit pas dicter le scope du MVP.

**Approche retenue** : hybride *screencast + scènes Remotion animées*, sans voix-off, avec typographie cinétique et une seule piste musicale.

## Problem Statement / Motivation

Niamoto a désormais un niveau de maturité suffisant pour justifier une vidéo de démonstration sérieuse, mais le produit n'a aujourd'hui aucun support vidéo clair pour :

- la landing `arsis.dev`
- la présentation rapide du workflow Import → Transform → Export
- les futures annonces produit sur les réseaux

Le vrai problème n'est pas de "faire plusieurs vidéos". Le vrai problème est de produire **une première vidéo marketing crédible**, rapidement itérable, sans partir dans un mini studio vidéo à gérer.

**Contrainte structurante** : pas de voix-off. Le message doit passer en muet, avec des scènes visuellement lisibles et peu de texte.

## Decision Summary

### Ce que ce plan engage

- créer un projet `media/demo-video/` autonome
- produire **une composition marketing 16:9** comme livrable principal
- bâtir **quelques scènes réutilisables** qui pourront ensuite servir aux formats sociaux
- s'appuyer sur l'instance **`test-instance/niamoto-nc`** pour les captures

### Ce que ce plan ne doit pas engager tout de suite

- un pipeline complet pour 3 formats en parallèle
- un système d'assets externe avant d'avoir prouvé le besoin
- une vidéo tutorielle longue
- une narration orientée GBIF / DwC-A si elle ne reflète pas encore le produit mis en avant

## Proposed Solution

### Architecture globale

Créer un projet Remotion autonome dans `media/demo-video/`, séparé du front principal `src/niamoto/gui/ui`, qui consomme :

1. des **screencasts** capturés de l'app Tauri
2. des **scènes animées Remotion** pour le branding et les transitions de sens
3. des **assets locaux** déjà présents dans le repo quand c'est possible
4. une **piste musicale unique**

Le MVP ne nécessite qu'**une composition master** :

- `MarketingLandscape` en 1920×1080

Les compositions sociales ne seront ajoutées **qu'après validation** du montage marketing.

### Pourquoi Remotion reste le bon choix

| Critère | Remotion | Éditeur vidéo classique |
|---|---|---|
| Itération rapide | ✅ rechargement live | ❌ rendu manuel récurrent |
| Versioning | ✅ code Git | ❌ projets binaires |
| Réutilisation de scènes | ✅ naturelle | ❌ duplication de timeline |
| Alignement avec la stack Niamoto | ✅ React / TS déjà maîtrisés | ❌ hors stack |
| Régénération après évolution GUI | ✅ simple | ❌ coûteuse |

Pour Niamoto, Remotion reste le meilleur compromis. Le point important est simplement de **réduire le nombre de scènes et de formats au départ**.

### Principe de réutilisation

Les scènes doivent être conçues dès le départ pour être redéployables :

- dimensions pilotées par `useVideoConfig()`
- timings passés par props ou config typée
- aucune dépendance à une composition spécifique

En revanche, le MVP n'a pas besoin d'un paramétrage exhaustif. Une **config TypeScript simple** suffit au début. Le Zod avancé peut venir ensuite si l'édition par sidebar studio apporte une vraie valeur.

## Scope

### In scope

- projet Remotion initialisé et documenté
- une vidéo marketing 16:9 finalisée
- 3 à 5 scènes réutilisables maximum
- 3 screencasts principaux maximum
- 1 piste musicale

### Out of scope for MVP

- tutoriel de 5 à 10 minutes
- pipeline multi-langue
- voix-off générée ou humaine
- système de téléchargement d'assets distants
- publication CDN définitive
- storytelling GBIF dédié

## Technical Approach

### Stack et bootstrap

```bash
cd /Users/julienbarbe/Dev/clients/niamoto
mkdir -p media/demo-video
cd media/demo-video
pnpm create video@latest . --template hello-world
```

### Dépendances recommandées pour le MVP

- `remotion`
- `@remotion/cli`
- `@remotion/transitions`
- `zod` uniquement si utile pour quelques configs

### Dépendances à différer

- `@remotion/player`
- `@remotion/zod-types`
- `@remotion/google-fonts`
- toute brique voix-off / sous-titrage automatique / 3D

Le repo possède déjà des polices locales dans [src/niamoto/gui/ui/public/fonts/fonts.css](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/public/fonts/fonts.css#L1). Le projet vidéo doit partir de là plutôt que réinventer un système de fonts.

### Arborescence cible

```text
media/
└── demo-video/
    ├── package.json
    ├── tsconfig.json
    ├── remotion.config.ts
    ├── README.md
    ├── SCRIPT.md
    ├── STORYBOARD.md
    ├── public/
    │   ├── screencasts/
    │   ├── music/
    │   ├── logo/
    │   ├── fonts/
    │   └── maps/
    ├── src/
    │   ├── Root.tsx
    │   ├── compositions/
    │   │   └── MarketingLandscape.tsx
    │   ├── scenes/
    │   │   ├── IntroLogo.tsx
    │   │   ├── PipelineAnimated.tsx
    │   │   ├── ScreencastBlock.tsx
    │   │   ├── StatsOrMap.tsx
    │   │   └── OutroCTA.tsx
    │   └── shared/
    │       ├── theme.ts
    │       ├── fonts.ts
    │       └── config.ts
    └── out/
```

Les compositions `SocialVertical`, `SocialSquare` et `Tutorial` n'ont pas besoin d'être scaffoldées immédiatement.

## Visual Direction

### Source de vérité visuelle

Le plan doit se caler sur les thèmes existants sous [src/niamoto/gui/ui/src/themes/presets](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/themes/presets).

Les candidats les plus crédibles aujourd'hui sont :

- `frond` : thème de marque Niamoto, propre, lisible, déjà aligné avec les couleurs du logo
- `tidal` : plus cartographique et structuré, pertinent si la vidéo insiste sur la carte, les couches ou l'analyse spatiale
- `ink` : plus éditorial et radical, intéressant pour une communication très sobre mais moins naturel pour une démo produit

Le preset `field` cité dans la version précédente du plan **n'existe pas** dans le code actuel. Il ne faut pas baser la direction visuelle sur ce nom.

### Recommandation

Pour le MVP marketing, je recommande :

- **GUI capturée en `frond`** pour coller à l'identité de marque Niamoto
- **overlays vidéo plus sobres** que le thème applicatif, pour éviter l'effet trop décoratif
- **`tidal` comme plan B** si la narration finale s'oriente davantage vers la cartographie et la structure de données

Alternative acceptable :

- **`ink`** pour un teaser plus éditorial ou une landing très minimaliste, mais probablement pas comme thème principal de capture

## Capture Plan

### Outil

Utiliser `ffmpeg` avec AVFoundation sur macOS, ou QuickTime si nécessaire.

### Lancement de l'app

Le chemin de lancement correct dans le repo est :

```bash
./scripts/dev/dev_desktop.sh test-instance/niamoto-nc
```

Le script existe bien dans [scripts/dev/dev_desktop.sh](/Users/julienbarbe/Dev/clients/niamoto/scripts/dev/dev_desktop.sh#L1), mais il **ne documente pas aujourd'hui** de flag `--window-size 1920x1080` côté commande utilisateur. Le plan ne doit donc pas promettre cette option tant qu'elle n'est pas réellement disponible.

### Règles de capture

- fenêtre Tauri cadrée en 16:9 de manière cohérente avant enregistrement
- notifications système coupées
- clips courts, ciblés, de 8 à 20 secondes
- mouvements de souris lents et lisibles
- captures limitées aux moments qui racontent vraiment le produit

### Screencasts à prévoir pour le MVP

- `01-import-flow.mp4`
- `02-transform-preview.mp4`
- `03-publish-or-site-preview.mp4`

Si un quatrième clip s'impose, il doit remplacer un autre, pas s'ajouter mécaniquement.

## Scene Design

Le MVP doit rester frugal. Cinq briques suffisent :

### `IntroLogo.tsx`

- apparition du logo
- tagline très courte
- durée cible : 2 à 3 secondes

### `PipelineAnimated.tsx`

- schéma simple Import → Transform → Export
- animation lisible sans fioritures
- durée cible : 5 à 7 secondes

### `ScreencastBlock.tsx`

- composant standard pour intégrer un clip
- trim début / fin
- léger habillage
- callouts ponctuels uniquement quand ils évitent une ambiguïté

### `StatsOrMap.tsx`

Une seule scène de respiration visuelle au milieu ou à la fin :

- soit une scène stats
- soit une scène carte NC

Le MVP n'a pas besoin des deux si cela dilue le récit.

### `OutroCTA.tsx`

- logo
- `arsis.dev`
- GitHub si utile
- 2 à 3 secondes

## Storytelling du MVP

### Positionnement

La vidéo marketing doit montrer **le produit actuel**. Elle peut suggérer l'ambition, mais ne doit pas reposer sur un usage futur comme pivot narratif.

En particulier, la mention explicite d'un import **DwC-A** au cœur du storyboard doit être retirée du MVP si ce n'est pas la démonstration produit la plus claire aujourd'hui.

### Storyboard recommandé

| # | Scène | Durée cible | Support |
|---|---|---:|---|
| 1 | Intro logo | 0:00-0:03 | Remotion |
| 2 | Problème en une phrase | 0:03-0:08 | Typo cinétique |
| 3 | Pipeline animé | 0:08-0:15 | Remotion |
| 4 | Import | 0:15-0:40 | Screencast |
| 5 | Transform / preview / widgets | 0:40-1:10 | Screencast |
| 6 | Export / site / portail | 1:10-1:35 | Screencast |
| 7 | Scène de respiration stats ou carte | 1:35-1:45 | Remotion |
| 8 | Outro CTA | 1:45-1:55 | Remotion |

### Cible de durée

- **objectif** : 90 à 120 secondes
- **borne haute tolérée** : 150 secondes
- **à éviter** : 3 min 30 pour une landing page

## Implementation Phases

### Phase 0 — Préparation et cadrage du MVP

**Livrables :**

- [x] Créer `media/demo-video/`
- [x] Rédiger `SCRIPT.md` en version courte
- [x] Rédiger `STORYBOARD.md` avec 8 scènes max
- [x] Choisir le thème de capture : `frond`, `tidal` ou `ink`
- [ ] Vérifier les écrans réellement montrables dans `test-instance/niamoto-nc`
- [x] Localiser le logo et les fonts réutilisables
- [ ] Sélectionner une piste musicale

**Acceptance :**

- script court validé
- storyboard figé avant toute capture
- décision visuelle prise

### Phase 1 — Bootstrap Remotion + primitives

**Livrables code :**

- [x] projet `media/demo-video` initialisé
- [x] `.gitignore` local
- [x] `Root.tsx`
- [x] `shared/theme.ts`
- [x] `shared/fonts.ts`
- [x] `shared/config.ts`
- [x] `IntroLogo.tsx`
- [x] `PipelineAnimated.tsx`
- [x] `ScreencastBlock.tsx`
- [x] `StatsOrMap.tsx`
- [x] `OutroCTA.tsx`
- [x] `README.md`

**Tests manuels :**

- [x] `pnpm run dev` ouvre le studio
- [x] chaque scène rend isolément
- [x] les polices locales chargent correctement

**Acceptance :**

- studio fonctionnel
- scènes de base prêtes
- aucune vidéo finale encore attendue

### Phase 2 — Vidéo marketing MVP

**Livrables :**

- [x] `MarketingLandscape.tsx`
- [ ] 3 screencasts capturés puis trimmés
- [ ] intégration d'une piste audio
- [ ] enchaînement final 90-120 s
- [ ] premier rendu complet dans `out/`
- [ ] 2 à 3 itérations visuelles maximum avant validation

**Acceptance :**

- un fichier marketing 1080p finalisé
- message compréhensible en muet
- récit clair et concis

### Phase 3 — Déclinaisons sociales après validation du marketing

**Conditions d'entrée :**

- le montage marketing est validé
- les scènes réutilisables tiennent bien le recadrage

**Livrables :**

- [ ] `SocialVertical.tsx`
- [ ] `SocialSquare.tsx`
- [ ] adaptation typographique
- [ ] recadrage des screencasts réellement nécessaires

**Acceptance :**

- deux exports lisibles sans audio
- aucun ajout de fond de récit non présent dans la marketing

### Phase 4 — Tutoriel onboarding si besoin confirmé

Cette phase reste optionnelle. Elle n'entre pas dans la définition de succès du MVP.

### Phase 5 — Diffusion et intégration

**Livrables possibles :**

- [ ] intégration sur `arsis.dev`
- [ ] lien depuis le README
- [ ] documentation média minimale

La question du stockage externe des assets vidéo ne doit être tranchée **qu'après** avoir un premier corpus réel de captures. Pas avant.

## Alternative Approaches Considered

### Alternative 1 — Tout faire d'un coup

**Rejetée** : trop de fronts ouverts, risque élevé de fatigue de production, trop peu de signal produit rapidement.

### Alternative 2 — Faire uniquement des screencasts bruts

**Rejetée** : trop faible niveau de finition pour une landing et trop peu de maîtrise du rythme.

### Alternative 3 — Faire directement un gros tutoriel

**Rejetée** : ce n'est pas le besoin principal. Il faut d'abord produire un artefact marketing court, partageable et publiable.

## Acceptance Criteria

### Fonctionnel

- [ ] `pnpm run dev` démarre sans erreur dans `media/demo-video/`
- [ ] `MarketingLandscape` rend un MP4 sans erreur
- [ ] au moins 3 scènes réutilisables existent et sont isolables dans le studio
- [ ] la vidéo finale marketing existe en 1080p

### Non-fonctionnel

- [ ] la vidéo fonctionne **sans audio**
- [ ] la durée reste <= 150 secondes
- [ ] les polices affichées sont cohérentes avec la direction retenue
- [ ] le projet reste compréhensible pour une itération future

### Qualité visuelle

- [ ] peu de texte à l'écran
- [ ] aucun effet décoratif gratuit
- [ ] transitions propres
- [ ] cohérence visuelle entre overlays et GUI capturée

## Success Metrics

- **Primaire** : une vidéo marketing intégrable sur `arsis.dev`
- **Secondaire** : une base saine pour dériver les formats sociaux
- **Tertiaire** : une infrastructure réutilisable plus tard pour une vidéo GBIF

## Dependencies & Risks

### Dépendances externes

- logo exploitable
- piste musicale exploitable
- instance `test-instance/niamoto-nc` stable

### Risques techniques

| Risque | Impact | Mitigation |
|---|---|---|
| Captures floues ou molles | Élevé | Capturer peu, recapturer vite, ralentir les gestes |
| Trop de texte faute de voix-off | Élevé | Script ultra court, max une idée par scène |
| Mismatch entre GUI et overlays | Moyen | Repartir des thèmes réels du repo |
| Départ dans un pipeline trop abstrait | Moyen | Garder une seule composition jusqu'à validation |
| Repo alourdi par les `.mp4` | Moyen | ignorer localement au début, décider ensuite |

### Risques de produit

- raconter une promesse future au lieu du produit actuel
- faire une vidéo trop longue pour son canal principal
- surinvestir le pipeline avant d'avoir un premier rendu convaincant

## Resource Requirements

- React / TypeScript : acquis
- Remotion : apprentissage raisonnable
- sens du montage : itératif, à garder simple
- `ffmpeg` : utile mais non bloquant si QuickTime suffit pour un premier jet

## Future Considerations

- ajouter `SocialVertical` et `SocialSquare`
- ajouter une config plus paramétrable si la réédition devient fréquente
- ajouter une version tutorielle
- ajouter plus tard une version GBIF dédiée

## Documentation Plan

- [ ] `media/demo-video/README.md`
- [ ] `media/demo-video/SCRIPT.md`
- [ ] `media/demo-video/STORYBOARD.md`
- [ ] `media/demo-video/ASSETS.md` si des sources externes sont réellement utilisées

## References & Research

### Références repo

- [scripts/dev/dev_desktop.sh](/Users/julienbarbe/Dev/clients/niamoto/scripts/dev/dev_desktop.sh#L1)
- [src/niamoto/gui/ui/public/fonts/fonts.css](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/public/fonts/fonts.css#L1)
- [src/niamoto/gui/ui/src/themes/presets/frond.ts](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/themes/presets/frond.ts#L1)
- [src/niamoto/gui/ui/src/themes/presets/tidal.ts](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/themes/presets/tidal.ts#L1)
- [src/niamoto/gui/ui/src/themes/presets/ink.ts](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/themes/presets/ink.ts#L1)
- [docs/plans/2026-03-11-feat-gbif-ebbe-nielsen-challenge-2026-opportunity-report.md](/Users/julienbarbe/Dev/clients/niamoto/docs/plans/2026-03-11-feat-gbif-ebbe-nielsen-challenge-2026-opportunity-report.md#L1)

### Références externes

- [Remotion docs](https://www.remotion.dev/docs/)
- [Remotion Studio](https://www.remotion.dev/docs/studio)
- [Remotion transitions](https://www.remotion.dev/docs/transitions)

### Notes de cadrage

- priorité réelle : marketing d'abord
- objectif réel : une vidéo publiable, pas un framework vidéo complet
- stratégie : prouver le rendu, puis élargir
