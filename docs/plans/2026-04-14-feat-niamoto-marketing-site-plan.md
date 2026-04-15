---
title: "feat: Niamoto marketing site (landing + pages compagnes)"
type: feat
date: 2026-04-14
brainstorm: null
precedes: déploiement niamoto.arsis.dev
---

# Niamoto Marketing Site

## Overview

Construire un site marketing pour Niamoto à partir de Stitch (Google Labs), en suivant le `docs/DESIGN_SYSTEM.md` et en s'appuyant sur les **assets existants** (logo, screenshots GUI, vidéo demo en cours). Le site comporte une **landing** + 3 pages compagnes (Documentation · Plugins · Showcase détaillé). Déploiement final sur `niamoto.arsis.dev`.

Projet Stitch créé : `projects/3994834925262801582` — "Niamoto"
Premier rendu landing téléchargé dans `.stitch/designs/landing/` (screenshot + index.html).

## Technical Approach

### Assets disponibles (à réutiliser, pas à regénérer)

**Logo** :
- `media/demo-video/public/logo/niamoto_logo.png` — 530 KB, version officielle
- Variante SVG construite dans `media/demo-video/src/ui/NiamotoLogo.tsx` (composant React vectoriel)

**Screenshots de l'app (23 captures)** — `docs/plans/caps/` :

| # | Fichier | Usage suggéré |
|---|---------|---------------|
| 01 | `01.splash-loading.png` | Optionnel — hero secondaire |
| 02 | `02.welcome-project-picker.png` | **Hero mockup** (écran d'accueil) |
| 05 | `05.project-create-ready.png` | Demo wizard |
| 06 | `06.dashboard-get-started.png` | Pillars — "Desktop app" section |
| 08 | `08.import-sources-review.png` | Pillar 1 — "Import any data" |
| 10 | `10.import-analysis-progress.png` | Animation / flux auto-config |
| 11 | `11.import-config-detected.png` | Pillar 1 — résultat auto-config |
| 13 | `13.data-dashboard-summary.png` | Proof of result |
| 15 | `15.collections-overview.png` | Pillar 2 — "Transform with plugins" |
| 16 | `16.collection-page.png` | Collection détaillée |
| 17 | `17.collections-widget-catalog.png` | Plugins page — grid de widgets |
| 19 | `19.collection-computation.png` | Pillar 2 — transforms en action |
| 21 | `21.site-builder-home-page.png` | **Hero mockup alternatif** (Site Builder) |
| 22 | `22.site-builder-methodology-page.png` | Showcase page |
| 25 | `25.publish-generation-preview.png` | Pillar 3 — "Publish a static portal" |
| 26-29 | `26-29.deploy-*.png` | Section déploiement / storytelling |

**Vidéo demo** (en cours de finalisation — `media/demo-video/`) :
- MP4 ~92.5s, 1920×1080, 30fps — 6 actes animés
- À intégrer en **hero secondaire** ou section dédiée avec contrôles (autoplay muted, loop optionnel)
- Fichier de sortie : `media/demo-video/out/niamoto-demo.mp4` (une fois rendu)

### Corrections du brief initial (à appliquer en Phase 1)

Le premier rendu Stitch a quelques écarts avec les attentes :

1. **"Used by research teams, parks, and environmental agencies"** → à remplacer par **section financeurs et utilisateurs**. Séparer clairement les deux :
   - **Financeurs** (bailleurs/partenaires institutionnels) — logos à récupérer
   - **Déployé pour / utilisé par** : mentionner les instances existantes et prévues :
     - Nouvelle-Calédonie (existant)
     - Gabon–Cameroun (prévu)
     - Guyane (prévu)
   - Format : map stylisée du monde avec marqueurs sur les 3 régions (steel blue pour "prévu", leaf green pour "actif"), ou simple strip de logos d'institutions

2. **Photos nature du showcase** → à remplacer par **screenshots de l'app** (depuis `docs/plans/caps/`) ou des mini-preview des portails réels

3. **Mockup Site Builder du hero** → utiliser directement le screenshot `21.site-builder-home-page.png` ou `02.welcome-project-picker.png` au lieu d'une illustration générée

### Financeurs & partenaires (récupérés depuis l'instance NC)

Les 9 logos sont copiés dans `docs/assets/funders/` avec manifest YAML détaillé (`docs/assets/funders/manifest.yaml`).

**Répartition proposée par rôle** (à confirmer avec Julien) :

| Rôle | Logo | Nom complet | URL |
|------|------|-------------|-----|
| **Financeurs** | `pn_100.png` | Province Nord | province-nord.nc |
| | `ps_100.png` | Province Sud | province-sud.nc |
| | `ofb_100.png` | OFB (Office Français de la Biodiversité) | ofb.gouv.fr |
| **Partenaires scientifiques** | `ird_100.png` | IRD | nouvelle-caledonie.ird.fr |
| | `cirad_100.png` | CIRAD | cirad.fr |
| | `amap_100.png` | UMR AMAP | amap.cirad.fr |
| | `iac_100.png` | IAC | iac.nc |
| **Partenaires données** | `endemia_100.png` | Endemia | endemia.nc |
| | `herbarium_100.png` | Herbier de Nouvelle-Calédonie | publish.plantnet-project.org |

**Instances Niamoto** :
- Nouvelle-Calédonie — **Actif** (portail en ligne, lead : Province Nord/Sud + IRD + IAC)
- Gabon – Cameroun — **Prévu** (partenaires à compléter)
- Guyane — **Prévu** (partenaires à compléter)

**Rendu retenu** : **1 strip unique "Nos partenaires"** (comme sur le portail NC actuel), avec les 9 logos alignés et centrés. Pas de séparation visuelle par rôle sur la landing — la taxonomie reste dans le manifest pour exploitation future (page /about/partners dédiée si besoin).

**Screenshots du portail NC** (source pour le showcase) :
- Home : `http://localhost:5173/api/site/preview-exported/fr/index.html` (dev server)
- Taxons : `http://localhost:5173/api/site/preview-exported/fr/taxons/index.html`
- À capturer en Phase 1 pour remplacer les photos nature du premier rendu Stitch.

---

## Implementation Phases

### Phase 1 — Itérer la landing

**Objectif** : atteindre une version "shippable" du premier écran avec les corrections ci-dessus.

- [ ] **Pass 1 — Financeurs & utilisateurs** : remplacer le trust strip générique par :
  - Section "Financé par" avec logos des bailleurs (ordre à définir)
  - Section "Déployé pour" avec map ou strip "Nouvelle-Calédonie · Gabon-Cameroun · Guyane" (badges status : Actif / En cours / Prévu)
  - Outil : `mcp__stitch__edit_screens`

- [ ] **Pass 2 — Showcase réel** : remplacer les 3 photos nature par :
  - Screenshot cadré du portail Nouvelle-Calédonie (ou mockup à défaut)
  - Mockups stylisés Gabon-Cameroun et Guyane (avec badge "Coming soon")
  - Conserver le format card (screenshot + nom + organisation)

- [ ] **Pass 3 — Hero mockup** : remplacer l'illustration générique par une intégration du screenshot `21.site-builder-home-page.png` ou `02.welcome-project-picker.png` (au choix selon impact visuel)

- [ ] **Pass 4 — Logo officiel** : s'assurer que le logo utilisé est bien `niamoto_logo.png` et pas une reconstruction Stitch

- [ ] **Pass 5 — Ajustements copy & densité** si nécessaire après review visuelle

- [ ] Télécharger la version finale dans `.stitch/designs/landing/v2/`

**Exit** : landing validée par l'utilisateur, prête à être exportée.

### Phase 2 — Pages compagnes

**Objectif** : étendre à un site multi-pages cohérent.

- [ ] **Documentation home** :
  - Hero "Documentation" + sub "Guides, references, and plugin recipes"
  - Sidebar TOC (Getting Started · Core Concepts · Plugins · Deployment · API)
  - Corps : liste des guides avec card (titre · description · temps estimé)
  - Outil : `generate_screen_from_text`
  - Référence visuelle : dashboards/docs comme Astro Docs, Nextra, Mintlify (mais version sobre)

- [ ] **Plugins showcase** :
  - Hero "Explore 50+ plugins for every ecological workflow"
  - Filter bar (Transformer · Widget · Loader · Exporter)
  - Grid 3 cols de plugin cards (nom · type badge · description · utilisé par X projets)
  - Référence screenshot : `17.collections-widget-catalog.png`

- [ ] **Showcase détaillé — 1 portail exemple (Nouvelle-Calédonie)** :
  - Hero du portail en grand
  - Stats : nombre de taxa, d'occurrences, de plots
  - Screenshots de sections clés du portail NC
  - Quote du responsable scientifique si dispo
  - CTA : "Visit the portal →" + "Build yours with Niamoto →"

- [ ] Télécharger les 3 écrans dans `.stitch/designs/{docs,plugins,showcase}/`

**Exit** : 4 pages cohérentes (landing + 3 compagnes), design system respecté.

### Phase 3 — Variantes & dark mode (optionnel)

**Objectif** : explorer des directions avant de figer.

- [ ] **Variantes du hero** — `generate_variants` avec 3 directions :
  - a) Minimaliste (juste titre + CTA, pas de mockup)
  - b) Dense (plus de social proof immédiat — stats clés, logos)
  - c) Editorial (gros mockup app, copy plus conceptuel)

- [ ] **Dark theme** de la landing finale via `apply_design_system` avec un thème dark (charcoal canvas, white text, green accents conservés)

- [ ] Décider : on garde light, dark, ou toggle user

**Exit** : choix validé pour la direction finale.

### Phase 4 — Intégration & déploiement

**Objectif** : site live sur un domaine Arsis.

- [ ] **Export HTML** des 4 écrans finaux via les fichiers dans `.stitch/designs/*/index.html`

- [ ] **Choix stack** :
  - a) **Astro** (recommandé — cohérent avec `arsis.dev` déjà en Astro 5.x, SEO propre, composants partagés faciles)
  - b) HTML statique simple + Tailwind (plus rapide si on n'ajoute rien)
  - c) Next.js (overkill sauf si on veut un blog dynamique)

- [ ] **Refactoring** :
  - Extraire design tokens CSS (via le DESIGN.md du Stitch project qui contient déjà les color named values)
  - Extraire header/footer en composants partagés
  - Extraire Button, Card, Pill primitives
  - Intégrer le logo `niamoto_logo.png` (ou version SVG dérivée)
  - Remplacer les placeholders par les screenshots réels de `docs/plans/caps/`
  - Intégrer la vidéo demo (hero secondaire ou section "Watch the demo")

- [ ] **Métadonnées** :
  - Open Graph (image = screenshot hero, description, titre)
  - Twitter Cards
  - favicon (dérivé du logo)
  - sitemap.xml + robots.txt

- [ ] **Deploy** :
  - Repo dédié `niamoto-site` dans `projects/arsis-niamoto-site/` ou sous-dossier de `niamoto/`
  - Dockerfile simple (Astro build + Caddy/Nginx static serve)
  - Déploiement sur le serveur Arsis via Coolify
  - Domaine : `niamoto.arsis.dev` (sous-domaine Arsis) ou achat `niamoto.io` si dispo
  - SSL auto via Coolify/Traefik

**Exit** : site accessible publiquement, lighthouse score ≥ 95 performance/a11y/best-practices/SEO.

### Phase 5 — Post-launch (optionnel)

- [ ] Analytics léger (Plausible ou Umami auto-hébergé)
- [ ] Section blog si on veut communiquer régulièrement (releases, cas d'usage)
- [ ] Page "Hire us" si le site fait aussi office de vitrine Arsis (Niamoto = projet de démonstration)

---

## Acceptance Criteria

### Functional
- [ ] Landing comporte les 8 sections du brief (Header, Hero, Financeurs/Users, Pillars, Showcase, Two ways, Open-source callout, Footer)
- [ ] Section "Déployé pour" mentionne bien Nouvelle-Calédonie, Gabon-Cameroun, Guyane avec statuts distincts
- [ ] Logo Niamoto officiel utilisé partout (pas de reconstruction IA)
- [ ] Screenshots réels de l'app intégrés (pas de photos nature génériques)
- [ ] Vidéo demo intégrée (quand disponible)
- [ ] 3 pages compagnes fonctionnelles (Documentation, Plugins, Showcase)
- [ ] Navigation cohérente entre les pages

### Technical
- [ ] Respect strict du `docs/DESIGN_SYSTEM.md` (couleurs, typo, espacement)
- [ ] Responsive : mobile < 768px, tablet 768-1024, desktop 1024+
- [ ] Performance : TTI < 2s sur desktop 3G, images optimisées (WebP + fallback)
- [ ] A11y : contraste WCAG AA, labels ARIA sur tous les CTAs, navigation clavier
- [ ] SEO : meta tags, Open Graph, sitemap, schema.org Organization
- [ ] Site buildable en CI (Docker build < 2 min)

### Quality
- [ ] Tous les liens fonctionnels (pas de `href="#"` en prod)
- [ ] Copy relu : pas d'emojis, pas de "revolutionary", ton scientifique sobre
- [ ] Deploy reproductible (Dockerfile committé, secrets en env vars Coolify)

---

## Assets à produire (hors Stitch)

- [x] **Logos partenaires/financeurs** — 9 logos récupérés depuis l'instance NC → `docs/assets/funders/` avec `manifest.yaml`
- [x] **Screenshots de l'app** — 23 captures disponibles dans `docs/plans/caps/` (voir mapping ci-dessus)
- [x] **Logo Niamoto officiel** — `media/demo-video/public/logo/niamoto_logo.png` (1.5 MB) + version HD dans l'instance NC
- [ ] **Screenshot portail NC live** — à capturer une fois le portail NC accessible publiquement (sinon utiliser `21.site-builder-home-page.png` en fallback)
- [ ] **Mockups Gabon-Cameroun et Guyane** — placeholders stylisés avec badge "Prévu 2026" (Stitch peut les générer)
- [ ] **Vidéo demo finalisée** — MP4 optimisé web (H.264, 1080p, ~92s) + poster frame (en cours, plan `2026-04-13-feat-demo-video-motion-graphics-plan.md`)
- [ ] **Favicon** SVG + PNG 32x32 + apple-touch-icon 180x180 (dérivés du logo)
- [ ] **Social cards** — Open Graph 1200x630, Twitter 1200x600 (screenshots du hero)

---

## Dependencies & Risks

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Logos financeurs indisponibles | Section vide ou placeholder moche | Demander à Julien la liste + récupérer depuis sites officiels si besoin |
| Portails Gabon-Cameroun/Guyane pas encore live | Showcase peu crédible | Badges "Coming 2026" assumés, focus sur NC |
| Vidéo demo pas prête pour le launch | Manque un élément visuel fort | Launch sans, intégrer en v1.1 |
| Stitch génère des variantes qui dévient du DS | Incohérence visuelle | `apply_design_system` après chaque génération + review |
| Domaine `niamoto.io` non dispo | Revenir sur `niamoto.arsis.dev` | Vérifier whois tôt, fallback préparé |

---

## Timing Estimate

| Phase | Durée | Dépendances |
|-------|-------|-------------|
| Phase 1 — Itérer landing | 1-2h | Logos financeurs dispo |
| Phase 2 — Pages compagnes | 2-3h | Phase 1 terminée |
| Phase 3 — Variantes & dark (opt.) | 1h | Phase 2 terminée |
| Phase 4 — Intégration & deploy | 2-3h | Toutes les phases précédentes |
| **Total** | **6-9h** | Sessions 1-2h préférable |

---

## References

### Internal
- Design system : `docs/DESIGN_SYSTEM.md`
- Screenshots app : `docs/plans/caps/*.png`
- Vidéo demo : `media/demo-video/` (plan : `docs/plans/2026-04-13-feat-demo-video-motion-graphics-plan.md`)
- Logo : `media/demo-video/public/logo/niamoto_logo.png`
- Fidelity mapping : `docs/plans/caps/video-fidelity-mapping.md`

### Stitch
- Project : `projects/3994834925262801582` (Niamoto)
- Screen v1 : `projects/3994834925262801582/screens/3a13f3b146c840ac8f336ea0724fc11f`
- Design system généré : "Niamoto Ecological" / "The Living Laboratory"
- Assets locaux : `.stitch/designs/landing/`

### External
- [Stitch docs](https://stitch.withgoogle.com/docs)
- [Astro 5.x docs](https://docs.astro.build) (stack recommandé)
- Inspiration landing : [Remotion](https://remotion.dev) · [Tauri](https://tauri.app) · [Astro](https://astro.build)
