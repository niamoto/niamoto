---
title: "Offline Support Complet pour l'Application Desktop"
type: feat
date: 2026-02-05
---

# Support Offline Complet pour Niamoto Desktop

## Overview

L'application desktop Niamoto (Tauri 2 + FastAPI embarque) est **deja fonctionnelle offline a 95%** grace a son architecture locale-first : Tauri lance FastAPI comme sous-processus sur `127.0.0.1`, toutes les operations core (Import, Transform, Export) tournent sur DuckDB local, et le frontend communique via des chemins relatifs `/api`.

Ce plan adresse les **5% restants** : des dependances CDN dans les previews GUI, l'absence de detection reseau, et le manque de degradation gracieuse pour les fonctionnalites necessitant internet (Enrichissement API, Deploy).

**Fonctionnalites explicitement exclues du scope offline** (confirmees par l'utilisateur) :
- Deploy vers providers externes (Cloudflare, GitHub Pages, SSH)
- Enrichissement API (appels GBIF, Endemia, WFO)

---

## Etat des Lieux Detaille

### Ce qui fonctionne deja offline

| Fonctionnalite | Mecanisme | Statut |
|----------------|-----------|--------|
| Lancement Tauri + FastAPI | Subprocess local sur port dynamique | OK |
| Import fichiers (CSV, GeoJSON, shapefiles) | Lecture locale vers DuckDB | OK |
| Transform (tous plugins) | Computation locale sur DuckDB | OK |
| Export HTML (generation site statique) | Jinja2 + assets locaux | OK |
| Preview site statique | Monte sur `/preview` via StaticFiles | OK |
| Edition config YAML | Lecture/ecriture fichiers locaux | OK |
| Data Explorer | Requetes DuckDB locales | OK |
| Systeme plugins | Chargement filesystem (system -> user -> project) | OK |
| Plotly dans pages exportees | Bundle local `/assets/js/vendor/plotly/3.0.1_plotly.min.js` | OK |
| Stores Zustand | Persistance localStorage | OK |

### Ce qui echoue offline (a corriger)

| Probleme | Fichier(s) | Impact |
|----------|------------|--------|
| **Preview widgets GUI** : Plotly charge depuis `cdn.jsdelivr.net` | `preview_service.py:71`, `layout.py:452` | Previews completement vides |
| **Preview entites** : topojson depuis CDN | `entities.py:452` | Cartes entites cassees |
| **Preview cartes Leaflet** : JS/CSS depuis `unpkg.com` + tuiles OSM | `map_renderer.py:249-262` | Cartes Leaflet non fonctionnelles |
| **Polices themes** : Google Fonts | `themes/presets/*.ts` (5 fichiers) | Fallback polices systeme (mineur) |
| **Placeholders mock** : `placehold.co` | `site.py:1063-1068` | Images cassees dans mocks |
| **Aucune detection reseau** | Frontend entier | Pas d'indication offline |
| **Enrichissement sans gestion offline** | `enrichment.py` | Itere tout, echoue en silence |
| **Deploy sans pre-check** | `deploy.py` | Erreur cryptique |

### Probleme de version Plotly

Le bundle local est en **Plotly 3.0.1** (`plotly_utils.py:12`) alors que les previews GUI referent **Plotly 2.35.0** (CDN). Ce sont deux versions majeures differentes. La migration des previews vers le bundle local implique d'aligner sur 3.0.1.

---

## Solution Proposee

### Principes

1. **Zero CDN pour le GUI desktop** : toutes les dependances JS/CSS du GUI servies localement
2. **Degradation gracieuse** : les fonctionnalites necessitant internet sont desactivees avec un message clair, jamais silencieusement cassees
3. **Detection reseau legere** : un hook frontend + un endpoint backend optionnel
4. **Pages statiques exportees** : fonctionnelles offline pour les graphiques Plotly ; les cartes avec tuiles affichent un fallback `white-bg` sans tuiles
5. **Polices** : les polices du GUI desktop sont bundlees localement ; les pages exportees gardent les liens CDN (elles seront deployees en ligne)

---

## Phases d'Implementation

### Phase 1 — Elimination des CDN dans le GUI (P0, effort faible)

**Objectif** : Le GUI desktop fonctionne 100% sans internet.

#### 1.1 Servir Plotly localement pour les previews

**Fichiers a modifier :**
- `src/niamoto/gui/api/services/preview_service.py:71`
- `src/niamoto/gui/api/routers/layout.py:452`

**Action** : Remplacer `https://cdn.jsdelivr.net/npm/plotly.js@2.35.0/dist/plotly.min.js` par le chemin local `/preview-assets/js/plotly.min.js` (ou equivalent).

**Prerequis** : Monter un endpoint FastAPI qui sert le fichier `publish/assets/js/vendor/plotly/3.0.1_plotly.min.js`. Cet endpoint existe peut-etre deja via le montage StaticFiles — a verifier.

**Note version** : Les previews passeront de Plotly 2.35.0 a 3.0.1. Verifier que les widgets existants rendus sont visuellement coherents. Plotly 3.x est retrocompatible pour la majorite des graphiques (bar, scatter, pie, gauge).

#### 1.2 Bundler topojson.js localement

**Fichier a modifier :**
- `src/niamoto/gui/api/routers/entities.py:452`

**Action** :
1. Telecharger `topojson@3.0.0/dist/topojson.min.js`
2. Placer dans `src/niamoto/publish/assets/js/vendor/topojson/3.0.0_topojson.min.js`
3. Modifier la reference dans `entities.py` pour pointer vers le chemin local

#### 1.3 Leaflet local pour les previews cartes GUI

**Fichiers a modifier :**
- `src/niamoto/gui/api/services/map_renderer.py:249-250`

**Action** :
1. Telecharger `leaflet@1.9.4` (CSS + JS)
2. Placer dans `src/niamoto/publish/assets/js/vendor/leaflet/`
3. Modifier `_render_leaflet()` pour utiliser les chemins locaux
4. Pour les tuiles : en mode offline, utiliser un fond blanc/gris avec le GeoJSON overlay seulement. Afficher un bandeau discret "Fond de carte indisponible hors connexion".

#### 1.4 Remplacer placeholders mock

**Fichier a modifier :**
- `src/niamoto/gui/api/routers/site.py:1063-1068`

**Action** : Remplacer les URLs `placehold.co` par des data URIs SVG inline (placeholder generique gris avec icone image).

**Criteres d'acceptation Phase 1 :**
- [x] Les previews de widgets Plotly s'affichent sans internet
- [x] Les previews de layout s'affichent sans internet
- [x] Les cartes topojson des entites s'affichent sans internet
- [x] Les cartes Leaflet affichent le GeoJSON sur fond neutre sans internet
- [x] Les mocks n'ont plus de references a placehold.co

---

### Phase 2 — Detection Reseau et Indicateur UI (P1, effort faible-moyen)

**Objectif** : L'utilisateur sait a tout moment s'il est connecte et quelles fonctionnalites sont affectees.

#### 2.1 Hook frontend `useNetworkStatus`

**Fichier a creer :**
- `src/niamoto/gui/ui/src/hooks/useNetworkStatus.ts`

**Implementation** :
```typescript
// Logique :
// 1. Ecouter les events "online" / "offline" du navigateur
// 2. Optionnellement, appeler GET /api/health/connectivity pour verifier l'acces internet reel
// 3. Exposer { isOnline, isChecking, lastChecked }
```

`navigator.onLine` est peu fiable (renvoie `true` si connecte a un routeur sans internet). Le hook peut combiner :
- `navigator.onLine` pour la detection rapide (evenements browser)
- Un appel backend `/api/health/connectivity` declenche on-demand (avant enrichment/deploy) pour la fiabilite

#### 2.2 Endpoint backend `/api/health/connectivity`

**Fichier a modifier :**
- `src/niamoto/gui/api/routers/health.py`

**Action** : Ajouter un endpoint leger qui tente un HEAD request vers un service externe fiable (ex: `https://dns.google` ou `https://1.1.1.1`) avec timeout de 3 secondes.

```python
@router.get("/connectivity")
async def check_connectivity():
    """Verifie l'acces internet (non bloquant, timeout 3s)."""
    # Retourne { "online": true/false, "latency_ms": 42 }
```

#### 2.3 Indicateur offline dans le TopBar

**Fichiers a modifier :**
- `src/niamoto/gui/ui/src/components/layout/TopBar.tsx` (ou equivalent)

**Design** :
- **Online** : aucun indicateur (etat par defaut, pas de bruit visuel)
- **Offline** : icone `WifiOff` discreet dans la barre, couleur ambre
- **Au clic** : tooltip ou petit popup listant les fonctionnalites affectees :
  - "Enrichissement API : indisponible"
  - "Publication : indisponible"
  - "Tuiles cartographiques : indisponibles"

#### 2.4 Desactivation conditionnelle des features online-only

**Fichiers a modifier :**
- Composants d'enrichissement : bouton "Enrichir" desactive avec tooltip
- Composants de deploy : bouton "Deployer" desactive avec tooltip
- Formulaire test API : message "Connexion impossible" apres timeout 5s

**Criteres d'acceptation Phase 2 :**
- [x] Un indicateur visuel apparait dans le TopBar quand offline
- [x] Le bouton Enrichir est desactive avec tooltip explicatif quand offline
- [x] Le bouton Deployer est desactive avec tooltip explicatif quand offline
- [x] L'indicateur disparait quand la connexion revient
- [x] Le test API affiche un message clair apres 5s de timeout

---

### Phase 3 — Gestion Gracieuse de l'Enrichissement Offline (P1, effort moyen)

**Objectif** : L'enrichissement ne gaspille pas de temps/ressources quand offline.

#### 3.1 Auto-pause apres echecs reseau consecutifs

**Fichier a modifier :**
- `src/niamoto/gui/api/routers/enrichment.py` (fonction `_run_enrichment_job`)

**Logique** :
- Compter les echecs consecutifs de type reseau (`ConnectionError`, `TimeoutError`, `DNSLookupError`)
- Apres **5 echecs consecutifs** de type reseau : auto-pause du job
- Mettre a jour le statut du job : `"paused_offline"` (distinct de `"paused"` manuel)
- Cote frontend : afficher "Job en pause — connexion internet perdue. Reprendra automatiquement quand la connexion sera retablie."

#### 3.2 Reprise automatique optionnelle

Quand le hook `useNetworkStatus` detecte un retour en ligne :
- Si un job d'enrichissement est en statut `"paused_offline"` : afficher une notification "Connexion retablie — reprendre l'enrichissement ?"
- L'utilisateur confirme ou annule (pas de reprise automatique silencieuse)

#### 3.3 Timeout sur le preview enrichissement

**Fichier a modifier :**
- `src/niamoto/gui/api/routers/enrichment.py` (endpoint `/preview`)

**Action** : Ajouter un timeout explicite de 10 secondes sur l'appel API. En cas de timeout, retourner une erreur claire : `"Impossible de contacter l'API d'enrichissement. Verifiez votre connexion internet."`

**Criteres d'acceptation Phase 3 :**
- [x] L'enrichissement s'auto-pause apres 5 echecs reseau consecutifs
- [x] Le statut `paused_offline` est distinct du pause manuel
- [x] Le frontend affiche un message clair quand le job est en pause offline
- [x] La reconnexion propose de reprendre le job (avec confirmation utilisateur)
- [x] Le preview enrichissement a un timeout de 10s avec message explicite

---

### Phase 4 — Polices Locales pour le GUI Desktop (P2, effort faible)

**Objectif** : Le GUI desktop affiche les bonnes polices meme offline.

#### 4.1 Bundler les polices des themes

**Fichiers a modifier :**
- `src/niamoto/gui/ui/src/themes/presets/field.ts`
- `src/niamoto/gui/ui/src/themes/presets/neutral.ts`
- `src/niamoto/gui/ui/src/themes/presets/herbarium.ts`
- `src/niamoto/gui/ui/src/themes/presets/laboratory.ts`
- `src/niamoto/gui/ui/src/themes/presets/forest.ts`
- `src/niamoto/gui/ui/src/themes/index.ts` (fonction `loadThemeFonts`)

**Strategie** :
1. Telecharger les fichiers WOFF2 des polices referees (seuls les poids utilises)
2. Les placer dans `src/niamoto/gui/ui/public/fonts/`
3. Creer un fichier CSS `fonts.css` avec les `@font-face` declarations
4. Modifier `loadThemeFonts()` pour :
   - En mode desktop (`isTauri`) : charger depuis `/fonts/`
   - En mode web : conserver le lien Google Fonts (CDN disponible)

**Polices a bundler** (estimation ~3-5 MB total en WOFF2) :
- Inter (neutral) : 400, 500, 600, 700
- Nunito + DM Sans (forest) : 400-700
- IBM Plex Sans (laboratory) : 400-600
- Crimson Pro + Cormorant Garamond (herbarium) : 400-600
- Caveat + Source Sans 3 (field) : 400-700
- JetBrains Mono (tous) : 400, 500

**Note** : Les pages statiques exportees conservent les liens Google Fonts car elles sont destinees a etre deployees en ligne.

**Criteres d'acceptation Phase 4 :**
- [x] Les 5 themes affichent les bonnes polices en mode desktop offline
- [x] Le mode web continue d'utiliser Google Fonts CDN
- [x] La taille ajoutee au bundle est documentee (2.7 MB WOFF2, 64 @font-face rules)

---

### Phase 5 — Cartes Interactives : Strategie Offline (P2, effort moyen)

**Objectif** : Les cartes affichent les donnees GeoJSON meme sans tuiles de fond.

#### 5.1 Fallback `white-bg` pour les cartes Plotly

**Fichier a modifier :**
- `src/niamoto/core/plugins/widgets/interactive_map.py`

**Logique** :
- Le style de carte est configure par l'utilisateur dans `map_style` (ex: `open-street-map`, `carto-positron`, `white-bg`)
- Ajouter une option de config `offline_fallback_style: "white-bg"` (defaut)
- Les pages exportees incluent un snippet JS qui :
  1. Tente de charger les tuiles
  2. Si echec apres timeout (3s), bascule sur `white-bg`
  3. Affiche un message discret "Fond de carte indisponible"

#### 5.2 Documentation de la limitation

- Documenter dans le guide utilisateur que les cartes interactives necessitent une connexion internet pour le fond de carte
- L'overlay GeoJSON (limites, points) est toujours visible quel que soit l'etat de la connexion

**Criteres d'acceptation Phase 5 :**
- [x] Les cartes Plotly affichent le GeoJSON sur fond blanc quand les tuiles sont inaccessibles
- [x] Un message discret indique que le fond de carte est indisponible
- [x] Le fallback se declenche apres un timeout de 5s ou 3 erreurs de tuiles (pas de blocage)

---

## Ce qui est Hors Scope

| Sujet | Raison |
|-------|--------|
| **Cache de tuiles cartographiques** | Effort disproportionne (stockage, invalidation, regions) |
| **Service Worker** | Inutile en mode desktop (Tauri sert les assets localement) |
| **Sync enrichissement offline** | La fonctionnalite est explicitement online-only |
| **Jobs persistants (SQLite)** | Traite dans un plan separe (T1 du overview) |
| **PWA / mode web offline** | Le mode web est secondaire, le focus est desktop |
| **Deploy multi-plateforme** | Traite dans un plan separe (T3 du overview) |

---

## Risques et Mitigations

| Risque | Probabilite | Impact | Mitigation |
|--------|-------------|--------|------------|
| Migration Plotly 2.35 -> 3.0.1 casse des rendus | Faible | Moyen | Tester visuellement les 10+ types de widgets existants |
| Taille du bundle augmente (polices + JS vendors) | Certain | Faible | ~5-8 MB, acceptable pour une app desktop |
| `navigator.onLine` peu fiable | Connue | Faible | Combine avec endpoint backend pour verifications critiques |
| Tuiles de carte manquantes degrade l'experience | Moyen | Moyen | Fallback `white-bg` + message explicatif clair |

---

## Estimation d'Effort

| Phase | Description | Effort | Fichiers |
|-------|-------------|--------|----------|
| **Phase 1** | CDN -> local (Plotly, topojson, Leaflet) | ~3h | 5-6 fichiers |
| **Phase 2** | Detection reseau + indicateur UI | ~4h | 4-5 fichiers |
| **Phase 3** | Enrichissement gracieux offline | ~3h | 2-3 fichiers |
| **Phase 4** | Polices locales desktop | ~2h | 6-7 fichiers |
| **Phase 5** | Cartes fallback offline | ~3h | 1-2 fichiers |
| **Total** | | **~15h** | **~20 fichiers** |

---

## References

### Fichiers Cles

- Architecture Tauri : `src-tauri/src/lib.rs` (lancement sidecar)
- Configuration Tauri : `src-tauri/tauri.conf.json` (CSP, externalBin)
- App FastAPI : `src/niamoto/gui/api/app.py` (montage routes + static)
- Preview service : `src/niamoto/gui/api/services/preview_service.py:71`
- Layout preview : `src/niamoto/gui/api/routers/layout.py:452`
- Entities preview : `src/niamoto/gui/api/routers/entities.py:452`
- Map renderer : `src/niamoto/gui/api/services/map_renderer.py:249`
- Plotly local : `src/niamoto/core/plugins/widgets/plotly_utils.py:12`
- Bundle Plotly : `src/niamoto/publish/assets/js/vendor/plotly/3.0.1_plotly.min.js`
- Themes polices : `src/niamoto/gui/ui/src/themes/presets/*.ts`
- Enrichment : `src/niamoto/gui/api/routers/enrichment.py`
- Deploy : `src/niamoto/gui/api/routers/deploy.py`
- Health : `src/niamoto/gui/api/routers/health.py`
- Runtime mode : `src/niamoto/gui/ui/src/hooks/useRuntimeMode.ts`

### Documentation Architecture

- Desktop app : `docs/10-roadmaps/gui/DESKTOP_APP.md`
- Distribution binaire : `docs/10-roadmaps/gui/BINARY_DISTRIBUTION.md`
- FastAPI double usage : `docs/06-gui/fastapi-dual-purpose-architecture.md`
- Overview GUI : `docs/10-roadmaps/gui-finalization/00-overview.md`
