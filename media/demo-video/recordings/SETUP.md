# Teaser hybride — SETUP screen recordings

État de l'instance de référence, money shots identifiés, bug connu, checklist macOS avant capture.

Document vivant : mis à jour pendant Phase 1 au fur et à mesure des décisions.

## Instance de référence

- **Chemin** : `test-instance/nouvelle-caledonie/`
- **Nom projet** (config.yml) : `niamoto-subset` — déjà générique, pas de renommage nécessaire
- **Niamoto version** : 0.8.0
- **Exports** : regénérés le 14/04/2026 — à jour
- **Titre du site** : « Niamoto » — générique ✅
- **Sous-titre** : « Portail de la forêt de Nouvelle-Calédonie »
- **i18n** : `fr/` + `en/` disponibles — on capture en **FR** (brief R13 dit anglais prioritaire, à réévaluer Phase 2 car le pitch kanak en FR est signifiant)

## URLs des pages clés (via preview local)

Serveur de preview : **http://localhost:5173/api/site/preview-exported/**

| Page | URL | Rôle dans le teaser |
|------|-----|---------------------|
| Hero accueil | `/fr/index.html` | **Acte 3 payoff principal** — hero forêt + chiffres clés + pitch kanak |
| Liste taxons | `/fr/taxons/index.html` | **Acte 3 beat intermédiaire** — grille cards avec photos taxons |
| Page Araucariaceae | `/fr/taxons/948049381.html` | **Acte 3 beat detail** — page taxon riche avec charts |
| Présentation peuplements | `/fr/plots.html` | Asset secondaire — contient carte NC-PIPPN qui MARCHE |
| Présentation arbres | `/fr/trees.html` | Asset secondaire |
| Présentation forêt | `/fr/forests.html` | Asset secondaire |
| Méthodologie | `/fr/methodology.html` | Asset secondaire (non encore exploré) |

## Taxon vedette : Araucariaceae (948049381.html)

Confirmé après exploration. Données :
- **Rang** : Famille
- **Occurrences** : 3 539
- **Sous-taxons** : 10+ (Araucaria montana 643, Agathis ovata 498, Agathis lanceolata 466, Araucaria ruleï, Agathis moorei, etc. — palette multicolore)
- **Charts disponibles sur la page** :
  - Distribution géographique (carte NC Plotly + 3 539 bubbles gradient — **money shot #1 du teaser**)
  - Informations générales (cards)
  - Sous-taxons principaux (bar chart horizontal multicolore)
  - Distribution DBH (bar chart beige/brun, 8 bins 10–300 cm)
  - Phénologie (12 mois, bars empilées orange/vert/bleu)
  - Milieu de vie Holdridge (Sec/Humide/Très humide)
  - Distribution substrat (**donut** 82.8% Ultramafique / 17.1% non-UM)
  - Répartition pluviométrie (bar chart horizontal bleu)
  - Distribution altitudinale + Stratification en bas

## Money shots identifiés (screenshots capturés pendant Phase 1)

1. **Hero forêt plein écran** (`/fr/index.html` top) — photo forêt tropicale + « NIAMOTO » typo blanche centrée + nav verte. **Ouverture ou payoff**.
2. **Partenaires + chiffres clés** (`/fr/index.html` scroll 1) — logos IAC/IRD/Cirad/OFB + 4 stats (1 208 taxons / 5 400 km² / 509 parcelles / 70 000+ arbres). Animation motion potentielle.
3. **Pitch kanak** (`/fr/index.html` scroll 2) — « En paicî, mötö est l'arbre… ». Storytelling culturel unique.
4. **Grille taxons avec photos** (`/fr/taxons/index.html` top) — 1223 éléments, cards photos, filtres. **Beat Acte 2 ou 3**.
5. **Page Araucariaceae — sidebar + charts** (`/fr/taxons/948049381.html`) — sidebar taxonomique vivante + bar charts scientifiques denses. **Acte 3 détail**.
6. **Photo terrain mètre ruban DBH** (`/fr/plots.html` scroll) — photo immersive collecte terrain. **Acte 1 douleur potentielle**.
7. **Carte Distribution géographique Araucariaceae** (`/fr/taxons/948049381.html` top) — contour NC complet + 3539 points gradient bleu→violet→orange→jaune, hot spots jaune (Poindimié) et orange (Nouméa). **LE money shot #1 de l'Acte 3** pour montrer la densité + distribution endémique.
8. **Carte NC-PIPPN** (`/fr/plots.html` mid) — inventaires du réseau, carte différente (points par parcelle), asset alternatif.

## Problèmes détectés

### ✅ Carte Distribution géographique — PAS de bug (rectification)

J'avais d'abord cru que la carte était cassée sur Araucariaceae : en réalité **elle fonctionne parfaitement**. L'erreur venait d'une lecture à trop basse résolution des screenshots — la carte Plotly utilise des teintes pâles (beige pour la terre, bleu clair pour l'océan) qu'on ne distingue pas à 1382×889 sans zoom.

**Vérifié en zoomant** : carte Araucariaceae = splendide money shot. 3 539 points d'occurrence avec gradient count bleu → violet → orange → jaune, hot spots visibles (jaune près de Poindimié — probablement *Araucaria montana* — et orange près de Nouméa — probablement *Araucaria columnaris* endémique), toutes les villes annotées (Pouébo, Koumac, Koné, Houaïlou, Canala, Thio, Païta, Nouméa, Heo, Hunete), îles Loyauté et Île des Pins incluses.

**La carte EST le money shot le plus spectaculaire de la page taxon.** À capturer en priorité en Acte 3.

### 🟡 Erreur dans plan hybride v1

J'ai écrit dans le plan initial « aucun chart de type donut ou gauge dans le vrai produit ». **Faux** — Distribution substrat est un vrai donut chart (82.8% Ultramafique / 17.1% non-UM). Plan corrigé le 14/04.

## Checklist macOS avant capture (à faire côté Julien)

Julien fait ces étapes localement avant chaque session de capture :

### Système (System Settings)
- [ ] **Do Not Disturb ON** (via Focus Modes) — bloque toutes les notifs
- [ ] **Dock autohide** (System Settings → Desktop & Dock → Automatically hide)
- [ ] **Menu Bar autohide** (System Settings → Desktop & Dock → Automatically hide and show menu bar → In full screen only, ou Always)
- [ ] **Accessibility → Pointer → Pointer size** : taille 2 ou 3 (curseur agrandi pour visibilité 1280×720 web)
- [ ] **Displays** : résolution 1920×1080 (ou plus haute avec downscale au montage)
- [ ] **Desktop clean** : zéro icône visible (si icônes, System Settings → Desktop & Dock → Show on Desktop → tout décocher)
- [ ] **Wallpaper neutre** (si desktop peut apparaître) — gris ou noir uni

### Chrome (ou navigateur de preview)
- [ ] Profil **incognito** ou nouveau profil propre, zéro extension
- [ ] Fenêtre **1920×1080 exact** (utiliser `Rectangle` ou `Raycast` pour snap exact)
- [ ] **Zoom à 100%** (Cmd+0)
- [ ] **Masquer la bookmarks bar** (Cmd+Shift+B)
- [ ] **Fermer onglets inutiles** — un seul onglet Niamoto
- [ ] **DevTools fermée**

### Niamoto GUI Tauri (pour les captures d'interface IDE)
- [ ] Lancer via `./scripts/dev/dev_desktop.sh test-instance/nouvelle-caledonie`
- [ ] Fenêtre en taille fixe (1920×1080 ou plus)
- [ ] Projet ouvert : `niamoto-subset` (nouvelle-caledonie)
- [ ] État initial propre : aucune donnée en cours d'import, aucune erreur dans la sidebar

### Instance à vérifier avant chaque session
- [ ] `niamoto-subset` charge sans erreur
- [ ] Le site preview s'affiche correctement (sauf carte taxon — bug connu)
- [ ] Le GUI Tauri démarre proprement, projet sélectionné
- [ ] L'URL `http://localhost:5173/api/site/preview-exported/fr/index.html` répond

## Screen recordings à capturer (storyboard v1)

Correspondance avec le plan hybride v1 :

### Acte 2 — Solution en action (8–35 s)
- **2.1 Import** (8–17 s) : GUI Tauri, drag fichiers CSV dans la zone d'import, progression bar
- **2.2 Configuration** (17–26 s) : navigation Collections, sélection widget « Carte distribution », widget ajouté, un autre, un autre, mosaïque qui se construit
- **2.3 Preview** (26–35 s) : bascule sur panneau preview, page taxon se rend live avec charts

### Acte 3 — Payoff (35–50 s)
- **3.1 Site load** (35–42 s) : browser charge `/fr/index.html` — hero forêt « NIAMOTO » plein écran
- **3.2 Scroll éditorial** (42–46 s) : scroll vers partenaires + 4 chiffres clés + pitch kanak
- **3.3 Liste taxons** (46–48 s) : navigation vers `/fr/taxons/index.html` — grille cards photos
- **3.4 Page taxon** (48–50 s) : clic sur Araucariaceae → page détail, scroll doux vers les charts

**La carte est le money shot #1 de l'Acte 3.4** — toute scène qui la montre pleine page avec un zoom doux post-prod est gagnante.

### Acte 1 & 4 — Motion design Remotion (pas de screen recording)
- Acte 1 : composition Remotion pure (texte animé sur fond sombre ou photo terrain mètre ruban en background blurred)
- Acte 4 : composition Remotion pure (logo + tagline + CTA vert)

## Naming convention captures

```
media/demo-video/recordings/
  references/                    # screenshots pris pendant Phase 1 (référence storyboard)
    home-hero.png
    home-partners-stats.png
    taxons-grid.png
    araucariaceae-top.png
    araucariaceae-charts.png
    plots-map-working.png
    trees-hero.png
    forests-hero.png
  acte2/                         # screen recordings Acte 2 (Phase 2)
    2.1-import-take1.mov
    2.1-import-take2-BEST.mov
    2.2-config-take1-BEST.mov
    2.3-preview-take1-BEST.mov
  acte3/                         # screen recordings Acte 3 (Phase 2)
    3.1-site-load-take1-BEST.mov
    3.2-editorial-scroll-take1-BEST.mov
    3.3-taxons-grid-take1-BEST.mov
    3.4-taxon-page-take1-BEST.mov
  AUDIO.md                       # sources musique + SFX (remplie Phase 4)
  SETUP.md                       # ce fichier
```

## Prochaine étape

1. Prep macOS côté Julien (checklist ci-dessus — DnD, curseur accessibility, dock autohide, clean desktop, fenêtre Chrome 1920×1080)
2. Commencer les captures OBS systématiques : Acte 2 (GUI Tauri, interactions import/config/preview) d'abord, Acte 3 (site publié : hero → scroll → liste taxons → page Araucariaceae zoom carte) ensuite
3. Plan hybride v1 déjà corrigé pour « donut existe bien » et « pas de bug carte »
