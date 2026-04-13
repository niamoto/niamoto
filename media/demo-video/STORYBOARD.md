# Niamoto Demo Video — Storyboard

**Composition** : MarketingLandscape (1920x1080 @ 30fps)
**Durée totale** : ~115 secondes (~3450 frames)
**Thème visuel** : frond (brand Niamoto)
**Palette** : charcoal #1E1E22, forest green #2E7D32, light green #4BAF50, steel blue #3FA9F5

---

| # | Scène | Composant | Durée (s) | Frames | Support | Transition entrée |
|---|-------|-----------|-----------|--------|---------|-------------------|
| 1 | Intro Logo | `IntroLogo` | 3 | 90 | Remotion | fade in |
| 2 | Problème | `PipelineAnimated` (mode texte) | 5 | 150 | Remotion typo cinétique | fade |
| 3 | Pipeline animé | `PipelineAnimated` | 7 | 210 | Remotion | fade |
| 4 | Import | `ScreencastBlock` | 25 | 750 | Screencast `01-import-flow.mp4` | slide from-right |
| 5 | Transform | `ScreencastBlock` | 30 | 900 | Screencast `02-transform-preview.mp4` | fade |
| 6 | Export | `ScreencastBlock` | 25 | 750 | Screencast `03-publish-or-site-preview.mp4` | fade |
| 7 | Respiration | `StatsOrMap` | 10 | 300 | Remotion | fade |
| 8 | Outro CTA | `OutroCTA` | 10 | 300 | Remotion | fade |

**Total** : ~115s (~3450 frames, ajusté par les transitions)

---

## Direction visuelle

- **Fond** : charcoal sombre (#1E1E22) pour les scènes Remotion
- **Texte** : Plus Jakarta Sans, blanc ou light green
- **Accents** : forest green pour les éléments actifs, steel blue pour les liens
- **Screencasts** : GUI capturée en thème `frond`, fenêtre centrée avec léger padding sombre
- **Transitions** : fade 15 frames entre scènes Remotion, slide pour l'entrée des screencasts
- **Aucun effet décoratif gratuit** : pas de particules, pas de glow, pas de 3D

---

## Assets requis

### Screencasts (à capturer manuellement)
- [ ] `public/screencasts/01-import-flow.mp4` — 25s, import de données
- [ ] `public/screencasts/02-transform-preview.mp4` — 30s, widgets et preview
- [ ] `public/screencasts/03-publish-or-site-preview.mp4` — 25s, export et site

### Musique
- [ ] `public/music/track.mp3` — piste unique, ambiance tech/nature, ~2 min

### Logo
- [x] `public/logo/niamoto_logo.png` — logo Niamoto

### Fonts
- [x] `public/fonts/plus-jakarta-sans/` — font display (frond)
- [x] `public/fonts/jetbrains-mono/` — font mono
- [x] `public/fonts/inter/` — font body alternative
