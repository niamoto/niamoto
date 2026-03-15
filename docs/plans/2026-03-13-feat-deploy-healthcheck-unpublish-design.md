# Design : Health Check & Dépublication des sites déployés

**Date** : 2026-03-13
**Statut** : Validé
**Contexte** : Le dashboard Deploy (refonte cartes) ne permet pas de savoir si un site déployé est toujours en ligne, ni de le dépublier sans aller sur l'interface du provider.

## Décisions

- Health check via proxy backend (évite les problèmes CORS depuis Tauri/localhost)
- Dépublication pour les 5 providers API (GitHub, Cloudflare, Netlify, Vercel, Render). SSH exclu.
- Après dépublication, la carte reste avec badge "Hors ligne" — la config locale est conservée, on peut redéployer en 1 clic
- Vérification simple au chargement de la page, pas de polling automatique

## Architecture

```
Frontend (deploy.tsx)                    Backend (deploy.py)              Provider APIs
┌─────────────────┐                    ┌──────────────────┐
│ Site Card        │─── GET /health ──▶│ HEAD request     │──▶ site URL
│  [●] En ligne    │◀── {status}  ─────│ (httpx, 5s)      │
│                  │                    │                  │
│ Menu [...] ──────│── POST /unpublish ▶│ unpublish()      │──▶ Provider API
│  Dépublier       │◀── SSE stream ────│ (même pattern    │    (DELETE branch,
│                  │                    │  que deploy)     │     worker, site...)
└─────────────────┘                    └──────────────────┘
```

## Backend

### Health check

Endpoint `GET /api/deploy/health?url=https://...` :
- `HEAD` request via httpx (timeout 5s, follow redirects)
- Retourne `{ "status": "up" | "down" | "unknown", "statusCode": 200, "responseTime": 142 }`
- Pas de token nécessaire — requête publique

### Dépublication

Nouvelle méthode abstraite dans `DeployerPlugin` :
- `async def unpublish(self, config: DeployConfig) -> AsyncIterator[str]`
- Même pattern SSE que `deploy()`
- Implémentation par défaut qui yield une erreur "Not supported"
- Endpoint `POST /api/deploy/unpublish` (même structure que `/execute`)

### Actions par provider

| Provider   | Action                        | API Call                                                     |
|------------|-------------------------------|--------------------------------------------------------------|
| GitHub     | Supprimer la branche gh-pages | `DELETE /repos/{owner}/{repo}/git/refs/heads/{branch}`       |
| Cloudflare | Supprimer le Worker           | `DELETE /accounts/{account_id}/workers/scripts/{script_name}`|
| Netlify    | Supprimer le site             | `DELETE /api/v1/sites/{site_id}`                             |
| Vercel     | Supprimer le projet           | `DELETE /v9/projects/{project_name}`                         |
| Render     | Suspendre le service          | `POST /v1/services/{service_id}/suspend`                     |
| SSH        | Non supporté                  | Retourne une erreur explicite                                |

## Frontend

### Health check

- Au montage de la page, pour chaque carte ayant une `deploymentUrl` dans l'historique
- Appel `GET /api/deploy/health?url=...`
- Point coloré sur la carte : vert (up), rouge (down), gris (checking/unknown)
- Rafraîchissable via le menu `[...]` ("Vérifier le statut")

### Dépublication

- Item "Dépublier" dans le `DropdownMenu` (icône `CloudOff`)
- `AlertDialog` avec confirmation : "Le site sera supprimé de {platform}. La configuration locale sera conservée."
- `POST /api/deploy/unpublish` avec streaming SSE
- Après succès : badge "Hors ligne"

### Badge "offline"

- En plus de "configured", "deployed", "failed"
- Apparaît quand health check retourne `down` sur un site `deployed`
- Ou après une dépublication réussie

## i18n

Nouvelles clés `deploy.dashboard.*` :
- `unpublish`, `unpublishConfirmTitle`, `unpublishConfirmDescription`
- `unpublishSuccess`, `unpublishNotSupported`
- `healthOnline`, `healthOffline`, `healthChecking`, `checkHealth`

## Fichiers impactés

1. `src/niamoto/core/plugins/base.py` — Ajouter `unpublish()` à `DeployerPlugin`
2. `src/niamoto/core/plugins/deployers/{github,cloudflare,netlify,vercel,render,ssh}.py` — Implémenter `unpublish()`
3. `src/niamoto/gui/api/routers/deploy.py` — Endpoints `/health` et `/unpublish`
4. `src/niamoto/gui/ui/src/pages/publish/deploy.tsx` — Health check + menu dépublier
5. `src/niamoto/gui/ui/src/i18n/locales/{fr,en}/publish.json` — Nouvelles clés
