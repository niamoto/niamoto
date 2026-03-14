---
title: "feat: Multi-platform deployment from GUI"
type: feat
date: 2026-03-13
---

# Multi-Platform Deployment from GUI

## Overview

Permettre le déploiement du site statique généré (`exports/web/`) vers **6 plateformes** (Cloudflare Workers, GitHub Pages, Netlify, Vercel, Render, SSH/SFTP) entièrement depuis l'interface GUI, sans dépendance CLI externe (Node.js, wrangler, netlify-cli). Cible deux profils : chercheurs non techniques (flow guidé) et techniciens données (options avancées).

## Problem Statement / Motivation

Actuellement, seul Cloudflare Pages est déployable via le GUI, et il nécessite :
- Node.js installé sur la machine (`npx wrangler`)
- `CLOUDFLARE_API_TOKEN` comme variable d'environnement système
- Connaissance technique pour configurer le token

**Pourquoi c'est bloquant :** Un écologue de terrain ne sait pas ce qu'est une variable d'environnement. Le workflow Import → Transform → Export est complet dans le GUI, mais la dernière étape (Deploy) casse l'expérience en exigeant la ligne de commande.

**Contexte :** Cloudflare Pages a été **déprécié en avril 2025** au profit de Workers avec Static Assets. L'implémentation actuelle via `wrangler pages deploy` fonctionne encore (wrangler gère la migration) mais toute nouvelle implémentation doit cibler l'API Workers.

## Proposed Solution

### Architecture

```
┌──────────────────────────────────────────────────┐
│  GUI (React/TS)                                  │
│  ┌────────────┐  ┌───────────┐  ┌─────────────┐ │
│  │ SetupWizard│  │ DeployView│  │ HistoryView │ │
│  └─────┬──────┘  └─────┬─────┘  └──────┬──────┘ │
│        │               │               │         │
│  ──────┼───────────────┼───────────────┼──────── │
│        ▼               ▼               ▼         │
│  POST /api/deploy/  POST /api/deploy/  GET /api/ │
│  credentials/save   {platform}/deploy  deploy/   │
│                     (SSE streaming)    history    │
└──────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────┐
│  FastAPI Backend (Python)                        │
│                                                  │
│  ┌──────────────┐  ┌──────────────────────────┐  │
│  │CredentialSvc │  │ DeployService            │  │
│  │ (keyring)    │  │ ├── CloudflareDeployer   │  │
│  │              │  │ ├── GitHubDeployer       │  │
│  │ .get(plat)   │  │ ├── NetlifyDeployer     │  │
│  │ .save(plat)  │  │ ├── VercelDeployer      │  │
│  │ .save(plat)  │  │ ├── RenderDeployer      │  │
│  │ .save(plat)  │  │ └── SshDeployer (rsync) │  │
│  │ .delete(plat)│  │                          │  │
│  │ .validate()  │  │ Tous utilisent httpx     │  │
│  └──────────────┘  │ sauf SSH → rsync         │  │
│                    └──────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### Credentials : Python `keyring`

Chaque plateforme stocke ses secrets dans le trousseau OS via la lib Python `keyring` :

| Plateforme | Service keyring | Identifiant | Valeur |
|------------|-----------------|-------------|--------|
| Cloudflare | `niamoto-deploy` | `cloudflare-api-token` | API Token |
| Cloudflare | `niamoto-deploy` | `cloudflare-account-id` | Account ID |
| GitHub | `niamoto-deploy` | `github-token` | Personal Access Token |
| Netlify | `niamoto-deploy` | `netlify-token` | Personal Access Token |
| Vercel | `niamoto-deploy` | `vercel-token` | Personal Access Token |
| Render | `niamoto-deploy` | `render-token` | API Key |
| SSH | `niamoto-deploy` | `ssh-{host}-password` | Password (optionnel) |

Config non sensible (project name, branch, host, path) → `publishStore` (Zustand/localStorage).

### Authentification par plateforme

Toutes les plateformes utilisent la même approche : **token personnel guidé**. Pas d'OAuth — évite la complexité de maintenir des OAuth Apps et reste indépendant de tout service tiers.

| Plateforme | Credentials | Flow UX (wizard) |
|------------|-------------|-------------------|
| Cloudflare | API Token + Account ID | Lien direct vers `dash.cloudflare.com/profile/api-tokens` → Create Token → permissions Workers Scripts Edit → coller |
| GitHub | Personal Access Token (fine-grained) | Lien vers `github.com/settings/tokens?type=beta` → scope `contents:write` sur le repo cible → coller |
| Netlify | Personal Access Token | Lien vers `app.netlify.com/user/applications#personal-access-tokens` → coller |
| Vercel | Personal Access Token | Lien vers `vercel.com/account/tokens` → Create Token → coller |
| Render | API Key | Lien vers `dashboard.render.com/settings#api-keys` → Create API Key → coller |
| SSH | Clé SSH (fichier) ou mot de passe | Sélecteur de fichier pour la clé, ou saisie du mot de passe |

Chaque wizard : 3 étapes numérotées avec captures d'écran, lien "ouvrir dans le navigateur", champ de saisie avec validation immédiate (appel API test), message de succès/échec clair.

### APIs de déploiement (sans CLI externe)

| Plateforme | API | Méthode |
|------------|-----|---------|
| Cloudflare Workers | Direct Upload API (3 étapes : manifest → upload → deploy) | `httpx` |
| GitHub Pages | Git Data API (blobs → tree → commit → update ref) | `httpx` |
| Netlify | Deploy API (upload ZIP) | `httpx` |
| Vercel | Deployments API (upload fichiers + create deployment) | `httpx` |
| Render | Deploy Hook (trigger) ou Static Site API | `httpx` |
| SSH/SFTP | `rsync` subprocess | Seule dépendance externe, préinstallé sur macOS/Linux |

## Technical Considerations

### Cloudflare Workers Static Assets API

Remplacement de `npx wrangler pages deploy` par 3 appels HTTP :

1. **Manifest** : `POST /accounts/{account_id}/workers/scripts/{name}/assets-upload-session` — envoie le hash SHA-256 (16 premiers octets, hex) + taille de chaque fichier. Retourne un JWT + `buckets` (fichiers à uploader, les autres sont déjà sur le CDN → **déploiement incrémental natif**).

2. **Upload** : `POST /accounts/{account_id}/workers/assets/upload?base64=true` — multipart, chaque part = hash + contenu base64. Retourne un completion JWT.

3. **Deploy** : `PUT /accounts/{account_id}/workers/scripts/{name}` — multipart avec metadata JSON (JWT, config html_handling) + script worker minimal (passthrough pour sites statiques).

**Limites** : 25 MiB/fichier, 20 000 fichiers max. → Vérification pré-deploy.

### GitHub Git Data API

Pas besoin de `git` installé. Pur HTTP :

1. `GET /repos/{owner}/{repo}/git/refs/heads/gh-pages` → SHA parent
2. `POST /repos/{owner}/{repo}/git/blobs` × N fichiers (base64)
3. `POST /repos/{owner}/{repo}/git/trees` → arbre complet
4. `POST /repos/{owner}/{repo}/git/commits` → commit
5. `PATCH /repos/{owner}/{repo}/git/refs/heads/gh-pages` → update ref

**Limites** : 100 MiB/fichier, 1 Go soft limit repo. Rate limit 5000 req/h.

**Scalabilité** : Chaque fichier = 1 appel API blob. Un site de 500 fichiers = 500+ appels. Pour les gros sites (>200 fichiers), prévoir :
- Barre de progression par lot (batch de blobs en parallèle, max 10 concurrent)
- Warning si >500 fichiers avec suggestion d'utiliser Netlify ou Cloudflare (upload unique)

### Netlify Deploy API (ZIP)

Le plus simple de tous :

```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/zip",
        },
        content=zip_bytes,
    )
```

Alternative incrémentale via file digest pour les gros sites (envoie les hashes, upload uniquement les fichiers modifiés). À considérer si les sites dépassent ~50 MiB (évite de re-uploader tout à chaque deploy).

**Limites** : 500 deploys/mois (free), 100 MiB/fichier.

### Vercel Deployments API

Upload de fichiers individuels puis création du deployment :

1. **Upload** : `POST /v2/files` — chaque fichier avec header `x-vercel-digest` (SHA-1). Les fichiers déjà présents sont ignorés (déploiement incrémental).

2. **Deploy** : `POST /v13/deployments` — envoie la liste des fichiers avec leurs SHA-1 et chemins :

```python
payload = {
    "name": project_name,
    "files": [
        {"file": "index.html", "sha": sha1_hex, "size": file_size},
        {"file": "css/style.css", "sha": sha1_hex, "size": file_size},
    ],
    "projectSettings": {"framework": None},  # site statique pur
}
```

**Limites** : 100 Go bande passante/mois (free), 100 deploys/jour, 50 MiB max par fichier.

### Render Static Site API

Render utilise un modèle différent : les sites statiques sont liés à un repo git. Pour du deploy sans git, deux approches :

1. **Deploy Hook** (le plus simple) : URL de webhook qui déclenche un re-deploy. Nécessite que le site soit déjà configuré avec un repo.

2. **API REST** : `POST /v1/services` pour créer un service static, puis trigger de deploy via `POST /v1/services/{id}/deploys`. Render pull depuis un repo — pas d'upload direct de fichiers.

**Approche recommandée pour Niamoto** : Utiliser l'API REST pour créer un Static Site pointant vers un repo GitHub (si l'utilisateur a aussi configuré GitHub). Sinon, le Deploy Hook est le fallback le plus simple — l'utilisateur configure une fois sur render.com, copie l'URL du hook.

**Limites** : Sites statiques gratuits illimités, 400 heures build/mois, 100 Go bande passante/mois.

### Sécurité

- Tokens jamais dans les logs SSE → sanitization du output avant streaming
- Tokens jamais dans localStorage → uniquement dans keyring OS
- Validation du token avant le premier deploy (appel API léger)
- Nettoyage des deploys orphelins au démarrage de l'app

### Staleness

Warning ambre sur la page Deploy quand le site est périmé (via `usePipelineStatus`), avec bouton "Reconstruire". Le deploy reste possible — l'utilisateur décide.

## Acceptance Criteria

### Phase 1 — Fondations (credential management + refactoring)

- [x] Service `CredentialService` Python avec CRUD keyring (`save`, `get`, `delete`, `validate`)
- [x] Endpoints API : `POST /api/deploy/credentials/{platform}` (save), `GET .../check` (exists?), `DELETE` (remove), `POST .../validate` (test API call)
- [x] Endpoint deploy changé de `GET` à `POST`
- [x] Bouton Deploy désactivé pendant un deploy en cours (fix bug actuel)
- [x] Nettoyage des deploys orphelins ("running") au démarrage
- [x] Sanitization des logs SSE (masquer tokens/secrets)
- [x] Bannière staleness sur la page Deploy
- [x] Vérification pré-deploy (taille fichiers, nombre fichiers) par plateforme

**Fichiers concernés :**
- `src/niamoto/gui/api/routers/deploy.py` — refactoring complet
- `src/niamoto/core/services/credential.py` — nouveau
- `src/niamoto/gui/ui/src/pages/publish/deploy.tsx` — fixes + bannière
- `src/niamoto/gui/ui/src/stores/publishStore.ts` — cleanup startup

### Phase 2 — Cloudflare Workers (migration wrangler → API directe)

- [x] `CloudflareDeployer` : implémente les 3 étapes Direct Upload API via `httpx`
- [x] Wizard setup guidé : lien vers dashboard Cloudflare, champs Account ID + API Token, validation immédiate
- [x] Déploiement incrémental (seuls les fichiers modifiés sont uploadés)
- [x] Progression : nombre de fichiers uploadés / total
- [x] URL de déploiement affichée (avec support custom domain optionnel)
- [ ] Migration transparente depuis l'ancienne config (si `CLOUDFLARE_API_TOKEN` env var existe, proposer de l'importer dans le keyring)

**Fichiers concernés :**
- `src/niamoto/core/services/deployers/cloudflare.py` — nouveau
- `src/niamoto/gui/ui/src/components/publish/wizards/CloudflareWizard.tsx` — nouveau

### Phase 3 — GitHub Pages + Netlify

- [x] `GitHubDeployer` : Git Data API (blobs → tree → commit → update ref) via `httpx`
- [x] UI GitHub : wizard token (PAT fine-grained), sélection repo owner/name + branche
- [x] `NetlifyDeployer` : ZIP upload via Netlify Deploy API
- [x] UI Netlify : wizard token (PAT), sélection/création de site
- [x] Streaming SSE pour les deux plateformes (progression upload)
- [x] Gestion token invalide/révoqué avec message explicite + lien vers re-création

**Fichiers concernés :**
- `src/niamoto/core/services/deployers/github.py` — nouveau
- `src/niamoto/core/services/deployers/netlify.py` — nouveau
- `src/niamoto/gui/ui/src/components/publish/wizards/GitHubWizard.tsx` — nouveau
- `src/niamoto/gui/ui/src/components/publish/wizards/NetlifyWizard.tsx` — nouveau

### Phase 4 — Vercel + Render

- [x] `VercelDeployer` : upload fichiers via `/v2/files` + create deployment via `/v13/deployments`
- [x] UI Vercel : wizard token, saisie nom de projet, déploiement incrémental (SHA-1)
- [x] `RenderDeployer` : trigger via Deploy Hook URL ou API REST
- [x] UI Render : wizard avec deux modes — Deploy Hook (coller l'URL) ou API Key + service ID
- [x] Streaming SSE pour les deux plateformes

**Fichiers concernés :**
- `src/niamoto/core/services/deployers/vercel.py` — nouveau
- `src/niamoto/core/services/deployers/render.py` — nouveau
- `src/niamoto/gui/ui/src/components/publish/wizards/VercelWizard.tsx` — nouveau
- `src/niamoto/gui/ui/src/components/publish/wizards/RenderWizard.tsx` — nouveau

### Phase 5 — SSH/SFTP + polish

- [x] `SshDeployer` : formulaire host/port/path/clé, rsync subprocess
- [x] UI SSH : sélecteur de fichier pour clé SSH, test de connexion
- [x] Bouton d'annulation de deploy (termine le subprocess backend)
- [x] Messages d'erreur traduits et explicites (mapping des erreurs API → messages FR/EN)

**Fichiers concernés :**
- `src/niamoto/core/services/deployers/ssh.py` — nouveau
- `src/niamoto/gui/ui/src/components/publish/wizards/SshWizard.tsx` — nouveau
- `src/niamoto/gui/ui/src/pages/publish/deploy.tsx` — cancel

## Dependencies & Risks

### Dépendances Python

| Package | Usage | Statut |
|---------|-------|--------|
| `keyring` | Stockage credentials OS | À ajouter |
| `httpx` | Appels API plateformes | Déjà présent |

### Risques

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Cloudflare Pages → Workers migration | L'API peut différer des docs | Tester avec un compte réel dès Phase 2 |
| GitHub PAT fine-grained : scope trop large ou trop restreint | Deploy échoue ou token trop permissif | Le wizard précise le scope exact (`contents:write` sur le repo cible). Validation immédiate à la saisie. |
| Netlify PAT : 500 deploys/mois sur free tier | Épuisement du quota en itération rapide | Afficher le compteur de deploys restants via `GET /api/v1/user` si disponible |
| Vercel : 100 deploys/jour sur free tier | Quota atteint en itération intensive | Compteur visible dans le wizard, warning à partir de 80 deploys/jour |
| Render : pas d'upload direct de fichiers | Nécessite un repo git comme source | Proposer le couplage avec GitHub, ou fallback Deploy Hook |
| `keyring` ne fonctionne pas headless (CI/serveur) | Pas de deploy en CI | Fallback sur variable d'env pour les contextes CI |
| `keyring` sur Linux sans desktop (pas de libsecret) | Credentials ne se sauvent pas | Détecter l'absence de backend keyring → fallback fichier chiffré local ou variable d'env |
| Gros sites (>20k fichiers) dépassent les limites Cloudflare | Deploy échoue | Vérification pré-deploy + message clair |
| rsync absent sur Windows | SSH ne fonctionne pas | Documenter comme "macOS/Linux only" ou utiliser paramiko comme fallback |

### Décision : pas d'OAuth, tokens manuels guidés

Pas d'OAuth Apps à maintenir. Toutes les plateformes utilisent des Personal Access Tokens créés par l'utilisateur via un wizard guidé (screenshots + lien direct + validation). Avantages :
- Aucune dépendance externe (pas de client_id à maintenir)
- Fonctionne pour tous les utilisateurs sans configuration côté Niamoto
- Le wizard compense la complexité de création du token
- Chaque token est scopé au minimum nécessaire (principe du moindre privilège)

## References & Research

### Internes
- Deploy CLI actuel : `src/niamoto/cli/commands/deploy.py`
- Deploy API actuel : `src/niamoto/gui/api/routers/deploy.py`
- Deploy GUI actuel : `src/niamoto/gui/ui/src/pages/publish/deploy.tsx`
- Store publish : `src/niamoto/gui/ui/src/stores/publishStore.ts`
- Pipeline status : `src/niamoto/gui/ui/src/hooks/usePipelineStatus.ts`
- Roadmap GUI : `docs/10-roadmaps/gui-finalization/00-overview.md` (T3 lacune "Deploy limité")
- i18n deploy : `src/niamoto/gui/ui/src/i18n/locales/fr/publish.json`

### Externes
- [Cloudflare Workers Direct Upload API](https://developers.cloudflare.com/workers/static-assets/direct-upload/)
- [Cloudflare Pages → Workers migration](https://developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/)
- [GitHub Device Flow](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow)
- [GitHub Git Data API (Trees)](https://docs.github.com/en/rest/git/trees)
- [Netlify Deploy API](https://docs.netlify.com/api-and-cli-guides/api-guides/get-started-with-api/)
- [Netlify OAuth2](https://www.netlify.com/blog/2016/10/10/integrating-with-netlify-oauth2/)
- [Vercel Deployments API](https://vercel.com/docs/rest-api/endpoints/deployments)
- [Vercel File Uploads](https://vercel.com/docs/rest-api/endpoints/artifacts)
- [Render API Reference](https://api-docs.render.com/)
- [Python keyring](https://pypi.org/project/keyring/)
