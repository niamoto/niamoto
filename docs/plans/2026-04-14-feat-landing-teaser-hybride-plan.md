---
title: "feat: Landing teaser hybride — screen recording réel + Remotion compositor + audio"
type: feat
status: alternative
active_plan: docs/plans/2026-04-14-feat-landing-teaser-refonte-plan.md
date: 2026-04-14
origin: docs/brainstorms/2026-04-14-landing-teaser-refonte-brainstorm.md
parent_plan: docs/plans/2026-04-14-feat-landing-teaser-video-plan.md
revised: 2026-04-15
---

> **Plan maintenu comme alternative** — 2026-04-15 l'utilisateur a préféré l'approche mocks JSX (plan refonte) plutôt que screen recording. Ce plan reste archivé comme option de repli si les mocks ne tiennent pas la route techniquement ou visuellement en Phase 2 de la refonte. Les décisions locked (CTA, hook, taxon, audio, etc.) restent partagées entre les deux plans.

# feat: Landing teaser hybride — screen recording réel + Remotion compositor + audio

## Overview

Refondre le landing teaser Niamoto selon l'approche **hybride 2026** documentée pour les teasers produit B2B SaaS : **screen recording réel** du GUI Tauri et du site publié + **Remotion** comme compositeur (overlay motion design pour intro/outro/cartouches) + **audio** (musique fond + SFX sur les beats clés).

Cette approche remplace la refonte mocks JSX (plan superseded) après que la recherche indépendante a montré que :
1. Les meilleurs teasers B2B (Linear, Vercel, Stripe, Loom, Notion, Figma) sont **majoritairement des screen recordings du vrai produit**, pas du motion design pur.
2. **L'audio est non-négociable** — sans SFX sur les beats, même une vidéo bien composée semble plate par comparaison.
3. Pour un produit avec une **interface visuelle réelle** comme Niamoto (GUI Tauri + site publié riche), reconstruire en JSX est un combat perdu d'avance vs. capturer le vrai.

## Why This Approach (lecture pédagogique pour comprendre les choix)

### Le code-as-video (Remotion mocks) n'est pas le bon outil pour ce job

Remotion brille quand : (a) la vidéo doit être paramétrable / data-driven, (b) le contenu n'a pas de représentation visuelle "réelle" déjà existante, (c) on a besoin de contrôle frame-par-frame sur des animations qui n'existent pas dans le produit. **Niamoto ne coche aucun de ces critères** : son interface existe déjà, elle est visuellement riche, et un teaser landing n'a pas besoin d'être paramétrable.

### Le pattern hybride dominant 2026

Les teasers de référence (URL dans `References`) suivent tous une structure 4-actes :

| Acte | Durée | Contenu | Outil principal |
|------|-------|---------|-----------------|
| 1. Douleur / accroche | 0–8 s | Texte animé sur fond visuel ; pose le problème | Motion design (Remotion) |
| 2. Solution en action | 8–35 s | Screen recording du vrai produit | OBS / ScreenFlow |
| 3. Résultat / payoff | 35–50 s | Screen recording du livrable (site publié) | OBS / ScreenFlow |
| 4. CTA + signature | 50–60 s | Logo + URL + accroche | Motion design (Remotion) |

Remotion devient **un compositeur** : il assemble les MP4 capturés via `<OffthreadVideo>`, ajoute les overlays (cartouches éditoriaux courts, transitions, intro/outro), gère les fades et la sync audio.

### Pourquoi l'audio change tout

Sans son, même un screen recording propre paraît mort. Avec :
- une **musique de fond** instrumentale "propre et déterminée" (catégorie minimal corporate / documentary / ambient progressive sur Artlist)
- des **SFX UI** (clicks, soft pops sur reveal, swoosh sur transitions de scène)

…on passe d'une « démo froide » à une « expérience produit ». Coût : ~200 €/an Artlist, mixage gratuit dans DaVinci Resolve.

### Brief original R1-R15 — ce qui change

| Req | Décision |
|-----|----------|
| R1 (asset distinct walkthrough) | ✅ préservé |
| R2 (`Import. Structure. Publish.`) | ✅ **Hybride préservé** — nouveau hook user-centric en Acte 1 (« Vos données terrain. Dispersées, illisibles. ») + `Import. Structure. Publish.` conservé comme tagline marque en Acte 4 sous le logo |
| R3 (sobre, crédible, scientifique, éditorial) | ✅ préservé — choix musique aligné |
| R4 (~45 s) | 🔁 Étendu à **50–60 s** (durée optimale documentée pour landing B2B 2026) |
| R5 (phrase éditoriale avant interface) | ✅ préservé — c'est l'Acte 1 |
| R6 (transformation, pas démo exhaustive) | ✅ préservé |
| R7 (mosaïque collection comme centre visuel) | ✅ préservé — Acte 3 |
| R8 (page taxon publiée comme payoff) | ✅ préservé — Acte 3 |
| R9 (mix interface + cartouches courts) | ✅ préservé — overlay Remotion |
| R10 (générique, pas NC explicite) | ⚠ **Tension** — un screen recording du vrai produit montrera des taxons NC. Acceptable si on évite le mot « Nouvelle-Calédonie » dans les overlays |
| R11/R12 (curseur sur 2 interactions) | 🔁 N/A — le curseur sera **celui du screen recording**, plus contrôlable en code |
| R13 (anglais d'abord) | ✅ préservé |
| R14 (pas de voix off) | ✅ préservé |
| R15 (endcard sans URL ni CTA) | ❌ **Renversé (validé)** — Acte 4 = logo + tagline marque + accroche + bouton CTA `niamoto.org`. Best practice conversion B2B 2026 prime sur le brief original |

## Storyboard détaillé en 4 actes

### Acte 1 — La douleur (0–8 s) | Motion design Remotion

**Intention** : poser le problème en 5 secondes pour qu'un visiteur scientifique se reconnaisse. Pas de produit visible.

**Visuel** : fond sombre vert profond `#0a1f0a` ou noir. Texte typo serif scientifique (Plus Jakarta Sans déjà installée OK) qui apparaît mot à mot.

**Texte (lock)** :
- 0–4 s : « Vos données terrain. CSV, GPS, photos, références. »
- 4–7 s : « Dispersées. Illisibles pour ceux qui en ont besoin. »
- 7–8 s : transition vers Acte 2

> Note : le hook user-centric reste à itérer en Phase 2 (test de formulation avant capture). Alternatives à évaluer : « Vos données terrain. Précieuses. Mais invisibles. » / « Des années de données. Et personne ne peut les consulter. »

**SFX** : « pop » discret à chaque mot apparaissant, « swoosh » grave sur la transition.

### Acte 2 — La solution en action (8–35 s) | Screen recording GUI Tauri

**Intention** : montrer le workflow réel du produit en 3 beats de ~9 s.

**Beat 2.1 (8–17 s) — Import** : capture du vrai GUI Niamoto. L'utilisateur drag des fichiers dans la zone d'import. La progression bar avance. Les fichiers apparaissent triés (occurrences.csv, plots.csv, etc.).

**Beat 2.2 (17–26 s) — Configuration** : navigation vers Collections. Sélection d'un widget « Carte distribution ». Le widget est ajouté. Un autre, et un autre. Mosaïque qui se construit.

**Beat 2.3 (26–35 s) — Preview** : bascule sur le panneau preview. La page taxon se rend en live avec sa carte NC, ses charts, sa sidebar.

**Overlay Remotion** : un seul cartouche par beat, max 4 mots, en bas de cadre :
- Beat 2.1 : « Import en un drop. »
- Beat 2.2 : « Configurez vos widgets. »
- Beat 2.3 : « Aperçu instantané. »

**SFX** : clicks UI naturels du screen recording (à laisser) + un "ping" doux sur chaque cartouche.

### Acte 3 — Le payoff (35–50 s) | Screen recording site publié

**Intention** : montrer le livrable qui justifie tout le travail. Le moment "wow".

**Beat 3.1 (35–42 s)** : le site publié charge dans un navigateur. Header vert Niamoto. Sidebar taxonomique. La page taxon `Olea paniculata` (ou autre vedette) s'affiche.

**Beat 3.2 (42–48 s)** : zoom doux (post-prod) sur la carte NC interactive. Hover sur une bubble — popup avec count d'occurrences. Scroll doux vers les charts (DBH, phénologie).

**Beat 3.3 (48–50 s)** : pause de respiration. Cadre fixe sur la page complète. Le spectateur réalise.

**Overlay Remotion** : aucun cartouche — on laisse le produit parler (pattern Figma). Optionnel : « Site public, statique, partageable. » à 47 s en bas.

**SFX** : un "swell" musical doux qui monte vers 42 s, retombe à 50 s.

### Acte 4 — CTA & signature (50–60 s) | Motion design Remotion

**Intention** : convertir l'intérêt en action.

**Visuel** : transition douce vers fond clair `#f9fafb`. Logo Niamoto centré. Tagline marque en signature. Une ligne d'accroche. Un bouton CTA vert `#228b22`.

**Texte (lock)** :
- 50–54 s (apparition stagger) :
  - Logo Niamoto (animation du logo en signature)
  - Tagline marque : **« Import. Structure. Publish. »** (sous le logo, sobre)
- 54–57 s : apparition de l'accroche + bouton
  - Accroche : « Open source. Auto-hébergeable. »
  - Bouton CTA : **« niamoto.org »** sur fond vert `#228b22`, texte blanc, coins arrondis, style Niamoto
- 57–60 s : **hold statique** 3 s sur la composition complète pour permettre lecture / clic. **Pas de loop seamless** — quand la vidéo redémarre (autoplay loop), le contraste Acte 4 clair → Acte 1 sombre est assumé.

**SFX** : « ding » doux à l'apparition du logo, « pop » discret sur le bouton CTA, silence sur les 3 dernières secondes pour laisser respirer.

## Technical Approach

### Phase 1 — Préparer une instance test « photogénique » (~3h)

L'instance dont on capture détermine 80% du résultat visuel. Préparer minutieusement.

**Deliverables** :
- Choix du **projet vedette** : `test-instance/niamoto-nc/` (déjà riche, Olea paniculata + Araucariaceae bons candidats)
- **Préparation cosmétique** :
  - Vérifier que les exports `test-instance/niamoto-nc/exports/web/` sont à jour (régénérer si besoin via `niamoto run`)
  - Charger un dataset visuellement dense (minimum 50 occurrences pour avoir des bubbles lisibles sur la carte)
  - Choisir un taxon vedette avec : (a) hiérarchie taxonomique riche pour la sidebar, (b) distribution DBH multi-bins jolie, (c) phénologie 12 mois cohérente
  - Le projet doit avoir un nom générique (pas « Test Julien 2025 ») — renommer si nécessaire
- **Préparation interface** :
  - Macbook avec écran propre (résolution 1920×1080 minimum, idéalement 2880×1800 retina pour downscale propre)
  - Désactiver toutes les notifications système (`Do Not Disturb` + System Settings → Notifications)
  - Cacher la barre menu / dock pendant la capture (System Settings → Dock & Menu Bar → autohide)
  - Curseur agrandi via Accessibility (taille 2-3) pour visibilité dans la vidéo
  - Police système à taille standard
  - Clean desktop (zéro icône)
  - Browser : profil incognito ou nouveau profil sans extensions, taille fenêtre 1920×1080 fixe
- **Documentation du setup** : un fichier `media/demo-video/recordings/SETUP.md` qui documente l'état exact de l'instance, les commandes pour la régénérer, le projet/taxon vedette choisi.

**Acceptance** :
- Lancer `niamoto serve` dans le projet vedette → site visuel sans glitch
- Le GUI Tauri démarre proprement
- Test screen capture courte : aucune notif/distraction

### Phase 2 — Capture screen recordings (~4h)

**Outils** :
- **OBS Studio** (gratuit, Mac/Linux/Windows) ou **ScreenFlow** ($129, Mac, plus polished) — recommandé OBS pour un premier teaser
- Codec : ProRes 422 LT (qualité haute, taille raisonnable) ou H.264 high bitrate
- Résolution capture : **3840×2160 (4K)** si possible — downscale en post pour netteté ; sinon 1920×1080 natif
- Framerate : **60 fps** (permet ralentis fluides en post)
- Pas de webcam, pas d'audio mic

**Workflow par beat** :
1. **Répétition** : faire le geste 2-3 fois en réel pour fluidifier
2. **Take 1** : enregistrer le beat avec ~2 s de marge avant et après
3. **Take 2** : refaire si hésitation, mauvaise position curseur, animation interrompue
4. **Sélection** : marquer le meilleur take dans le nom de fichier

**Naming convention** :
```
media/demo-video/recordings/
  acte2/
    2.1-import-take1.mov
    2.1-import-take2-BEST.mov
    2.2-config-take1-BEST.mov
    2.3-preview-take1-BEST.mov
  acte3/
    3.1-site-load-take1-BEST.mov
    3.2-map-zoom-take1-BEST.mov
    3.3-page-static-take1-BEST.mov
```

**Trims initiaux** : ouvrir chaque MOV dans QuickTime, trimer les bouts vides, exporter en `*-trimmed.mov`. Pas de montage à ce stade — juste des clips propres.

**Deliverables** :
- 6 fichiers MOV trimés (3 pour Acte 2, 3 pour Acte 3)
- `recordings/SETUP.md` à jour avec les choix faits

**Acceptance** :
- Chaque clip < 12 s, joue sans glitch dans QuickTime
- Aucune notif visible, aucun mouvement parasite
- Curseur visible et aux bons endroits

### Phase 3 — Composition Remotion (compositor mode) (~6h)

Le `LandingTeaser` est restructuré en **4 actes** (au lieu de 5 scènes). Les composants `CollectionMosaic`, `PublicSiteFrame`, `EditorialOverlay`, `AppWindow` côté teaser deviennent **inutiles** et peuvent être supprimés.

**Nouvelle structure de fichiers** :

```
media/demo-video/src/teaser/
  config.ts                           # durées des 4 actes, fps
  copy.ts                             # textes courts à valider Phase 2
  scenes/
    Act1Pain.tsx                      # motion design pure (Remotion)
    Act2Solution.tsx                  # OffthreadVideo + overlay cartouches
    Act3Payoff.tsx                    # OffthreadVideo + zoom/pan post-prod
    Act4CTA.tsx                       # motion design pure (Remotion) + CTA
  components/
    Cartouche.tsx                     # bottom-card text overlay réutilisable
    LogoSignature.tsx                 # logo animation pour Act4
```

**Suppressions** :
- `media/demo-video/src/teaser/components/CollectionMosaic.tsx` (711 lignes)
- `media/demo-video/src/teaser/components/PublicSiteFrame.tsx` (287 lignes)
- `media/demo-video/src/teaser/components/EditorialOverlay.tsx` (89 lignes)
- `media/demo-video/src/teaser/scenes/TeaserOpener.tsx`
- `media/demo-video/src/teaser/scenes/TeaserDataIntake.tsx`
- `media/demo-video/src/teaser/scenes/TeaserStructure.tsx`
- `media/demo-video/src/teaser/scenes/TeaserPublish.tsx`
- `media/demo-video/src/teaser/scenes/TeaserEndCard.tsx`

**Patterns clés Remotion compositor** :

```tsx
// Act2Solution.tsx — utilisation de OffthreadVideo
import { OffthreadVideo, staticFile, useCurrentFrame, interpolate } from "remotion";

export const Act2Solution: React.FC = () => {
  const frame = useCurrentFrame();
  const cartoucheOpacity = interpolate(frame, [60, 90, 240, 270], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <OffthreadVideo src={staticFile("recordings/acte2/2.1-import-take2-BEST.mov")} />
      <Cartouche text="Import en un drop." opacity={cartoucheOpacity} position="bottom" />
    </AbsoluteFill>
  );
};
```

**Pattern zoom/pan post-prod** (Act 3.2) : appliquer `transform: scale(...) translate(...)` interpolé sur le `<OffthreadVideo>` pour créer un Ken Burns doux. Permet d'attirer l'œil sur la carte sans avoir à zoomer dans le browser pendant la capture.

**Composition root** :

```tsx
// LandingTeaser.tsx
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";

export const LandingTeaser: React.FC = () => (
  <AbsoluteFill style={{ background: "#000" }}>
    <TransitionSeries>
      <TransitionSeries.Sequence durationInFrames={teaserSec(8)} premountFor={30}><Act1Pain /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: 15 })} />
      <TransitionSeries.Sequence durationInFrames={teaserSec(27)} premountFor={30}><Act2Solution /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: 15 })} />
      <TransitionSeries.Sequence durationInFrames={teaserSec(15)} premountFor={30}><Act3Payoff /></TransitionSeries.Sequence>
      <TransitionSeries.Transition presentation={fade()} timing={linearTiming({ durationInFrames: 15 })} />
      <TransitionSeries.Sequence durationInFrames={teaserSec(10)} premountFor={30}><Act4CTA /></TransitionSeries.Sequence>
    </TransitionSeries>
  </AbsoluteFill>
);
```

**Bonnes pratiques Remotion (résolues vs revue précédente)** :
- ✅ `premountFor={30}` partout (fix régression critique)
- ✅ Tous les `interpolate` ont `extrapolateLeft/Right: "clamp"`
- ✅ Pas de `backdropFilter` (n'est pas rendu en headless)
- ✅ `OffthreadVideo` (pas `Video`) pour render headless propre
- ✅ Fonts via `delayRender` + `ensureFontsLoaded` préservé

**Acceptance** :
- `pnpm exec tsc --noEmit` passe
- `pnpm exec remotion render LandingTeaser out/landing-teaser.mp4` produit un MP4 lisible
- Durée totale 60 s ±2 s
- Visuel cohérent en preview Remotion Studio

### Phase 4 — Audio (~3h)

**Sources (gratuites, licence commerciale OK)** :
- **Musique** : [YouTube Audio Library](https://studio.youtube.com/channel/UC/music) — tracks libres usage commercial, pas d'attribution requise sur la plupart
- **SFX** : [Freesound.org](https://freesound.org/) — Creative Commons, filtrer sur licence **CC0** (domaine public) ou **CC-BY** (attribution) pour rester simple juridiquement
- **Alternative SFX** : [Mixkit](https://mixkit.co/free-sound-effects/) — free commercial, pas d'attribution

**Choix musique (YouTube Audio Library)** :
- Filtres à appliquer : Genre = `Ambient` ou `Cinematic`, Mood = `Calm` ou `Inspirational`, Attribution = `Not required`, Durée ≥ 60 s
- Critères : instrumentale uniquement (pas de voix), tempo medium 90-110 BPM, pas de drop électronique, pas de violons sentimentaux
- Test : écouter en boucle → si après 3 écoutes c'est encore agréable, c'est bon
- Format : MP3 320 kbps (YT AL export natif) — suffisant pour un premier teaser

**Choix SFX (Freesound.org ou Mixkit)** :
- 1 × `soft pop UI` (CC0) pour les apparitions de mots Acte 1 — cherche « soft pop », « bubble pop », « interface click »
- 1 × `low swoosh transition` (CC0) pour les transitions entre actes — cherche « swoosh low », « woosh transition »
- 1 × `UI click minimal` (CC0) pour les cartouches Acte 2 (optionnel — les clicks du screen recording peuvent suffire)
- 1 × `soft ping` (CC0) pour l'apparition du logo Acte 4 — cherche « notification ping », « soft bell »
- 1 × `cinematic swell` (CC0) pour la montée Acte 3.2 — cherche « ambient swell », « cinematic riser soft »

**Temps estimé recherche audio** : 1-2 h pour dénicher le bon track + SFX (plus long qu'Artlist car catalogue moins curé). Prévoir cette friction en Phase 4.

**Mixage dans DaVinci Resolve** (gratuit) :
1. Importer le MP4 généré par Remotion comme video track principale
2. Importer la musique → audio track 1, niveau **-30 LUFS** (faible, fond)
3. Importer les SFX → audio track 2, sync sur les beats, niveau **-18 LUFS** (présents, pas écrasants)
4. Page « Fairlight » de Resolve → maître à **-14 LUFS integrated** (standard web 2026)
5. Export : H.264 1920×1080, audio AAC 192 kbps stéréo

**Deliverables** :
- `media/demo-video/audio/music-track.wav` (committé ou via git-lfs si > 5 MB)
- `media/demo-video/audio/sfx/*.wav` (×5)
- `media/demo-video/recordings/AUDIO.md` documentant les choix

**Acceptance** :
- Écoute casque : musique audible mais discrète, SFX nets, pas de saturation
- Loudness meter Resolve : intégré final entre -13.5 et -14.5 LUFS
- Test sur enceintes laptop : la vidéo « se sent » avec énergie

### Phase 5 — Export & distribution (~1h)

Deux exports cibles :

| Cible | Résolution | Codec | Bitrate | Taille cible | Usage |
|-------|------------|-------|---------|--------------|-------|
| **Master** | 1920×1080 | H.264 | CRF 18 | ~30-50 MB | Archive, YouTube, partage interne |
| **Landing web** | 1280×720 | H.264 | CRF 22 | < 5 MB | Hero landing, autoplay muted |

**Compression FFmpeg landing** :
```bash
ffmpeg -i out/landing-teaser-master.mp4 \
  -vf scale=1280:720 \
  -c:v libx264 -crf 22 -preset slow \
  -c:a aac -b:a 96k \
  -movflags +faststart \
  out/landing-teaser-web.mp4
```

`-movflags +faststart` est critique : déplace les métadonnées en début de fichier pour streaming progressif.

**Test autoplay muted** :
- Page HTML test locale avec `<video src="..." autoplay muted loop>`
- Vérifier que les 3 premières secondes (Acte 1) restent compréhensibles **sans son**
- Vérifier que la boucle (loop seamless ou hard cut ?) — pour landing hero, on peut couper avec un fade out propre à 60s

**Deliverables** :
- `out/landing-teaser-master.mp4` (1080p, ~30-50 MB)
- `out/landing-teaser-web.mp4` (720p, < 5 MB)
- `media/demo-video/README.md` — section « Export & distribution » mise à jour

## Tools & costs

| Item | Coût | Récurrent |
|------|------|-----------|
| Remotion 4.x | 0 € | OSS |
| OBS Studio | 0 € | OSS |
| DaVinci Resolve (gratuit) | 0 € | One-shot |
| YouTube Audio Library (musique) | 0 € | Free commercial |
| Freesound.org / Mixkit (SFX) | 0 € | Free commercial CC0/CC-BY |
| FFmpeg | 0 € | OSS |
| **Total** | **0 €** | |

Décision utilisateur : stack 100% gratuite pour ce premier teaser. Si des vidéos ultérieures demandent une qualité ou vélocité supérieures, Artlist (199 €/an) ou achat single track AudioJungle (~30-50 €) restent des pistes d'évolution.

## Acceptance Criteria

### Functional Requirements

- [ ] 4 actes dans l'ordre Pain → Solution → Payoff → CTA
- [ ] Durée totale 60 s ±2 s
- [ ] Au moins 80 % de la durée des Actes 2 et 3 = screen recording du vrai produit Niamoto
- [ ] Aucun mock JSX du produit (suppression des composants `CollectionMosaic`, `PublicSiteFrame`, etc.)
- [ ] Audio présent : musique de fond + minimum 4 SFX placés sur les beats clés
- [ ] CTA visible Acte 4 avec URL `niamoto.org` (sous réserve validation R15 inversion)
- [ ] Captions/copy on-screen en anglais (R13)

### Non-Functional Requirements

- [ ] `MarketingLandscape` rend toujours à l'identique (zéro régression composition existante)
- [ ] Pas de nouvelle dépendance npm dans `media/demo-video/package.json`
- [ ] `pnpm exec tsc --noEmit` passe
- [ ] Master MP4 ≤ 80 MB ; web MP4 ≤ 5 MB
- [ ] Loudness intégré final entre -13.5 et -14.5 LUFS
- [ ] `pnpm exec remotion render` complète en < 5 min sur Mac M-series

### Quality Gates

- [ ] Vérification autoplay muted : les Actes 1 et 4 restent lisibles sans son
- [ ] Test sur 3 navigateurs (Safari, Chrome, Firefox)
- [ ] Aucune notification visible dans les screen recordings
- [ ] Aucun chart faux ou type non-Niamoto dans la vidéo. **Types validés 14/04 par exploration `test-instance/nouvelle-caledonie`** : bar horizontal multicolore (sous-taxons), bar vertical beige (DBH), bar empilé 12 mois (phénologie), bar horizontal bleu (pluviométrie), **donut** (distribution substrat UM/non-UM), cards stats. Les donuts existent bien dans le vrai produit, contrairement à ce que j'avais écrit initialement.
- [ ] Visionnage côte-à-côte avec un teaser de référence (Loom AI Workflows par exemple) → ressenti pro comparable

## Risk Analysis & Mitigation

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Screen recordings de mauvaise qualité (curseur saute, glitch) | Moyenne | Haut | Multi-takes systématiques, validation visuelle de chaque clip avant Phase 3 |
| Instance test pas assez photogénique | Moyenne | Haut | Phase 1 dédiée à ça ; sélectionner taxon riche, dataset dense |
| Choix musique difficile à arrêter (paralysie de choix Artlist) | Élevée | Moyen | Time-box à 1h max d'écoute, shortlist 3 tracks puis test sur la vidéo |
| `OffthreadVideo` glitche en render headless | Faible | Haut | Pattern documenté Remotion, fallback `<Video>` natif |
| CTA Acte 4 contredit R15 du brief original | Certaine | Faible | Décision explicite à valider avec utilisateur — si refus, retomber sur logo + wordmark only |
| Boucle autoplay laide (cut hard) | Moyenne | Moyen | Crossfade au montage Resolve entre fin et début, ou « hold » 2 s sur logo statique |
| Première fois screen recording — courbe d'apprentissage | Élevée | Moyen | Tutoriel OBS 30 min en amont (cf. References), test à blanc |
| Audio mix amateur (musique trop forte) | Moyenne | Haut | Loudness meter Resolve, comparaison casque vs enceintes laptop |
| Confidentialité du nom de projet visible dans le screen recording | Moyenne | Faible | Renommer le projet en générique (« Niamoto Test ») avant capture |

## Decisions (locked 2026-04-14)

Les 7 questions cadres ont été tranchées par l'utilisateur après le brainstorm :

| # | Décision | Implication |
|---|----------|-------------|
| 1 | **CTA Acte 4 activé** (renverse R15) | Bouton « niamoto.org » vert + accroche « Open source. Auto-hébergeable. » |
| 2 | **Hook hybride** (nouveau user-centric Acte 1 + `Import. Structure. Publish.` tagline Acte 4) | Acte 1 : « Vos données terrain. Dispersées, illisibles. » ; Acte 4 : tagline marque sous le logo |
| 3 | **Taxon vedette : Araucariaceae** | Famille endémique NC, hiérarchie taxonomique riche, sidebar dense, distribution large → belle carte |
| 4 | **Curseur agrandi via Accessibility macOS** (taille 2-3) pendant la capture | Documenté dans `recordings/SETUP.md` ; zéro post-prod curseur |
| 5 | **One-shot avec hold final sur Acte 4** | 3 s de hold statique fin ; loop autoplay = hard cut assumé ; pas de crossfade fin→début |
| 6 | **1920×1080 uniquement pour la v1** | Formats 1:1 / 9:16 différés ; simplicité > multi-format au premier teaser |
| 7 | **Audio hors-repo, source documentée** | Fichiers audio locaux ; `media/demo-video/recordings/AUDIO.md` liste titre + URL source + licence (CC0 / CC-BY / YT AL) + hash MD5 ; pas de git-lfs |
| 8 | **Source audio 100% gratuite** (YouTube Audio Library + Freesound / Mixkit) | 0 € ; tracking licence CC dans AUDIO.md pour chaque asset ; Artlist reste une option future si qualité insuffisante |

Ces décisions sont locked. Toute nouvelle ambigüité en cours d'implémentation : créer une nouvelle entrée ici avant de coder.

## Documentation Plan

- [ ] `media/demo-video/recordings/SETUP.md` — état de l'instance test, projet/taxon vedette, commandes de régénération
- [ ] `media/demo-video/recordings/AUDIO.md` — choix musique (titre Artlist, URL), choix SFX, niveaux finaux
- [ ] `media/demo-video/README.md` — section « Hybride workflow » expliquant le pipeline screen recording → Remotion → Resolve → FFmpeg
- [ ] `docs/DESIGN_SYSTEM.md` — note disant que la palette teaser n'est plus pertinente (le screen recording remplace)
- [ ] CHANGELOG note dans `media/demo-video/` (si CHANGELOG existe — sinon skip)

## References & Research

### Internal

- Brainstorm origine : `docs/brainstorms/2026-04-14-landing-teaser-refonte-brainstorm.md`
- Plan superseded : `docs/plans/2026-04-14-feat-landing-teaser-refonte-plan.md`
- Brief original R1-R15 : `docs/plans/2026-04-14-feat-landing-teaser-video-plan.md`
- Theme actuel (à conserver intact) : `media/demo-video/src/shared/theme.ts`
- Composition préservée : `media/demo-video/src/compositions/MarketingLandscape.tsx`

### Best practices teaser produit B2B 2026 (recherche indépendante)

- Notion Agents : https://www.youtube.com/watch?v=R1cF4T4lgI4
- Figma AI Editing : https://www.youtube.com/watch?v=y8mzJDJzvX4
- Loom AI Workflows : https://www.youtube.com/watch?v=NQWReDct7c0
- Arcade — Product Launch Video Examples : https://www.arcade.software/post/product-launch-video-examples
- Superside — 16+ B2B SaaS Video Examples : https://www.superside.com/blog/saas-video-examples
- Inside Marketing Design at Stripe : https://insidemarketingdesign.com/at/stripe
- Spacebar Visuals — Why Most SaaS Demos Don't Work : https://www.spacebarvisuals.com/post/why-most-saas-product-demos-dont-work-and-how-to-fix-them
- Ignite Video — Autoplay Best Practices : https://www.ignite.video/en/articles/basics/autoplay-videos
- Artlist SFX guide : https://artlist.io/blog/sound-effects-for-videos-essential-tips-for-dynamic-sound-design/
- Natclark — Optimize Video for Web 2025 : https://natclark.com/how-to-optimize-video-for-web-complete-2025-guide/

### Tooling

- Remotion 4.x docs : https://www.remotion.dev/docs
- OffthreadVideo : https://www.remotion.dev/docs/offthreadvideo
- Skill local Remotion : `/Users/julienbarbe/.claude/skills/remotion-best-practices/`
- OBS Studio : https://obsproject.com/
- DaVinci Resolve (gratuit) : https://www.blackmagicdesign.com/products/davinciresolve
- YouTube Audio Library (musique free) : https://studio.youtube.com/ → onglet Audio Library
- Freesound.org (SFX CC) : https://freesound.org/ — filter by License `Creative Commons 0` ou `Attribution`
- Mixkit (SFX free commercial) : https://mixkit.co/free-sound-effects/
- Artlist (backup payant) : https://artlist.io/
- AudioJungle (single track) : https://audiojungle.net/
- FFmpeg : https://ffmpeg.org/

### Tutoriels d'embarquement (dev qui débute en vidéo)

- OBS Studio premier setup : https://obsproject.com/wiki/OBS-Studio-Quickstart
- DaVinci Resolve crash course (free, YouTube) : https://www.youtube.com/results?search_query=davinci+resolve+18+beginners+tutorial
- LUFS expliqué simplement : https://www.izotope.com/en/learn/what-is-lufs.html
