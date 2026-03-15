---
title: "Publication vers GBIF via Registry API"
type: feat
date: 2026-03-13
---

# Publication vers GBIF via Registry API

## Overview

Ajouter un plugin deployer `gbif_publisher` permettant de publier automatiquement les données Niamoto sur GBIF.org. Le plugin prend en entrée un DwC-A généré par l'exporteur existant, l'héberge à une URL publique, et l'enregistre via l'API Registry de GBIF.

## Contexte : comment fonctionne la publication GBIF

### L'IPT n'est PAS une API

L'**Integrated Publishing Toolkit (IPT)** est une webapp Java auto-hébergée avec une interface graphique. Elle ne dispose d'**aucune API d'écriture** — seulement des endpoints GET en lecture :

| Endpoint IPT | Méthode | Usage |
|---|---|---|
| `/inventory/dataset` | GET | Inventaire JSON des ressources |
| `/rss.do` | GET | Flux RSS des publications |
| `/archive.do?r={name}` | GET | Télécharger le DwC-A |
| `/eml.do?r={name}` | GET | Télécharger les métadonnées EML |

L'IPT est conçu pour les organisations qui veulent une interface web pour gérer manuellement leurs publications. **Ce n'est pas le bon chemin pour une intégration programmatique.**

### La GBIF Registry API : le bon chemin

La **GBIF Registry API** (`https://api.gbif.org/v1/`) permet d'enregistrer des datasets directement, sans passer par l'IPT. C'est ce qu'utilisent les plateformes comme EarthCape pour leur publication automatisée.

**Le flux de publication GBIF :**

```
Niamoto                          GBIF
┌──────────────────┐            ┌──────────────────────────┐
│ 1. Génère DwC-A  │            │                          │
│    (déjà fait)   │            │                          │
├──────────────────┤            │                          │
│ 2. Héberge le    │───URL──────│ 3. POST /v1/dataset      │
│    ZIP à une URL │  publique  │    → crée le dataset     │
│    HTTPS publique│            │                          │
│                  │            │ 4. POST /v1/dataset/     │
│                  │            │    {uuid}/endpoint       │
│                  │            │    → indique l'URL DwC-A │
│                  │            │                          │
│                  │◄───crawl───│ 5. GBIF crawle le ZIP    │
│                  │            │    (auto, 1-60 min)      │
│                  │            │                          │
│                  │            │ 6. Données indexées       │
│                  │            │    sur gbif.org           │
└──────────────────┘            └──────────────────────────┘
```

### Appels API concrets

**Créer un dataset :**
```http
POST https://api.gbif.org/v1/dataset
Content-Type: application/json
Authorization: Basic {base64(username:password)}

{
  "publishingOrganizationKey": "ORG-UUID",
  "installationKey": "INSTALL-UUID",
  "type": "OCCURRENCE",
  "title": "Niamoto Biodiversity Data",
  "description": "Occurrence records from the Niamoto platform",
  "language": "fra",
  "license": "http://creativecommons.org/licenses/by/4.0/lc/legalcode"
}
```
→ Retourne un dataset UUID.

**Ajouter l'endpoint DwC-A :**
```http
POST https://api.gbif.org/v1/dataset/{dataset-uuid}/endpoint
Content-Type: application/json
Authorization: Basic {base64(username:password)}

{
  "type": "DWC_ARCHIVE",
  "url": "https://your-server.com/data/dwc-archive.zip"
}
```

**Déclencher un crawl immédiat (optionnel) :**
```http
POST https://api.gbif.org/v1/dataset/{dataset-uuid}/crawl
Authorization: Basic {base64(username:password)}
```

### Prérequis organisationnels (étape humaine, one-time)

| Étape | Action | Délai estimé |
|---|---|---|
| 1 | S'inscrire comme publisher sur [gbif.org/become-a-publisher](https://www.gbif.org/become-a-publisher) | Immédiat |
| 2 | Être endossé par un noeud GBIF participant (France ou Pacifique) | Jours à semaines |
| 3 | Demander à `helpdesk@gbif.org` les droits de publication API pour un compte | Quelques jours |
| 4 | Obtenir les UUIDs : organization_key + installation_key | Avec l'étape 3 |

**Environnement de test :** `https://api.gbif-uat.org/v1/` — créer un compte test sur `https://www.gbif-uat.org` pour développer sans toucher à la production.

### Licences acceptées par GBIF

Seules 3 licences sont acceptées :
- **CC0** (domaine public)
- **CC-BY 4.0**
- **CC-BY-NC 4.0**

### Types de datasets GBIF

- `OCCURRENCE` — enregistrements d'occurrences (le cas principal Niamoto)
- `CHECKLIST` — listes taxonomiques
- `SAMPLING_EVENT` — événements d'échantillonnage avec protocole
- `METADATA` — métadonnées seules

---

## Solution proposée

### Architecture : un deployer plugin `gbif_publisher`

Le plugin s'intègre dans l'architecture existante des deployers (comme `cloudflare.py`, `github.py`, etc.) :

```
src/niamoto/core/plugins/deployers/
├── models.py           ← ajouter GbifPublishConfig
├── cloudflare.py
├── github.py
├── netlify.py
├── ...
└── gbif.py             ← NOUVEAU
```

**Pourquoi un deployer et pas un exporter ?** Parce que :
- L'export DwC-A existe déjà (`dwc_archive_exporter`)
- Le deployer est en aval de l'export (même pattern que GitHub Pages/Cloudflare)
- L'architecture SSE async des deployers permet le feedback en temps réel dans le GUI

### Flux complet dans Niamoto

```yaml
# export.yml
exports:
  - name: dwc_archive
    exporter: dwc_archive_exporter
    params:
      output_dir: exports/dwc
      archive_name: dwc-archive.zip
      metadata:
        title: "Flora of New Caledonia"
        description: "Occurrence records from ecological inventories"
        publisher: "IRD / Niamoto"
        rights: "CC-BY-4.0"
        contact_name: "Julien Barbe"
        contact_email: "contact@example.com"
    groups:
      - group_by: occurrences
        transformer_plugin: niamoto_to_dwc_occurrence
```

```yaml
# deploy via GUI ou CLI
deploy:
  platform: gbif
  project_name: niamoto-flora-nc
  extra:
    gbif_api: https://api.gbif-uat.org/v1   # ou api.gbif.org en prod
    organization_key: "ORG-UUID"
    installation_key: "INSTALL-UUID"
    dataset_type: OCCURRENCE
    dataset_uuid: null                        # null = créer, UUID = mettre à jour
    trigger_crawl: true
    dwca_path: exports/dwc/dwc-archive.zip
    hosting:
      method: ssh                             # ou s3, github_release, manual
      url: "https://data.niamoto.io/dwc/dwc-archive.zip"
      ssh_target: "user@server:/var/www/data/dwc/"
```

### Le problème de l'hébergement du DwC-A

GBIF ne reçoit pas le fichier — il le **télécharge** depuis une URL publique. Cela signifie que le DwC-A doit être hébergé quelque part. Options :

| Méthode | Complexité | Pérennité | Coût |
|---|---|---|---|
| **SSH/rsync** vers un serveur web | Faible | Haute | Serveur existant |
| **S3 / R2 / B2** avec URL publique | Moyenne | Haute | Quelques centimes/mois |
| **GitHub Release** | Faible | Haute | Gratuit |
| **Deployer existant** (Netlify, etc.) | Faible | Moyenne | Gratuit |
| **URL manuelle** | Nulle | Variable | Variable |

**Recommandation** : réutiliser les deployers existants (SSH, GitHub) pour héberger le ZIP, puis enchaîner avec l'enregistrement GBIF. Le deployer `gbif_publisher` orchestre les deux étapes.

### Pseudo-code du plugin

```python
# src/niamoto/core/plugins/deployers/gbif.py

@register("gbif_publisher", PluginType.DEPLOYER)
class GbifPublisherPlugin(DeployerPlugin):
    """Publish DwC-A to GBIF via Registry API."""

    async def deploy(self, config: DeployConfig) -> AsyncIterator[str]:
        extra = config.extra
        gbif_api = extra["gbif_api"]
        auth = self._get_credentials()  # CredentialService

        # 1. Vérifier que le DwC-A existe
        dwca_path = Path(extra["dwca_path"])
        if not dwca_path.exists():
            yield self.sse_error(f"DwC-A not found: {dwca_path}")
            return

        yield self.sse_log(f"Found DwC-A: {dwca_path} ({dwca_path.stat().st_size / 1024:.0f} KB)")

        # 2. Héberger le DwC-A (si hosting configuré)
        dwca_url = extra.get("hosting", {}).get("url")
        if extra.get("hosting", {}).get("method") == "ssh":
            yield self.sse_log("Uploading DwC-A via SSH...")
            await self._upload_ssh(dwca_path, extra["hosting"])
            yield self.sse_log(f"Uploaded to {dwca_url}")

        # 3. Créer ou mettre à jour le dataset
        dataset_uuid = extra.get("dataset_uuid")
        async with httpx.AsyncClient(base_url=gbif_api, auth=auth, timeout=60) as client:
            if not dataset_uuid:
                yield self.sse_log("Creating new dataset on GBIF...")
                resp = await client.post("/dataset", json={
                    "publishingOrganizationKey": extra["organization_key"],
                    "installationKey": extra["installation_key"],
                    "type": extra.get("dataset_type", "OCCURRENCE"),
                    "title": config.project_name,
                    # ... metadata from DwC-A eml.xml
                })
                resp.raise_for_status()
                dataset_uuid = resp.text.strip('"')
                yield self.sse_log(f"Dataset created: {dataset_uuid}")
            else:
                yield self.sse_log(f"Updating existing dataset: {dataset_uuid}")

            # 4. Enregistrer l'endpoint DwC-A
            yield self.sse_log(f"Registering DwC-A endpoint: {dwca_url}")
            resp = await client.post(f"/dataset/{dataset_uuid}/endpoint", json={
                "type": "DWC_ARCHIVE",
                "url": dwca_url,
            })
            resp.raise_for_status()

            # 5. Déclencher le crawl (optionnel)
            if extra.get("trigger_crawl", True):
                yield self.sse_log("Triggering GBIF crawl...")
                await client.post(f"/dataset/{dataset_uuid}/crawl")
                yield self.sse_log("Crawl triggered. Ingestion in 1-60 minutes.")

            # 6. Retourner l'URL du dataset sur GBIF
            gbif_url = f"https://www.gbif.org/dataset/{dataset_uuid}"
            yield self.sse_url(gbif_url)
            yield self.sse_success(f"Published to GBIF: {gbif_url}")
            yield self.sse_done()
```

### Configuration des credentials

Réutiliser le `CredentialService` existant :

```python
# Stocké via le GUI ou CLI
credentials = {
    "gbif": {
        "username": "niamoto_publisher",
        "password": "****",
        "organization_key": "ORG-UUID",
        "installation_key": "INSTALL-UUID",
    }
}
```

Alternative : variables d'environnement (`$ENV:GBIF_USERNAME`, `$ENV:GBIF_PASSWORD`) comme le fait déjà `api_taxonomy_enricher.py`.

---

## Approches alternatives considérées

### 1. Intégrer un IPT auto-hébergé
- **Rejeté** : ajoute une dépendance Java lourde, interface graphique inutile si on automatise
- L'IPT n'a pas d'API d'écriture, donc l'intégration programmatique est impossible

### 2. Utiliser pygbif pour la publication
- **Rejeté** : pygbif (v0.6.6) est **read-only** pour le Registry — il ne supporte que les GET
- Utile pour la validation et le download, pas pour la publication

### 3. Publication manuelle via l'interface web GBIF
- **Rejeté pour l'automatisation** : le but est un pipeline reproductible
- Mais reste une option de fallback pour les utilisateurs non techniques

---

## Acceptance Criteria

### Fonctionnel
- [ ] Le plugin `gbif_publisher` peut créer un nouveau dataset sur GBIF (test sur UAT)
- [ ] Le plugin peut mettre à jour un dataset existant (via dataset_uuid stocké)
- [ ] Le DwC-A est hébergé à une URL publique HTTPS avant enregistrement
- [ ] Le crawl est déclenché automatiquement après publication
- [ ] Les logs SSE permettent de suivre la progression dans le GUI
- [ ] Le dataset_uuid est persisté pour les publications suivantes

### Technique
- [ ] Auth via `CredentialService` ou variables d'environnement (jamais en dur dans le YAML)
- [ ] Support de l'environnement UAT (`gbif-uat.org`) pour les tests
- [ ] Gestion d'erreurs : org non endossée, credentials invalides, DwC-A invalide
- [ ] Le plugin s'intègre dans le système de deploy existant (GUI + CLI)

### Tests
- [ ] Test unitaire avec mock de l'API GBIF
- [ ] Test d'intégration sur `api.gbif-uat.org` (avec credentials de test)
- [ ] Test du flux complet : export DwC-A → hébergement → publication GBIF

---

## Dépendances et risques

### Prérequis bloquant (humain)
**L'organisation doit être enregistrée et endossée sur GBIF.** C'est un processus qui prend des jours/semaines et nécessite une interaction avec le helpdesk GBIF.

**Action immédiate recommandée** : lancer l'inscription sur [gbif.org/become-a-publisher](https://www.gbif.org/become-a-publisher) dès maintenant, en parallèle du développement.

### Risques techniques

| Risque | Impact | Mitigation |
|---|---|---|
| Endorsement GBIF trop long | Bloque les tests en prod | Utiliser l'env UAT pour développer |
| URL DwC-A inaccessible par GBIF crawler | Dataset non indexé | Vérifier l'accessibilité publique avant publication |
| EML metadata insuffisant | Rejet par GBIF | Valider l'EML contre le schéma GBIF avant soumission |
| Changement de l'API GBIF Registry | Plugin cassé | Versionner l'API (v1), surveiller les changelogs |

### Dépendances

- `httpx` : déjà utilisé par les deployers existants
- `dwc_archive_exporter` : doit être exécuté avant le deployer
- Un serveur web ou stockage cloud pour héberger le ZIP (existant : SSH deployer réutilisable)

---

## Intégration dans le plan GBIF Challenge

Ce plugin s'insère dans la **Phase 5** du plan challenge (enrichissement + publication) :

```
Phase 1-4: Pipeline DOI/CSV → DwC-A → portail web (MVP)
Phase 5:   Enrichissement en chaîne + PUBLICATION GBIF  ← ici
Phase 6-9: SDM, LLM, GUI, documentation
```

**Pour le challenge**, la démonstration de publication GBIF directe depuis le pipeline serait un argument fort :

> *"Niamoto génère un DwC-A validé et le publie directement sur GBIF.org — sans passer par l'IPT, sans intervention manuelle, en une commande."*

---

## Références

### Documentation officielle GBIF
- [Registering a dataset using the API](https://techdocs.gbif.org/en/data-publishing/register-dataset-api)
- [GBIF Registry API (OpenAPI)](https://techdocs.gbif.org/en/openapi/v1/registry)
- [Quick guide to publishing data](https://www.gbif.org/publishing-data)
- [Become a GBIF publisher](https://www.gbif.org/become-a-publisher)
- [IPT User Manual](https://ipt.gbif.org/manual/en/ipt/latest/)
- [Dataset classes](https://www.gbif.org/dataset-classes)

### Code existant Niamoto
- `src/niamoto/core/plugins/exporters/dwc_archive_exporter.py` — génération DwC-A
- `src/niamoto/core/plugins/deployers/` — architecture deployer (models, SSE, async)
- `src/niamoto/core/plugins/deployers/github.py` — pattern upload + API calls
- `src/niamoto/core/plugins/deployers/ssh.py` — pattern rsync
- `src/niamoto/core/plugins/loaders/api_taxonomy_enricher.py` — pattern auth multi-méthodes

### Exemples tiers
- [EarthCape — Agile GBIF Publishing](https://earthcape.com/agile-gbif-publishing/) — plateforme ayant intégré la publication API
- [GBIF Community Forum — Publishing via API](https://discourse.gbif.org/t/how-to-publish-data-via-the-gbif-api-gbif-technical-support-hour-for-nodes/4575)
