# Feedback System — Brainstorm

**Date** : 2026-04-03
**Statut** : Orientation validée, cadrage sécurité/privacy à finaliser pour la V1

## Ce qu'on construit

Un système de feedback intégré à l'app Niamoto Desktop permettant aux utilisateurs (chercheurs, botanistes) de signaler des bugs, suggérer des améliorations, ou poser des questions. Les feedbacks sont envoyés directement comme GitHub Issues via un proxy Cloudflare Worker.

## Pourquoi cette approche

- **Audience non-technique** : les botanistes n'ont pas de compte GitHub → le proxy crée les Issues en leur nom
- **Friction minimale** : un bouton toujours visible dans la sidebar, un formulaire modal simple
- **Transparence** : l'utilisateur voit exactement quelles données sont envoyées
- **Traçabilité** : tout atterrit dans GitHub Issues avec labels, facile à trier et suivre
- **Sécurité raisonnable** : le token GitHub reste côté Worker, jamais dans l'application
- **Coût zéro** : Cloudflare Workers (100K req/jour gratuit) + R2 (10GB gratuit)

## Décisions clés

### 1. Architecture : Cloudflare Worker proxy

```
App Niamoto → POST /feedback → CF Worker → GitHub Issues API
                                    └──→ CF R2 (images)
```

L'app n'a jamais le token GitHub. Le Worker détient un fine-grained PAT avec scope `issues:write` sur `niamoto/niamoto` uniquement.

Le Worker n'est pas là pour "faire joli" : il sert de couche minimale de contrôle entre l'app et GitHub. Sans lui, il faudrait soit embarquer un token GitHub dans l'application, soit imposer une authentification GitHub aux utilisateurs, ce qui va à l'encontre du besoin initial.

**Sécurité** :
- Rate limit : 10 req/min par IP (natif Cloudflare)
- Clé API statique envoyée par l'app dans le header `X-Feedback-Key` — le Worker rejette les requêtes sans cette clé. Cette clé est un garde-fou anti-bruit, pas un mécanisme d'authentification fort : comme elle est embarquée dans le build, elle est récupérable par un utilisateur motivé. Elle reste utile pour filtrer les appels opportunistes les plus naïfs. Rotable via `wrangler secret`.
- Validation Worker : payload max 5MB, content-type JPEG vérifié sur le blob image, titre/type requis
- Sanitization : le texte utilisateur est échappé avant injection dans le template Markdown de l'Issue (prévention Markdown injection)
- Le vrai secret est le PAT GitHub, qui ne sort jamais du Worker

**Écarté** :
- Token embarqué dans l'app (extractible, risque de sécurité)
- API auto-hébergée sur Coolify (overengineered pour le volume)
- Webhook Discord/Slack (pas assez structuré pour le suivi)

### 2. Screenshot : html2canvas (DOM capture)

Capture le DOM de la fenêtre en image **avant** l'ouverture du modal (le screenshot est lancé, puis le modal s'affiche une fois la capture terminée). Cela garantit que le screenshot montre la page telle que l'utilisateur la voit, sans le modal par-dessus. Fonctionne 100% côté frontend, pas de code Rust à ajouter.

- Image compressée en JPEG 0.7, max 5MB
- Uploadée sur R2 par le Worker, URL incluse dans l'Issue
- L'utilisateur peut décocher l'envoi du screenshot

**Écarté** :
- Screenshot natif Tauri (nécessite crate Rust `xcap`, complexité cross-platform pour un gain marginal)
- Upload manuel (trop de friction pour des botanistes)

### 3. Données contextuelles : utiles, visibles, minimisées

Collectées automatiquement à l'ouverture du modal :

| Donnée | Source |
|--------|--------|
| `app_version` | `__APP_VERSION__` (injection Vite) |
| `os` | `navigator.userAgent` + Tauri `os.platform()` |
| `current_page` | React Router `useLocation()` |
| `runtime_mode` | Hook `useRuntimeMode()` existant |
| `theme` | Theme store |
| `language` | i18next `i18n.language` |
| `window_size` | `window.innerWidth × innerHeight` |
| `timestamp` | `new Date().toISOString()` |

Ajouts optionnels, visibles et désactivables :

| Donnée | Source |
|--------|--------|
| `diagnostic` | `GET /api/health/diagnostic` |
| `db_size` | Tauri `fs.stat()` sur le fichier DB pour obtenir la taille (desktop only) |
| `recent_errors` | Buffer circulaire console.error + unhandledrejection (10 dernières, avec timestamp et stack) |
| `screenshot` | Capture DOM via `html2canvas` |

Règles de minimisation pour la V1 :
- Tout est visible dans une section collapsible "Données envoyées" du formulaire
- Screenshot, logs récents et diagnostic détaillé restent optionnels
- Les chemins absolus, noms d'utilisateur locaux et autres valeurs potentiellement sensibles sont redacted avant envoi
- On envoie le minimum utile pour reproduire ou trier le problème, pas un dump exhaustif de l'environnement

### 4. Emplacement : bouton en bas de la sidebar + Command Palette

Icône `MessageSquarePlus` (Lucide React) en bas de la sidebar. Grisé quand hors connexion (via `useNetworkStatus()` existant).

**Fallback quand sidebar masquée** : la sidebar a un mode `hidden` (retourne `null`). Dans ce cas, le feedback reste accessible via la Command Palette (Cmd+K → "Feedback" / "Bug report"). Le modal est indépendant de la sidebar.

**WelcomeScreen / onboarding** : pas de bouton feedback avant le chargement d'un projet (le diagnostic et le contexte n'ont pas de sens sans projet ouvert).

### 5. Formulaire : modal avec sélecteur de type

Un seul point d'entrée, 3 types via toggle buttons :
- **Bug** 🐛 (défaut) — screenshot proposé avec preview visible
- **Suggestion** 💡 — screenshot auto désactivé
- **Question** ❓ — screenshot auto désactivé

Champs : titre (requis, 200 car. max), description (optionnelle, 5000 car. max).

### 6. Offline : bloqué avec message

Le bouton est grisé hors connexion avec tooltip explicatif. Pas de file d'attente locale (YAGNI).

## Format de l'Issue GitHub

```markdown
## 🐛 Bug Report

**Titre** : Le graphique ne s'affiche pas sur la page taxon

### Description
(texte de l'utilisateur)

### Screenshot
![screenshot](https://r2.niamoto.dev/feedback/2026-04-03-abc123.png)

### Contexte
| | |
|-|-|
| Version | 0.11.0 |
| OS | macOS 15.3 (arm64) |
| Page | /taxon/1234 |
| Mode | desktop |
| Thème | forest |
| Langue | fr |
| BDD | ok (45.2 MB) |
| Fenêtre | 1200×800 |

### Erreurs console
```
TypeError: Cannot read property 'data' of undefined
  at TaxonChart.tsx:42
```

---
*Envoyé depuis Niamoto Desktop v0.11.0*
```

Labels auto : `feedback`, `feedback:bug` / `feedback:suggestion` / `feedback:question`, `from:app`.

Notes :
- Le screenshot n'apparaît que si l'utilisateur a explicitement choisi de l'envoyer
- Les données de contexte affichées dans l'Issue sont une version résumée et redacted du contexte collecté

## Contrat API du Worker

### Requête
```
POST /feedback
Headers: X-Feedback-Key: <static-key>, Content-Type: application/json
Body: { type, title, description?, screenshot?, context }
```

### Réponses
| Status | Body | Signification |
|--------|------|---------------|
| `201` | `{ success: true, issue_url: "https://github.com/..." }` | Issue créée |
| `400` | `{ error: "missing_title" }` | Payload invalide |
| `401` | `{ error: "unauthorized" }` | Clé API manquante ou invalide |
| `429` | `{ error: "rate_limited", retry_after: 60 }` | Rate limit atteint |
| `502` | `{ error: "github_error", detail: "..." }` | GitHub API en erreur |
| `500` | `{ error: "internal_error" }` | Erreur Worker (R2, etc.) |

En cas de succès partiel (Issue créée mais upload image échoué) : retourne `201` avec `screenshot_uploaded: false`. L'Issue existe mais sans image — acceptable.

## États UX

| État | Comportement |
|------|-------------|
| Normal | Bouton actif, tooltip "Envoyer un feedback" |
| Hors connexion | Bouton grisé, tooltip "Feedback indisponible hors connexion" |
| Préparation screenshot | Skeleton sur la miniature (~1-2s), preview affichée avant envoi |
| Envoi en cours | Bouton spinner + "Envoi...", formulaire désactivé |
| Succès | Toast "Feedback envoyé !" + lien Issue, modal fermé |
| Échec réseau | Toast erreur, formulaire reste ouvert (pas de perte) |
| Rate limited (429) | Toast "Trop de feedbacks envoyés, réessayez dans quelques minutes" |
| Échec screenshot | Miniature remplacée par placeholder "Capture indisponible", envoi possible sans image |
| Passage offline pendant saisie | Bouton "Envoyer" grisé + message inline, formulaire préservé |
| Anti-spam | Bouton désactivé 30s après envoi réussi (cooldown global, avec compteur visible) |

## Composants impactés

### Nouveaux
- `src/features/feedback/` — feature module (modal, hooks, types)
- `workers/niamoto-feedback-proxy/` — Cloudflare Worker (repo séparé, déployé indépendamment via `wrangler`)

### Modifiés
- `NavigationSidebar.tsx` — ajout du bouton feedback
- `app/main.tsx` ou `RootProviders.tsx` — init du buffer console.error
- Namespace i18n `feedback` (nouveau fichier `feedback.json` dans chaque dossier locale, suivant le pattern existant)

### Dépendances ajoutées
- `html2canvas` (~40KB gzippé) — capture screenshot DOM

## Notes d'implémentation

- **R2 bucket** : créer un bucket `niamoto-feedback` avec un custom domain public (ex: `feedback-assets.niamoto.dev`) pour que GitHub puisse afficher les images dans les Issues
- **Console error buffer** : wrapper global sur `console.error` + listener `unhandledrejection`, initialisé dans `RootProviders.tsx`. Chaque entrée stocke `{ message, stack, timestamp }`. Buffer de 10 entrées max (circulaire).
- **Redaction** : avant envoi, remplacer automatiquement les chemins absolus locaux, noms d'utilisateur et segments sensibles évidents dans les logs, diagnostics et messages d'erreur affichés à l'utilisateur
- **html2canvas et thèmes** : limitation connue avec certaines propriétés CSS modernes (custom properties). Acceptable pour du feedback — la description textuelle complète le screenshot.
- **Format image** : JPEG (pas PNG) — le nom du fichier R2 utilise `.jpg` pour cohérence avec le content-type.

## Hors scope

- File d'attente offline (YAGNI — à ajouter si le besoin apparaît)
- Annotation sur screenshot (trop complexe pour V1)
- Authentification utilisateur (pas nécessaire via proxy)
- Dashboard de feedback dans l'app (GitHub Issues suffit)
- Mécanisme de sécurité fort côté client : la clé statique reste un filtre léger, pas une preuve d'identité
