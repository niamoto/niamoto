# Guide de Référence des APIs pour Niamoto

Ce document recense les APIs pertinentes pour enrichir les données de Niamoto avec des informations taxonomiques, géographiques, climatiques et de conservation.

## Table des matières

1. [APIs de Taxonomie Végétale](#1-apis-de-taxonomie-végétale)
2. [APIs Géographiques et Géospatiales](#2-apis-géographiques-et-géospatiales)
3. [APIs Climatiques et Environnementales](#3-apis-climatiques-et-environnementales)
4. [APIs de Conservation et Biodiversité](#4-apis-de-conservation-et-biodiversité)
5. [APIs d'Imagerie et Reconnaissance Végétale](#5-apis-dimagerie-et-reconnaissance-végétale)
6. [APIs de Données Phénologiques et Herbarium](#6-apis-de-données-phénologiques-et-herbarium)
7. [APIs d'Observations Citoyennes](#7-apis-dobservations-citoyennes)

---

## 1. APIs de Taxonomie Végétale

### GBIF (Global Biodiversity Information Facility)

**Description**: Réseau international fournissant un accès libre aux données sur la biodiversité mondiale.

**URL de base**: `https://api.gbif.org/v1/`

**Endpoints principaux**:
- `/species/match` - Recherche de correspondance taxonomique
- `/species/{key}` - Détails d'une espèce par clé GBIF
- `/species/search` - Recherche d'espèces

**Authentification**: Aucune (API publique)

**Exemple de requête**:
```
GET https://api.gbif.org/v1/species/match?name=Pinus%20radiata&kingdom=Plantae
```

**Réponse type**:
```json
{
  "usageKey": 5285750,
  "scientificName": "Pinus radiata D.Don",
  "canonicalName": "Pinus radiata",
  "rank": "SPECIES",
  "status": "ACCEPTED",
  "confidence": 99,
  "matchType": "EXACT",
  "kingdom": "Plantae",
  "phylum": "Tracheophyta",
  "order": "Pinales",
  "family": "Pinaceae",
  "genus": "Pinus",
  "species": "Pinus radiata"
}
```

**Mapping Niamoto suggéré**:
- `gbif_key`: `usageKey`
- `gbif_status`: `status`
- `gbif_confidence`: `confidence`
- `canonical_name`: `canonicalName`
- `authorship`: Extraire de `scientificName`

**Limitations**: Pas de limite de taux officielle, mais usage raisonnable recommandé

**Statut 2024**: API stable v1, nouvelles fonctionnalités pour les intervalles de dates ISO 8601

---

### Tropicos (Missouri Botanical Garden)

**Description**: Base de données botanique spécialisée dans la flore néotropicale avec plus de 4.2 millions de spécimens d'herbier.

**URL de base**: `https://services.tropicos.org/`

**Endpoints principaux**:
- `/Name/Search` - Recherche de noms
- `/Name/{id}` - Détails d'un nom
- `/Name/{id}/Synonyms` - Synonymes
- `/Name/{id}/AcceptedNames` - Noms acceptés

**Authentification**: Clé API requise (gratuite sur demande)

**Paramètres**:
- `apikey`: Votre clé API
- `format`: `json` ou `xml`

**Exemple de requête**:
```
GET https://services.tropicos.org/Name/Search?name=Quercus%20alba&apikey=YOUR_KEY&format=json
```

**Mapping Niamoto suggéré**:
- `tropicos_id`: `NameId`
- `tropicos_name`: `ScientificName`
- `tropicos_author`: `ScientificNameWithAuthors`
- `family`: `Family`

**Limitations**: 1000 requêtes par jour avec clé gratuite

---

### IPNI (International Plant Names Index)

**Description**: Index nomenclatural pour les plantes vasculaires, fournissant les détails bibliographiques des premières publications.

**URL de base**: `https://www.ipni.org/api/1/`

**Endpoints principaux**:
- `/search` - Recherche générale
- `/id/{id}` - Détails par identifiant IPNI

**Authentification**: Aucune

**Exemple de requête**:
```
GET https://www.ipni.org/api/1/search?q=Eucalyptus%20globulus
```

**Réponse type**:
```json
{
  "results": [{
    "id": "327955-2",
    "name": "Eucalyptus globulus",
    "authors": "Labill.",
    "publishedIn": "Voy. Rech. Pérouse 1: 153 (1800)",
    "family": "Myrtaceae"
  }]
}
```

**Mapping Niamoto suggéré**:
- `ipni_id`: `id`
- `ipni_publication`: `publishedIn`
- `ipni_authors`: `authors`

---

### WFO (World Flora Online)

**Description**: Liste consensuelle mondiale des espèces végétales, mise à jour tous les 6 mois.

**URL de base**: `https://list.worldfloraonline.org/`

**Services disponibles**:
- API GraphQL pour accès flexible aux données
- Outil de correspondance en ligne
- API de réconciliation compatible OpenRefine

**Authentification**: Aucune actuellement

**GraphQL Endpoint**: `https://list.worldfloraonline.org/gql`

**Exemple de requête GraphQL**:
```graphql
query {
  taxonNameSearch(name: "Rosa canina") {
    results {
      id
      fullNameString
      nomenclaturalStatus
      taxonomicStatus
    }
  }
}
```

**Statut 2024**: Version 2024-12 publiée en décembre, prochaine version juin 2025

---

### Endemia NC

**Description**: API spécialisée pour la flore de Nouvelle-Calédonie avec informations sur l'endémisme et le statut de conservation.

**URL de base**: `https://api.endemia.nc/v1/`

**Endpoints principaux**:
- `/taxons` - Recherche de taxons

**Authentification**: Clé API requise

**Paramètres de requête**:
- `section`: `flore`
- `q`: Terme de recherche
- `maxitem`: Nombre max de résultats
- `excludes`: `meta,links`
- `includes`: `images`

**Exemple de configuration**:
```json
{
  "api_url": "https://api.endemia.nc/v1/taxons",
  "auth_method": "api_key",
  "query_params": {
    "section": "flore",
    "maxitem": "1",
    "excludes": "meta,links",
    "includes": "images"
  },
  "response_mapping": {
    "id_endemia": "id",
    "endemic": "endemique",
    "protected": "protected",
    "redlist_cat": "categorie_uicn",
    "image_url": "image.big_thumb"
  }
}
```

---

## 2. APIs Géographiques et Géospatiales

### OpenStreetMap / Nominatim

**Description**: Service de géocodage gratuit basé sur les données OpenStreetMap.

**URL de base**: `https://nominatim.openstreetmap.org/`

**Endpoints principaux**:
- `/search` - Géocodage (adresse → coordonnées)
- `/reverse` - Géocodage inverse (coordonnées → adresse)

**Authentification**: Aucune, mais User-Agent requis

**Exemple de géocodage**:
```
GET https://nominatim.openstreetmap.org/search?q=Nouméa&format=json&limit=1
```

**Exemple de géocodage inverse**:
```
GET https://nominatim.openstreetmap.org/reverse?lat=-22.2758&lon=166.4580&format=json
```

**Limitations**:
- Max 1 requête par seconde
- Usage intensif nécessite installation locale

**Avantages**:
- Gratuit et open source
- Peut être auto-hébergé pour usage intensif
- Excellente couverture mondiale

---

### Mapbox Geocoding API

**Description**: Service de géocodage commercial avec fonctionnalités avancées.

**URL de base**: `https://api.mapbox.com/geocoding/v5/`

**Endpoints**:
- `/mapbox.places/{query}.json` - Géocodage
- `/mapbox.places/{lon},{lat}.json` - Géocodage inverse

**Authentification**: Token d'accès requis

**Fonctionnalités avancées**:
- Support des adresses secondaires (appartements, bureaux)
- Entrée structurée pour meilleure précision
- Stockage permanent des résultats autorisé
- Géocodage par lot disponible

**Exemple**:
```
GET https://api.mapbox.com/geocoding/v5/mapbox.places/Nouméa.json?access_token=YOUR_TOKEN
```

**Tarification**:
- 100 000 requêtes gratuites/mois
- $0.50 pour 1000 requêtes supplémentaires

---

### APIs d'Élévation

#### Open-Elevation

**URL**: `https://api.open-elevation.com/api/v1/lookup`

**Méthode**: POST

**Exemple de requête**:
```json
{
  "locations": [
    {"latitude": -22.2758, "longitude": 166.4580}
  ]
}
```

**Réponse**:
```json
{
  "results": [{
    "latitude": -22.2758,
    "longitude": 166.4580,
    "elevation": 17
  }]
}
```

---

## 3. APIs Climatiques et Environnementales

### NOAA Climate Data API

**Description**: Données climatiques historiques et actuelles du service météorologique américain.

**URL de base**: `https://www.ncdc.noaa.gov/cdo-web/api/v2/`

**Authentification**: Token requis (gratuit)

**Endpoints principaux**:
- `/data` - Données climatiques
- `/stations` - Informations sur les stations
- `/locations` - Emplacements disponibles

**Types de données disponibles**:
- Température (min, max, moyenne)
- Précipitations
- Humidité
- Pression atmosphérique
- Vitesse du vent

**Exemple**:
```
GET https://www.ncdc.noaa.gov/cdo-web/api/v2/data?datasetid=GHCND&locationid=FIPS:98&startdate=2024-01-01&enddate=2024-01-31&datatypeid=TMAX
Headers: token: YOUR_TOKEN
```

---

### OpenWeatherMap

**Description**: Service météo complet avec données actuelles, prévisions et historiques.

**URL de base**: `https://api.openweathermap.org/data/2.5/`

**Endpoints principaux**:
- `/weather` - Météo actuelle
- `/forecast` - Prévisions 5 jours
- `/onecall` - Données complètes (actuel + prévisions + historique)

**Authentification**: Clé API

**Exemple**:
```
GET https://api.openweathermap.org/data/2.5/weather?lat=-22.27&lon=166.45&appid=YOUR_KEY&units=metric
```

**Tarification**:
- Gratuit: 1000 appels/jour
- Plans payants disponibles

---

### SoilGrids REST API

**Description**: Données pédologiques mondiales à 250m de résolution.

**URL de base**: `https://rest.isric.org/soilgrids/v2.0/`

**Endpoints**:
- `/properties/query` - Requête ponctuelle
- `/properties/layers` - Liste des propriétés disponibles

**Propriétés disponibles**:
- Carbone organique (`soc`)
- pH (`phh2o`)
- Densité apparente (`bdod`)
- Capacité d'échange cationique (`cec`)
- Texture (argile, limon, sable)

**Exemple de requête**:
```
GET https://rest.isric.org/soilgrids/v2.0/properties/query?lon=166.45&lat=-22.27&property=soc&property=phh2o&depth=0-5cm&depth=5-15cm
```

**Réponse type**:
```json
{
  "properties": {
    "soc": {
      "0-5cm": {
        "mean": 58,
        "uncertainty": 23
      }
    },
    "phh2o": {
      "0-5cm": {
        "mean": 65,
        "uncertainty": 7
      }
    }
  }
}
```

**Limitations**: 5 requêtes par minute

---

### Open-Meteo Climate API

**Description**: Prévisions climatiques haute résolution jusqu'en 2050.

**URL de base**: `https://climate-api.open-meteo.com/v1/`

**Endpoints**:
- `/climate` - Projections climatiques

**Paramètres**:
- `latitude`, `longitude`
- `start_date`, `end_date`
- `models`: Modèles climatiques CMIP6
- `daily`: Variables quotidiennes

**Variables disponibles**:
- Température (min, max, moyenne)
- Précipitations
- Rayonnement solaire
- Évapotranspiration

**Gratuit** et sans limite de taux

---

## 4. APIs de Conservation et Biodiversité

### IUCN Red List API

**Description**: Base de données mondiale sur le statut de conservation des espèces.

**URL de base**:
- v3 (fin de vie mars 2025): `https://apiv3.iucnredlist.org/api/v3/`
- v4 (recommandé): `https://apiv4.iucnredlist.org/api/v4/`

**Authentification**: Token requis (gratuit sur demande)

**Endpoints principaux**:
- `/species/{name}` - Recherche par nom
- `/species/id/{id}` - Recherche par ID
- `/measures/species/name/{name}` - Mesures de conservation

**Catégories IUCN**:
- `EX` - Éteint
- `EW` - Éteint à l'état sauvage
- `CR` - En danger critique
- `EN` - En danger
- `VU` - Vulnérable
- `NT` - Quasi menacé
- `LC` - Préoccupation mineure
- `DD` - Données insuffisantes
- `NE` - Non évalué

**Exemple**:
```
GET https://apiv3.iucnredlist.org/api/v3/species/Pinus%20radiata?token=YOUR_TOKEN
```

**Réponse type**:
```json
{
  "name": "Pinus radiata",
  "result": [{
    "taxonid": 42408,
    "scientific_name": "Pinus radiata",
    "category": "EN",
    "criteria": "B1ab(ii,iii,v)+2ab(ii,iii,v)",
    "population_trend": "decreasing",
    "published_year": 2013
  }]
}
```

**Important**: Migrer vers v4 avant mars 2025

---

## 5. APIs d'Imagerie et Reconnaissance Végétale

### PlantNet API

**Description**: Identification automatique de plantes à partir de photos.

**URL de base**: `https://my-api.plantnet.org/v2/`

**Endpoints**:
- `/identify/{project}` - Identification d'images

**Authentification**: Clé API requise

**Projets disponibles**:
- `all` - Flore mondiale
- `useful-plants` - Plantes utiles
- Projets régionaux spécifiques

**Exemple de requête** (multipart/form-data):
```
POST https://my-api.plantnet.org/v2/identify/all?api-key=YOUR_KEY
Content-Type: multipart/form-data

organs: leaf
images: [fichier image]
```

**Réponse type**:
```json
{
  "query": {
    "project": "all",
    "images": ["image1.jpg"],
    "organs": ["leaf"]
  },
  "results": [{
    "score": 0.98765,
    "species": {
      "scientificNameWithoutAuthor": "Quercus robur",
      "scientificNameAuthorship": "L.",
      "genus": {
        "scientificNameWithoutAuthor": "Quercus"
      },
      "family": {
        "scientificNameWithoutAuthor": "Fagaceae"
      },
      "commonNames": ["Chêne pédonculé"]
    },
    "gbif": {
      "id": 2877951
    }
  }]
}
```

**Limitations**:
- 50 identifications/jour (gratuit)
- 500 identifications/jour (académique)

---

### iNaturalist API

**Description**: Plateforme d'observation naturaliste avec capacités d'identification.

**URL de base**: `https://api.inaturalist.org/v1/`

**Endpoints principaux**:
- `/observations` - Observations
- `/taxa` - Informations taxonomiques
- `/identifications` - Identifications communautaires
- `/places` - Lieux géographiques

**Authentification**: Optionnelle (OAuth2 pour écriture)

**Exemple de recherche d'observations**:
```
GET https://api.inaturalist.org/v1/observations?taxon_id=47219&place_id=6803&quality_grade=research
```

**Paramètres utiles**:
- `taxon_id`: ID du taxon
- `place_id`: ID du lieu
- `quality_grade`: `research` pour données validées
- `geo`: `true` pour observations géolocalisées
- `photos`: `true` pour observations avec photos

**Avantages**:
- Données validées par la communauté
- Photos haute qualité
- Métadonnées riches (observateur, date, lieu)

---

## 6. APIs de Données Phénologiques et Herbarium

### USA-NPN (National Phenology Network)

**Description**: Réseau national américain de phénologie avec données historiques et actuelles.

**Package R**: `rnpn` (recommandé)

**Installation R**:
```r
install.packages("rnpn")
library(rnpn)
```

**Fonctions principales**:
- `npn_species()` - Liste des espèces
- `npn_phenophases()` - Phases phénologiques
- `npn_observations()` - Données d'observation

**Authentification**: Auto-identification sur l'honneur

**Exemple R**:
```r
# Recherche d'observations pour une espèce
obs <- npn_observations(
  species_id = 35,
  start_date = "2024-01-01",
  end_date = "2024-12-31"
)
```

**Types de données**:
- Dates de floraison
- Feuillaison
- Fructification
- Sénescence

---

### GBIF - Données d'Herbarium

**Description**: Accès aux spécimens d'herbarium numérisés mondialement.

**Recherche de spécimens**:
```
GET https://api.gbif.org/v1/occurrence/search?basisOfRecord=PRESERVED_SPECIMEN&scientificName=Eucalyptus%20grandis
```

**Paramètres spécifiques herbarium**:
- `basisOfRecord=PRESERVED_SPECIMEN`
- `institutionCode`: Code de l'herbarium
- `catalogNumber`: Numéro de catalogue

**Métadonnées disponibles**:
- Date de collecte
- Collecteur
- Localisation précise
- Images haute résolution
- Annotations

---

### Phenobase

**Description**: Système d'intégration de données phénologiques avec raisonnement automatique.

**Statut**: En développement actif

**Objectifs**:
- Intégration herbarium + observations terrain
- Ontologie phénologique standardisée
- Liens entre spécimens historiques et données modernes

---

## 7. APIs d'Observations Citoyennes

### iNaturalist (Détails complets)

**Description**: Plus grande plateforme mondiale d'observations naturalistes citoyennes.

**Statistiques 2024**:
- 230+ millions d'observations
- 290 000 utilisateurs actifs/mois
- 4000+ publications scientifiques

**API REST Endpoints**:

#### Observations
```
GET /v1/observations
```
Paramètres:
- `user_id`: Observations d'un utilisateur
- `project_id`: Observations d'un projet
- `d1`, `d2`: Dates de début/fin
- `lat`, `lng`, `radius`: Zone géographique
- `iconic_taxa`: Groupe taxonomique (Plantae, etc.)

#### Espèces d'une zone
```
GET /v1/observations/species_counts?place_id=7241
```

#### Export en masse
```
GET /v1/observations/export
```

**Formats disponibles**: JSON, CSV, KML

**Flux de données**:
1. Observations → iNaturalist
2. Validation communautaire → Grade recherche
3. Export → GBIF
4. Images → Encyclopedia of Life

**Intégration Niamoto suggérée**:
- Import d'observations validées localement
- Enrichissement avec photos communautaires
- Suivi de nouvelles espèces dans une région

---

## Recommandations d'Implémentation

### Architecture suggérée

1. **Service d'enrichissement centralisé**
   ```python
   class EnrichmentService:
       def __init__(self):
           self.providers = {
               'gbif': GBIFProvider(),
               'iucn': IUCNProvider(),
               'inaturalist': iNatProvider()
           }

       async def enrich_taxon(self, taxon_name):
           results = {}
           for provider in self.providers.values():
               results.update(await provider.fetch(taxon_name))
           return results
   ```

2. **Gestion du cache**
   - Cache Redis pour réponses API
   - TTL adapté par type de données
   - Stockage permanent des données stables

3. **Gestion des erreurs**
   - Retry avec backoff exponentiel
   - Fallback vers cache si API indisponible
   - Logging détaillé des échecs

### Priorités d'intégration

1. **Phase 1 - Essentiels**
   - GBIF (taxonomie de référence)
   - IUCN Red List (conservation)
   - OpenStreetMap (géocodage)

2. **Phase 2 - Enrichissement**
   - iNaturalist (observations locales)
   - SoilGrids (données pédologiques)
   - NOAA/OpenWeatherMap (climat)

3. **Phase 3 - Avancé**
   - PlantNet (identification images)
   - USA-NPN (phénologie)
   - APIs régionales spécifiques

### Considérations légales et éthiques

1. **Licences de données**
   - Vérifier compatibilité avec licence Niamoto
   - Attribution correcte des sources
   - Respect des conditions d'utilisation

2. **Limites de taux**
   - Implémenter queue avec rate limiting
   - Monitoring usage par API
   - Alertes approche limites

3. **Données sensibles**
   - Filtrer espèces menacées
   - Obscurcir localisations précises si nécessaire
   - Respecter embargos sur données

---

## Ressources supplémentaires

- [GBIF API Documentation](https://www.gbif.org/developer/summary)
- [iNaturalist API Reference](https://www.inaturalist.org/pages/api+reference)
- [TDWG Standards](https://www.tdwg.org/standards/)
- [DarwinCore Terms](https://dwc.tdwg.org/terms/)

---

*Document mis à jour le 7 janvier 2025*
