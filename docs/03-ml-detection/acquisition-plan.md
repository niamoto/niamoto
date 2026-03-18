# Plan d'Acquisition de Données pour le Benchmark ML Detection

## Objet

Ce document traduit la shortlist de sources candidates en plan d'acquisition
concret :

- quoi intégrer d'abord ;
- où stocker les données ;
- comment les brancher au gold set ;
- quels tags de benchmark leur associer ;
- quels critères utiliser pour décider si une source vaut l'effort.

Le principe est simple :

- on ne cherche pas le volume maximal ;
- on cherche le meilleur **ROI benchmark** pour la cible produit réelle.

## Cible produit retenue

Les priorités déclarées à ce stade sont :

1. jeux de données du type :
   - Nouvelle-Calédonie
   - Gabon / Cameroun
   - Guyane
   - datasets des instances réellement testées
   - jeux pas nécessairement très standardisés
2. GBIF comme seconde grande priorité

Conséquence :

- `forest_inventory` doit rester un garde-fou utile ;
- mais il ne doit pas piloter seul la roadmap d'acquisition.

## Structure cible recommandée

La structure actuelle de `data/silver` contient surtout :

- `ifn_france/`
- `finland_sweden/`
- `pasoh/`
- des fichiers plats à la racine

Pour les nouvelles sources, je recommande une structure plus explicite :

```text
data/silver/
  instances/
    <instance_name>/
  guyane/
    paracou/
    trinite/
    tresor/
  africa_tropical/
    rainbio/
    lope/
    seosaw/
  gbif_targeted/
    new_caledonia/
    guyane/
    gabon/
    cameroon/
```

Objectif :

- rendre la provenance lisible ;
- simplifier les tags benchmark ;
- éviter une racine `data/silver/` trop plate.

## Lot 1 — acquisition prioritaire

## 1. Datasets des instances réellement testées

### Pourquoi

- valeur benchmark maximale ;
- meilleure proximité avec le produit ;
- vrais headers, vraies anomalies, vraies attentes.

### Stockage recommandé

```text
data/silver/instances/<instance_name>/
```

### Tags benchmark recommandés

- `instance_real`
- `priority_main`
- `schema_style=field`
- `region=<region réelle si connue>`

### Intégration build_gold_set

Ajouter chaque dataset comme source explicite dans
[build_gold_set.py](/Users/julienbarbe/Dev/clients/niamoto/scripts/ml/build_gold_set.py)
avec :

- `name`
- `path`
- `labels`
- `language`
- `sample_rows`
- et si possible un bloc de métadonnées de benchmark dans le futur

### Critère de succès

Après intégration :

- on doit pouvoir mesurer `instance_real` séparément ;
- ce bucket doit devenir un composant central du benchmark principal.

## 2. Guyane tropicale ouverte

### Sources visées

- Paracou
- Guyafor / Trinité
- Guyafor / Trésor

### Pourquoi

- très proche du besoin tropical terrain ;
- bonne chance d'obtenir des colonnes de placettes, arbres, taxonomie, mesures,
  environnement ;
- utile pour enrichir `tropical_field` avec des données mieux alignées au
  produit.

### Stockage recommandé

```text
data/silver/guyane/paracou/
data/silver/guyane/trinite/
data/silver/guyane/tresor/
```

### Tags benchmark recommandés

- `tropical_field`
- `plot_inventory`
- `guyane`
- `priority_main`

### Critère de succès

- créer un sous-benchmark `guyane`
- mesurer séparément ses résultats dans les runs d'évaluation

### État actuel vérifié

Vérification Dataverse effectuée :

- `Paracou / ForestScan` : CSV principal publiquement accessible
- `Trinité` : CSV principal restreint, accès sur demande
- `Trésor` : CSV principal restreint, accès sur demande
- `Tibourou` : CSV principal restreint, accès sur demande
- `Montagne Tortue` : CSV principal restreint, accès sur demande

Conséquence opérationnelle :

- le premier lot intégrable immédiatement est `Paracou / ForestScan`
- les autres jeux Guyane restent dans la file d'acquisition avec statut
  `waiting_access`

### Avancement du lot 1

Déjà fait :

- récupération locale de `FGPlotsCensusData2023.csv`
- récupération des fichiers de description Guyafor disponibles
- intégration de `forestscan_paracou_census` dans le gold set

Résultat :

- `34` colonnes gold ajoutées
- gold set total : `2265` colonnes

Statut recommandé :

- `Paracou / ForestScan` : `done`
- `Trinité / Trésor / Tibourou / Montagne Tortue` : `waiting_access`

## 3. GBIF ciblé par région

### Régions à prendre d'abord

- Nouvelle-Calédonie
- Guyane française
- Gabon
- Cameroun

### Pourquoi

- GBIF reste une priorité produit ;
- mais il faut le cibler géographiquement plutôt que prendre un corpus global
  aveugle ;
- cela permet de construire un benchmark GBIF proche des zones d'intérêt.

### Stockage recommandé

```text
data/silver/gbif_targeted/new_caledonia/
data/silver/gbif_targeted/guyane/
data/silver/gbif_targeted/gabon/
data/silver/gbif_targeted/cameroon/
```

### Tags benchmark recommandés

- `gbif`
- `gbif_core_standard`
- `gbif_extended`
- `priority_main`
- `region=<...>`

### Critère de succès

Après intégration :

- distinguer `gbif_core_standard` et `gbif_extended` ;
- suivre en priorité le GBIF des régions cibles plutôt qu'un GBIF mondial trop
  facile.

### État actuel vérifié

Deux sous-lots GBIF ciblés existent maintenant :

1. `gbif_targeted/`
   - lot régional général
   - `5000` occurrences `Plantae` par région
   - régions intégrées :
     - `new_caledonia`
     - `guyane`
     - `gabon`
     - `cameroon`

2. `gbif_targeted_institutional/`
   - lot filtré institutionnel
   - conservé à ce stade pour :
     - `gabon`
     - `cameroon`
   - filtre :
     - `PRESERVED_SPECIMEN`, `MATERIAL_SAMPLE`, `OCCURRENCE`
     - présence de champs institutionnels
     - exclusion des grands jeux observationnels

### Avancement

Déjà fait :

- script de récupération
  [fetch_gbif_targeted.py](/Users/julienbarbe/Dev/clients/niamoto/scripts/data/fetch_gbif_targeted.py)
- récupération du lot régional général `NC/GF/GA/CM`
- récupération du lot institutionnel `GA/CM`
- intégration des 6 nouvelles sources GBIF ciblées dans le gold set

Apport observé dans le gold set :

- lot régional général :
  - `new_caledonia` : `41`
  - `guyane` : `38`
  - `gabon` : `37`
  - `cameroon` : `39`
- lot institutionnel :
  - `gabon` : `36`
  - `cameroon` : `36`

### Statut recommandé

- `gbif_targeted/new_caledonia` : `done`
- `gbif_targeted/guyane` : `done`
- `gbif_targeted/gabon` : `done`
- `gbif_targeted/cameroon` : `done`
- `gbif_targeted_institutional/gabon` : `done`
- `gbif_targeted_institutional/cameroon` : `done`
- `gbif_targeted_institutional/new_caledonia` : `deferred`
- `gbif_targeted_institutional/guyane` : `deferred`

## 4. Afrique tropicale élargie

### Sources visées

- RAINBIO
- ForestPlots Lopé si accès possible

### Pourquoi

- apporte une couverture Afrique tropicale directement utile ;
- complète Gabon/Cameroun même si tout n'est pas du plot inventory pur ;
- très utile pour taxonomie, localité, habitat et champs semi-structurés.

### Stockage recommandé

```text
data/silver/africa_tropical/rainbio/
data/silver/africa_tropical/lope/
```

### Tags benchmark recommandés

- `africa_tropical`
- `tropical_field` ou `occurrence` selon le jeu
- `priority_main`

## Lot 2 — après stabilisation du lot 1

## 5. ForestGEO

- utile pour élargir les inventaires forestiers
- à intégrer après les priorités régionales
- tags :
  - `plot_inventory`
  - `forest_network`
  - `priority_secondary`

## 6. sPlotOpen

- utile pour la diversité de placettes végétation
- plutôt benchmark d'élargissement
- tags :
  - `vegetation_plot`
  - `priority_secondary`

## 7. SEOSAW

- utile si besoin woodland / savanna
- tags :
  - `africa_tropical`
  - `savanna_plot`
  - `priority_secondary`

## Lot 3 — seulement si besoin explicite

## 8. TRY

- utile surtout pour les traits ;
- plus pertinent pour enrichir l'ontologie ou les affordances que pour la
  détection brute.

## 9. OBIS

- à intégrer seulement si la partie marine/littorale devient importante ;
- potentiellement utile pour Nouvelle-Calédonie marine.

## 10. AusPlots

- bon benchmark de robustesse ;
- pas prioritaire au regard de la cible produit actuelle.

## Intégration dans build_gold_set.py

## Format minimal recommandé par source

Chaque nouvelle source devrait être ajoutée dans la liste des sources avec au
minimum :

```python
{
    "name": "...",
    "path": ROOT / "data/silver/...",
    "labels": ...,
    "language": "...",
    "sample_rows": ...,
}
```

## Métadonnées à prévoir

Le script actuel ne structure pas encore ces tags explicitement, mais je
recommande de préparer l'extension vers :

- `region`
- `source_family`
- `schema_style`
- `priority_tier`

Exemple conceptuel :

```python
{
    "name": "paracou_trees",
    "path": ROOT / "data/silver/guyane/paracou/trees.csv",
    "labels": PARACOU_TREE_LABELS,
    "language": "fr",
    "sample_rows": 1000,
    "benchmark_tags": {
        "region": "guyane",
        "source_family": "plot_inventory",
        "schema_style": "field",
        "priority_tier": "main",
    },
}
```

Même si `benchmark_tags` n'est pas encore consommé directement, prévoir cette
forme simplifiera l'évolution du protocole d'évaluation.

## Pipeline recommandé d'intégration

Pour chaque nouvelle source :

1. télécharger / normaliser dans `data/silver/...`
2. inspecter les colonnes et choisir un sous-ensemble annotable
3. écrire les `LABELS`
4. ajouter l'entrée dans `build_gold_set.py`
5. régénérer le gold set
6. vérifier son effet sur :
   - `primary`
   - `tropical_field`
   - `gbif_core_standard`
   - `gbif_extended`
   - `instance_real`

## Ce qu'il ne faut pas faire

- ajouter massivement du GBIF global non ciblé sans distinguer `core` et
  `extended`
- intégrer des datasets éloignés du produit avant les données d'instances
- laisser les nouvelles sources diluer le benchmark principal
- intégrer une source simplement parce qu'elle est grande

## Critères de sélection avant intégration

Une source vaut l'effort si au moins deux critères sont vrais :

- proche d'une zone ou d'un usage prioritaire ;
- headers non triviaux ;
- valeurs réalistes et exploitables ;
- variation utile par rapport au gold set existant ;
- probabilité forte d'améliorer la robustesse sur la cible produit.

## Ordre d'exécution recommandé

### Sprint 1

1. datasets d'instances réelles
2. Paracou
3. Trinité
4. Trésor

### Sprint 2

1. GBIF ciblé Nouvelle-Calédonie
2. GBIF ciblé Guyane
3. GBIF ciblé Gabon
4. GBIF ciblé Cameroun

### Sprint 3

1. RAINBIO
2. ForestPlots Lopé si accès possible
3. ForestGEO ou sPlotOpen selon disponibilité

## Critère de succès global

À l'issue du lot 1, le benchmark doit pouvoir répondre clairement à :

- est-on bon sur les datasets réels des instances ?
- est-on bon sur les jeux tropicaux de terrain ?
- est-on bon sur le GBIF ciblé des régions importantes ?
- les régressions sur `forest_inventory` restent-elles contenues ?

## Décision recommandée

Si on veut avancer efficacement :

1. intégrer d'abord les données d'instances réelles
2. enrichir ensuite Guyane
3. construire un sous-benchmark GBIF ciblé
4. élargir ensuite à l'Afrique tropicale

Le reste vient après.
