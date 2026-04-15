# Teaser hybride — sources audio

Catalogue des assets musique + SFX utilisés. Un asset = une ligne avec URL source + licence + hash MD5 (pour reproductibilité).

À remplir pendant Phase 4 (audio). Les fichiers eux-mêmes ne sont pas commit (cf. décision #7 du plan hybride).

Stack choisie : **100% gratuit** (décision #8 du plan).

## Musique de fond

| Asset | Source | Licence | URL | Hash MD5 | Usage |
|-------|--------|---------|-----|----------|-------|
| _à remplir_ | YouTube Audio Library | Creative Commons ou Audio Library / attribution not required | _url_ | _md5_ | Fond continu 60 s sur toute la vidéo |

### Critères de sélection (rappel plan)
- Instrumentale uniquement (pas de voix)
- Tempo medium 90–110 BPM
- Mood : calm, inspirational, documentary
- Pas de drop électronique, pas de violons sentimentaux
- Niveau final **-30 LUFS** (fond, sous les SFX)

### Comment retrouver
YouTube Studio → onglet Audio Library → filtres :
- Genre : Ambient ou Cinematic
- Mood : Calm ou Inspirational
- Attribution : Not required
- Durée ≥ 60 s

## SFX (effets sonores)

| Asset | Source | Licence | URL | Hash MD5 | Placement (beat) | Niveau |
|-------|--------|---------|-----|----------|------------------|--------|
| soft pop UI | Freesound.org ou Mixkit | CC0 ou CC-BY ou Mixkit free commercial | _url_ | _md5_ | Acte 1 mots apparaissent | -18 LUFS |
| low swoosh | Freesound.org | CC0 | _url_ | _md5_ | Transitions entre actes | -20 LUFS |
| UI click (optionnel) | Freesound.org ou capture native du screen recording | CC0 | _url_ | _md5_ | Cartouches Acte 2 | -22 LUFS |
| soft ping / notification bell | Freesound.org | CC0 | _url_ | _md5_ | Apparition logo Acte 4 | -18 LUFS |
| cinematic swell soft | Freesound.org | CC0 | _url_ | _md5_ | Montée vers peak Acte 3.2 | -18 LUFS crescendo |

### Tips recherche

Freesound.org : filtrer par licence **Creative Commons 0** (domaine public, zéro attribution) ou **Attribution** (CC-BY, crédit suffit).

Mixkit : tout est `Mixkit Free License` — usage commercial OK, aucune attribution requise. Plus simple juridiquement.

### Niveaux audio cibles (fix Phase 4)
- Musique de fond : **-30 LUFS** intégré
- SFX sur beats : **-18 à -22 LUFS** punch
- Master final export (web / social) : **-14 LUFS** intégré (standard 2026)

## Tracking licences pour attribution / compliance

Si un asset requiert attribution (CC-BY ou autre) :
- Ajouter ligne dans `README.md` de `media/demo-video/` avec crédit + URL
- Optionnel : inclure dans l'endcard ou dans les métadonnées vidéo (pas visible à l'écran)

Si tout CC0 ou Mixkit Free : rien à afficher.

## Fichiers locaux

Les WAV / MP3 téléchargés restent dans `media/demo-video/recordings/audio-src/` (gitignored) :

```
media/demo-video/recordings/audio-src/   # .gitignore this
  music-bg.wav
  sfx-soft-pop.wav
  sfx-swoosh-low.wav
  sfx-ui-click.wav
  sfx-soft-ping.wav
  sfx-cinematic-swell.wav
```

Ajouter `recordings/audio-src/` au `.gitignore` du repo avant de télécharger quoi que ce soit.
