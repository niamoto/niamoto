---
title: "feat: Standards-based dataset acquisition strategy for ML detection"
type: feat
date: 2026-03-21
---

# Standards-Based Dataset Acquisition Strategy for ML Detection

## Overview

Révision fondamentale de la stratégie d'acquisition de datasets d'entraînement
pour le classifieur ML de colonnes. Passage d'une approche « domaine seul »
(inventaires forestiers, écologie tropicale) + un standard (GBIF/DwC) vers une
approche **multi-standards** qui exploite les vocabulaires normalisés de 4
standards écologiques majeurs en complément du domaine existant.

**Constat** : le gold set actuel (2 231 colonnes, 88 datasets réels) repose
sur un seul standard formel (Darwin Core via GBIF) et des données de terrain à
headers ad-hoc. Le header model (macro-F1 0.77) bénéficierait directement de
l'injection de noms de colonnes normalisés issus d'autres standards, tandis que
le value model (macro-F1 0.35) profiterait de distributions de valeurs
caractéristiques de chaque standard.

## Blocking Preconditions

Avant toute nouvelle acquisition significative, trois prérequis doivent être
traités pour éviter d'augmenter le volume sur une base méthodologique fragile :

1. **Benchmark d'acceptation séparé du train**
   - geler au minimum un bucket `instances_real` et un bucket
     `coded_inventory`
   - ces jeux ne doivent pas être réinjectés dans `data/gold_set.json`

2. **Alignement des labels train/eval**
   - supprimer les divergences entre `build_gold_set.py` et
     `data/eval/annotations/*.yml` pour les datasets communs
   - si un dataset doit rester un vrai test d'acceptation, il doit sortir du
     train plutôt que porter des labels contradictoires

3. **Holdout anonymous leak-free**
   - ne plus persister de doublons anonymisés dans le gold set
   - générer l'anonymisation au moment de l'évaluation, à partir des exemples
     exclus du train du fold courant

Ces prérequis sont prioritaires sur toute phase d'acquisition ci-dessous.

## Problem Statement

### Limites identifiées

1. **Couverture FR faible** : holdout français à 67.5%, le plus bas de tous
   les langues testées. Cause : pas de données issues du standard français
   (SINP/INPN), seulement des headers IFN codés.

2. **Mono-standard** : Darwin Core est le seul standard formel dans le gold
   set. Les autres sources utilisent des conventions internes non
   reproductibles (IFN codes, FIA codes, noms de chercheurs).

3. **Concepts manquants** : les traits écologiques (`traitName`, `traitValue`,
   `dispersion`), le land-use (`predominant_land_use`, `use_intensity`), et la
   couverture végétation (`relative_cover`, `abundance_scale`) n'existent pas
   dans la taxonomie actuelle.

4. **Inventaires forestiers à ROI décroissant** : macro-F1 de 41-47% sur le
   bucket `forest_inventory` malgré l'ajout de données IFN/FIA. Les headers
   codés (ESPAR, SPCD, STATUSCD) ne généralisent pas.

### Opportunité

Quatre standards écologiques avec **vocabulaires normalisés** et **données CSV
disponibles** ont été identifiés comme complémentaires au Darwin Core :

| Standard | Champs uniques | Langue | Disponibilité CSV | Nouveaux concepts |
|----------|---------------|--------|-------------------|-------------------|
| SINP/INPN v2.0 | ~60+ | **FR** | Haute (OpenObs, TAXREF) | 0 (aliases FR) |
| ETS (Ecological Trait-data Standard) | 84 | EN | Haute (GitHub) | ~15 |
| PREDICTS | 67 | EN | Haute (NHM portal) | ~5 |
| sPlotOpen | 47+ | EN | Haute (iDiv) | ~5 |

## Proposed Solution

### Principe directeur

> **Chaque standard = un bloc d'aliases + des données représentatives + un
> bucket d'évaluation diagnostique.**

Le standard ne remplace pas l'approche domaine (tropical field, GBIF ciblé) ;
il la complète en apportant des noms de colonnes prévisibles et des
distributions de valeurs caractéristiques.

### Priorité produit révisée

L'ordre de priorité d'acquisition doit rester aligné avec le produit :

1. **instances réelles**
2. **données terrain tropicales / semi-standardisées**
3. **standards à fort levier direct** (`SINP`, puis `ETS`)
4. **standards plus éloignés du coeur produit** (`sPlotOpen`, `PREDICTS`)

Clarifications :

- `GBIF core standard` reste bien couvert et ne doit plus motiver d'expansion
  de volume à court terme ;
- `FIA` / `IFN` restent utiles comme **stress tests de headers codés**, mais
  plus comme axe principal d'acquisition d'entraînement.

### Architecture cible

```
column_aliases.yaml
├── dwc: (existant — Darwin Core)
├── sinp: (NOUVEAU — SINP OccTax v2.0 + TAXREF)
├── ets: (NOUVEAU — Ecological Trait-data Standard)
├── predicts: (NOUVEAU — PREDICTS schema)
├── splot: (NOUVEAU — sPlotOpen schema)
├── fr: (existant — enrichi avec headers GeoNature)
├── en: (existant — enrichi)
└── ...

concept_taxonomy.py
├── CONCEPT_MERGE (existant — ~45 concepts coarse)
├── + measurement.trait_name → measurement.trait
├── + measurement.trait_value → measurement.trait
├── + statistic.dispersion → statistic.count
├── + category.land_use → category.habitat
├── + category.use_intensity → category.management
├── + measurement.relative_cover → measurement.cover
├── + category.abundance_scale → statistic.count
└── + location.realm → location.admin_area

evaluate.py
├── _dataset_family() (enrichi)
│   ├── sinp_ → standards_based
│   ├── ets_ → standards_based
│   ├── predicts_ → standards_based
│   └── splot_ → standards_based
└── PRODUCT_SCORE_WEIGHTS (inchangé — standards_based = diagnostic only)
```

## Technical Approach

### Décisions architecturales

**D1. Nouveaux concepts = merge dans existants.**
Tous les concepts proposés fusionnent dans des concepts coarse existants via
`CONCEPT_MERGE`. Ceci évite la dilution du modèle (les nouveaux concepts
auraient < 5 exemples chacun). Le bénéfice vient des **aliases** (header
model) et des **valeurs** (value model), pas de nouveaux concepts.

**D2. Tags de langue dédiés par standard** (`sinp:`, `ets:`, `predicts:`,
`splot:`) dans `column_aliases.yaml`, similaire au `dwc:` existant. Ceci évite
les collisions avec les aliases génériques `fr:` ou `en:`.

**D3. Bucket d'évaluation `standards_based` diagnostique** (non pondéré dans
ProductScore). Les nouveaux standards sont mesurés séparément sans perturber
les métriques existantes. Migration vers ProductScore uniquement après
stabilisation.

**D4. TRY déféré.** Le format long-table de TRY (TraitID/TraitName/StdValue
sur chaque ligne) est incompatible avec le pipeline per-column actuel. Les
aliases TRY sont intégrés dans le bloc `ets:` (ETS et TRY partagent le même
vocabulaire). L'ingestion de données TRY comme training data est reportée à
une phase ultérieure, si un mécanisme de pivot est implémenté.

**D5. Intégration séquentielle avec évaluation après chaque phase.** Chaque
standard est intégré un par un avec snapshot d'évaluation. Ceci permet
d'attribuer toute régression à un standard spécifique.

### Implementation Phases

#### Phase 1A: SINP/INPN — Aliases FR + TAXREF v18

**Objectif** : poser une première couche `SINP` exploitable immédiatement,
centrée sur la taxonomie FR et l'exact-match runtime.

**Pourquoi en premier** : risque le plus bas (pas de nouveaux concepts,
uniquement des aliases sur concepts existants + une source taxonomique FR
structurée), bénéfice direct immédiat sur les colonnes standardisées.

**Étapes :**

1. **Ajouter le bloc `sinp:` à `column_aliases.yaml`**, mais seulement sur des
   concepts déjà supportés par le pipeline :

   ```yaml
   # Identifiants
   identifier.record:
     sinp: [idSINPOccTax, id_sinp, unique_id_sinp, idOrigine, id_origine,
            id_synthese, entity_source_pk_value]
   identifier.taxon:
     sinp: [cdNom, cd_nom, cdRef, cd_ref, cd_taxsup, cd_sup]

   # Taxonomie
   taxonomy.species:
     sinp: [nomCite, nom_cite, nomValide, nom_valide, nomComplet,
            nom_complet, lbNom, lb_nom, nomScientifique, nom_scientifique]
   taxonomy.vernacular_name:
     sinp: [nomVern, nom_vern, nomVernaculaire, nom_vernaculaire,
            nom_vern_eng]
   taxonomy.rank:
     sinp: [RANG]

   # Dates
   event.date:
     sinp: [dateDebut, date_debut, dateFin, date_fin, date_min, date_max,
            dateDetermination, date_determination, dEEDateDerniereModification,
            meta_create_date, meta_update_date]

   # Géographie
   location.locality:
     sinp: [nomLieu, nom_lieu, nomCommune, nom_commune]
   location.admin_area:
     sinp: [codeCommune, code_commune, codeDepartement, code_departement,
            nomDepartement, nom_departement, codeMaille, code_maille]
   location.elevation:
     sinp: [altitudeMin, altitude_min, altitudeMax, altitude_max,
            altitudeMoyenne]
   location.depth:
     sinp: [profondeurMin, depth_min, profondeurMax, depth_max,
            profondeurMoyenne]

   # Dénombrements
   statistic.count:
     sinp: [denombrementMin, denombrement_min, count_min, denombrementMax,
            denombrement_max, count_max]

   # Descripteurs biologiques
   category.ecology:
     sinp: [occSexe, occ_sexe, occStadeDeVie, occ_stade_de_vie,
            occEtatBiologique, occ_etat_biologique, occNaturalite,
            occ_naturalite, occStatutBiologique, occ_statut_biologique,
            occStatutBioGeographique, occComportement, occ_comportement,
            stadeDeVie, stade_de_vie, statutBiologique, statut_biologique]

   # Observateurs
   text.observer:
     sinp: [observers, determiner]

   # Méthode
   category.method:
     sinp: [obsTechnique, techniqueObservation, technique_observation,
            techniqueEchantillonnage, technique_echantillonnage,
            statutSource, statut_source, statutObservation,
            statut_observation]

   # Habitat
   category.habitat:
     sinp: [codeHabitat, code_habitat, refHabitat, codeHabRef]
   ```

2. **Intégrer `TAXREF v18`** depuis
   `data/silver/taxref/TAXREFv18.txt` comme première source `SINP/INPN`
   directement exploitable.

3. **Créer `TAXREF_V18_LABELS` dans `build_gold_set.py`** avec un mapping
   conservateur limité aux colonnes taxonomiques stables (`REGNE`, `PHYLUM`,
   `CLASSE`, `ORDRE`, `FAMILLE`, `CD_*`, `RANG`, `LB_NOM`, `LB_AUTEUR`,
   `NOM_*`, `HABITAT`).

4. **Ajouter la source `taxref_v18` au `SOURCES` list** avec `language: "fr"`
   et `sep: "\t"`.

5. **Vérifier les collisions** : tests ciblés du registre d'aliases sur les
   nouveaux headers `SINP`.

6. **Rebuild gold set** pour injecter `TAXREF v18` dans le corpus
   d'entraînement.

**Note de phase** : cette étape n'intègre pas encore de vraies observations
`SINP` et n'est donc pas suffisante pour mesurer un gain FR global à elle
seule. Elle prépare surtout la taxonomie et l'exact-match runtime.

**Fichiers impactés :**
- `src/niamoto/core/imports/ml/column_aliases.yaml`
- `scripts/ml/build_gold_set.py`

**Critère de succès :** `TAXREF v18` est intégré au gold set, les aliases
`sinp:` matchent au runtime, et aucune collision forte n'est introduite.

---

#### Phase 1B: SINP/INPN — Données d'observations OpenObs

**Statut** : bloqué par indisponibilité de la source `OpenObs / INPN` après la
cyberattaque du MNHN en 2025.

**Étapes prévues à la reprise de la source :**

1. Télécharger un export `OpenObs / SINP OccTax` pour une région cible
   (Nouvelle-Calédonie ou Guyane si disponible) et le stocker dans
   `data/silver/sinp/`.
2. Créer `SINP_OPENOBS_LABELS` dans `build_gold_set.py`.
3. Ajouter les sources `sinp_*` au pipeline d'évaluation diagnostique.
4. Rebuild gold set + évaluation ciblée FR.

---

#### Phase 2A: ETS — Vocabulaire de traits (aliases runtime)

**Objectif** : préparer la reconnaissance des exports de traits avec un bloc
`ets:` exploitable immédiatement au runtime.

**Pourquoi ensuite** : pas de datasets `ETS` disponibles dans le repo à ce
stade, mais le vocabulaire seul peut déjà améliorer l'exact-match sur des
headers normalisés de traits.

**Étapes :**

1. **Ajouter le bloc `ets:` à `column_aliases.yaml`**, mais seulement sur des
   concepts déjà présents dans le pipeline :

   ```yaml
   measurement.trait:
     ets: [traitName, trait_name, traitValue, trait_value, StdValue,
           traitID, trait_id,
           std_value, OrigValueStr, verbatimTraitName, verbatimTraitValue]
   measurement.dimension:
     ets: [traitUnit, trait_unit, UnitName, unit_name, expectedUnit,
           OrigUnitStr]
   measurement.quality:
     ets: [measurementResolution, ErrorRisk, error_risk,
           RelUncertaintyPercent]
   statistic.count:
     ets: [measurementValue_min, measurementValue_max, Replicates,
           replicates]
   category.method:
     ets: [statisticalMethod, ValueKindName, UncertaintyName,
           aggregateMeasure]
   category.ecology:
     ets: [morphotype]
   ```

2. **Ajouter des tests ciblés du registre d'aliases** pour sécuriser le bloc
   `ets:`.

3. **Préparer le dossier de dépôt `data/silver/ets/`** pour la future
   intégration des jeux de données réels.

**Note de phase** : on ne crée pas encore de nouveaux concepts comme
`identifier.trait` ou `measurement.unit`, et on n'ajoute pas encore de
datasets au gold set faute de fichiers disponibles.

**Fichiers impactés :**
- `src/niamoto/core/imports/ml/column_aliases.yaml`
- `tests/core/imports/test_alias_registry.py`

**Critère de succès :** les principaux headers ETS sont reconnus au runtime,
sans introduire de concepts orphelins ni de collisions majeures.

---

#### Phase 2B: ETS — Données alignées ETS

**Statut** : démarré. Trois fichiers d'extension `ETS` sont disponibles et
intégrés au gold set :

- `Occurrence_ext.csv`
- `Taxon_ext.csv`
- `Measurement_or_Fact_ext.csv`

**Décisions prises** :

- `ETS.csv` est traité comme dictionnaire du standard, pas comme dataset
  d'entraînement ;
- `species_trait_data.csv` est conservé pour inspection ultérieure, mais n'est
  pas intégré tant qu'un mapping sémantique plus propre n'est pas défini.

**Étapes prévues quand les données seront là :**

1. Intégrer les fichiers d'extension standards au gold set.
2. Décider si de nouveaux concepts fins sont réellement nécessaires à partir
   des colonnes observées, plutôt que les ajouter a priori.
3. Réévaluer `species_trait_data.csv` et les autres jeux de traits non
   normalisés.
4. Rebuild + évaluation ciblée.

---

#### Phase 3: sPlotOpen — Relevés de végétation

**Objectif** : enrichir la couverture végétation/plots avec un standard à
header normalisés

**Statut** : démarré. Les trois matrices principales sont intégrées au gold
set :

- `sPlotOpen_header(3).txt`
- `sPlotOpen_DT(2).txt`
- `sPlotOpen_CWM_CWV(2).txt`

**Décisions prises** :

- intégration conservatrice sur les concepts déjà existants du pipeline ;
- `Abundance_scale` est traité comme `category.method` ;
- les flags de resampling et les colonnes trop indirectes ne sont pas encore
  labellisés ;
- `sPlotOpen_metadata` reste à évaluer séparément.

**Étapes :**

1. **Ajouter les fine-grained concepts** :

   ```python
   "measurement.relative_cover": "measurement.cover",
   "category.abundance_scale": "statistic.count",
   "category.naturalness": "category.ecology",
   ```

2. **Ajouter le bloc `splot:` à `column_aliases.yaml`** :

   ```yaml
   identifier.plot:
     splot: [PlotObservationID, GIVD_ID, Original_plotID,
             Original_subplotID]
   measurement.cover:
     splot: [Relative_cover, relative_cover, percent_cover]
   statistic.count:
     splot: [Abundance_scale, abundance_scale, Original_abundance]
   taxonomy.species:
     splot: [Original_species, Species]
   text.observer:
     splot: [Releve_author, Releve_coauthor]
   text.metadata:
     splot: [Remarks, GUID, Project_name, Plot_Biblioreference]
   identifier.record:
     splot: [Original_nr_in_database, Nr_releve_in_table,
             Nr_table_in_publ]
   ```

3. **Créer LABELS séparés pour chaque matrice** :
   - `SPLOT_HEADER_LABELS` — 47 colonnes de la matrice header
   - `SPLOT_DT_LABELS` — 6 colonnes de la matrice espèces
   - `SPLOT_CWM_LABELS` — colonnes CWM trait means/variances

4. **Attention** : les colonnes dupliquées entre matrices
   (`PlotObservationID`) doivent être labellisées identiquement. Utiliser
   `sample_rows` distinct pour avoir des distributions de valeurs différentes.

5. **Rebuild + évaluation.**

**Critère de succès :** colonnes de cover/abundance correctement classifiées ;
pas de régression.

---

#### Phase 4: PREDICTS — Métriques de biodiversité et land-use

**Objectif** : enrichir les concepts macro-écologiques

**Pourquoi en dernier** : les concepts PREDICTS (`land_use`, `use_intensity`,
`realm`, `hotspot`) sont les plus éloignés du cœur produit Niamoto. Le
bénéfice est réel mais le risque de dilution est plus élevé.

**Étapes :**

1. **Ajouter les fine-grained concepts** :

   ```python
   "category.land_use": "category.habitat",
   "category.use_intensity": "category.management",
   "category.biodiversity_hotspot": "category.habitat",
   "category.wilderness": "category.habitat",
   "category.metric": "statistic.count",
   "category.metric_type": "statistic.count",
   "location.realm": "location.admin_area",
   ```

2. **Ajouter le bloc `predicts:` à `column_aliases.yaml`** :

   ```yaml
   category.habitat:
     predicts: [Predominant_land_use, Biome, Hotspot, Wilderness_area]
   category.management:
     predicts: [Use_intensity]
   statistic.count:
     predicts: [Diversity_metric, Measurement, Effort_corrected_measurement,
                Species_richness, N_samples]
   category.method:
     predicts: [Sampling_method, Diversity_metric_type,
                Diversity_metric_unit, Diversity_metric_is_effort_sensitive]
   identifier.record:
     predicts: [Source_ID, SS, SSB, SSBS, SSS, Study_number, Block]
   text.metadata:
     predicts: [Study_name]
   taxonomy.group:
     predicts: [Study_common_taxon, Higher_taxon, Best_guess_binomial,
                Parsed_name]
   taxonomy.rank:
     predicts: [Rank_of_study_common_taxon]
   location.admin_area:
     predicts: [UN_subregion, UN_region, Realm, Ecoregion]
   measurement.dimension:
     predicts: [Max_linear_extent_metres, Habitat_patch_area_square_metres,
                Km_to_nearest_edge_of_habitat, Ecoregion_distance_metres]
   measurement.growth:
     predicts: [Years_since_fragmentation_or_conversion]
   ```

3. **Télécharger PREDICTS depuis NHM Data Portal.** Stocker dans
   `data/silver/predicts/`.

4. **Créer PREDICTS_LABELS** — sous-ensemble des 67 colonnes.

5. **Rebuild + évaluation.**

**Critère de succès :** Les nouvelles colonnes sont correctement classifiées
dans leurs concepts coarse ; ProductScore stable (± 2 points).

---

#### Phase 5 (déférée): ForestGEO + TRY

**Conditions de déclenchement** :
- ForestGEO : quand l'accès aux données est obtenu. Ajouter le bloc `ctfs:`
  avec `pom`, `hom`, `gx`, `gy`, `StemTag`, `DFstatus`, `CensusID`.
- TRY : quand un mécanisme de pivot long→wide est implémenté dans le pipeline,
  ou si l'on décide de labeliser les 7 colonnes TRY comme concepts génériques
  (`identifier.trait`, `measurement.trait`, `measurement.unit`).

## Acceptance Criteria

### Functional Requirements

- [ ] Les prérequis bloquants benchmark/labels/anonymous sont traités avant
      l'intégration d'un nouveau standard
- [ ] `column_aliases.yaml` contient 4 nouveaux blocs de langue
      (`sinp`, `ets`, `predicts`, `splot`)
- [ ] `concept_taxonomy.py` contient les nouveaux fine→coarse merges
- [ ] Le gold set inclut au minimum 1 dataset par standard
- [ ] `evaluate.py` route les prefixes `sinp_`, `ets_`, `predicts_`, `splot_`
      vers le bucket `standards_based`
- [ ] Chaque phase produit un snapshot d'évaluation daté

### Non-Functional Requirements

- [ ] FR holdout ≥ 75% (actuellement 67.5%)
- [ ] ProductScore ne régresse pas de plus de 2 points par phase
- [ ] Aucune régression sur `tropical_field` ou `gbif_core_standard`
- [ ] Le temps de build du gold set reste < 2 minutes
- [ ] `forest_inventory` est suivi comme stress test secondaire, sans devenir
      la cible d'optimisation principale

### Quality Gates

- [ ] Analyse de collision aliases SINP vs FR existants effectuée
- [ ] Chaque nouveau dataset a ses LABELS revus manuellement
- [ ] `uvx ruff check src/` et `uvx ruff format src/` passent sans erreur
- [ ] Tests existants passent : `uv run pytest`

## Alternative Approaches Considered

### A. Tous les standards dans un seul bloc `standard:`

**Rejeté.** Les collisions inter-standards seraient impossibles à déboguer.
Le tag de langue dédié (`sinp:`, `ets:`, etc.) permet de tracer la provenance
et de désactiver un standard individuellement.

### B. Nouveaux concepts standalone (non mergés)

**Rejeté.** Avec < 5 exemples par concept, le modèle ne converge pas. Le
pattern existant de merge (111 → 45) a prouvé son efficacité. Les nouveaux
concepts sont des fine-grained qui enrichissent les coarse existants.

### C. Intégration de TRY en Phase 2 (format long-table)

**Rejeté.** Le pipeline assume un format wide-table (1 concept par colonne).
Pivoter TRY créerait des datasets « synthétiques-looking » qui risqueraient
de biaiser le value model. Mieux vaut intégrer les aliases TRY via le bloc
`ets:` (vocabulaire partagé) et déférer l'ingestion de données.

### D. Pondérer les standards dans ProductScore immédiatement

**Rejeté.** Redistribuer les poids avant d'avoir validé la qualité des
données serait prématuré. Les standards commencent en bucket diagnostique.

## Risk Analysis & Mitigation

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| Collisions aliases SINP/IFN FR | Moyen | Moyenne | Script de collision avant intégration |
| Régression tropical_field par dilution | Haut | Faible | Intégration séquentielle + snapshot |
| Benchmark encore fuité pendant acquisition | Haut | Moyenne | Prétraiter benchmark/labels/anonymous avant nouvelle phase |
| Données OpenObs non exploitables (format inattendu) | Moyen | Faible | Inspecter un sample avant labelling |
| Nouveaux concepts sous-représentés | Moyen | Haute | Merge dans coarse → pas de standalone |
| TRY long-table contamine le pipeline | Haut | Moyenne | TRY déféré à Phase 5 |
| Licence restrictive sur PREDICTS/sPlotOpen | Moyen | Faible | Vérifier licence avant download |

## Dependencies & Prerequisites

### Séquencement

```
Phase 1 (SINP)  ──→  Phase 2 (ETS)  ──→  Phase 3 (sPlotOpen)  ──→  Phase 4 (PREDICTS)
     │                     │                      │                        │
     ▼                     ▼                      ▼                        ▼
  Snapshot 1           Snapshot 2             Snapshot 3               Snapshot 4
  FR holdout           trait coverage         cover/plot               land-use
```

**Aucune dépendance inter-phases** pour les aliases (chaque bloc est
indépendant). Les phases peuvent être parallélisées si l'intégration
séquentielle est jugée trop lente — mais au prix de la traçabilité des
régressions.

### Prérequis techniques

- Benchmark d'acceptation gelé et séparé du train
- Alignement des labels train/eval sur les datasets qui se recouvrent
- Holdout anonymous reconstruit sans duplication train/test
- Gold set baseline snapshot (à prendre AVANT Phase 1)
- Accès OpenObs si la plateforme revient en ligne
- Accès iDiv pour sPlotOpen (inscription — gratuit)
- Accès NHM Data Portal pour PREDICTS (libre)
- TAXREF v18 téléchargeable librement sur inpn.mnhn.fr

## Appendix A: Cartographie complète SINP → Concepts Niamoto

| Champ SINP | Variantes rencontrées | Concept Niamoto (coarse) |
|---|---|---|
| `idSINPOccTax` | `id_sinp`, `unique_id_sinp` | `identifier.record` |
| `cdNom` | `cd_nom`, `CD_NOM` | `identifier.taxon` |
| `cdRef` | `cd_ref`, `CD_REF` | `identifier.taxon` |
| `nomCite` | `nom_cite`, `nom_scientifique` | `taxonomy.species` |
| `nomValide` | `nom_valide`, `NOM_VALIDE` | `taxonomy.species` |
| `nomVern` | `nom_vern`, `NOM_VERN` | `taxonomy.name` |
| `lbNom` | `lb_nom`, `LB_NOM` | `taxonomy.species` |
| `lbAuteur` | `lb_auteur`, `LB_AUTEUR` | `text.authority` → `text.metadata` |
| `dateDebut` | `date_debut`, `date_min` | `event.date` |
| `dateFin` | `date_fin`, `date_max` | `event.date` |
| `altitudeMin` | `altitude_min` | `location.elevation` |
| `altitudeMax` | `altitude_max` | `location.elevation` |
| `profondeurMin` | `depth_min`, `profondeur_min` | `location.depth` → `measurement.terrain` |
| `denombrementMin` | `count_min`, `denombrement_min` | `statistic.count` |
| `denombrementMax` | `count_max`, `denombrement_max` | `statistic.count` |
| `observateur` | `observers` | `text.observer` → `text.metadata` |
| `determinateur` | `determiner` | `text.observer` → `text.metadata` |
| `occSexe` | `occ_sexe` | `category.ecology` |
| `occStadeDeVie` | `occ_stade_de_vie` | `category.ecology` |
| `occNaturalite` | `occ_naturalite` | `category.ecology` |
| `occStatutBiologique` | `occ_statut_biologique` | `category.ecology` |
| `codeCommune` | `code_commune` | `location.admin_area` |
| `nomCommune` | `nom_commune` | `location.locality` |
| `codeDepartement` | `code_departement` | `location.admin_area` |
| `codeHabitat` | `code_habitat`, `cdHab` | `category.habitat` |
| `statutObservation` | `statut_observation` | `category.method` |
| `statutSource` | `statut_source` | `category.method` |
| `techniqueEchantillonnage` | `technique_echantillonnage` | `category.method` |
| `effortEchantillonnage` | `effort_echantillonnage` | `measurement.effort` → `measurement.dimension` |
| `sensiNiveau` | `sensi_niveau` | `text.metadata` |
| `commentaire` | `comment_context` | `text.metadata` |

## Appendix B: Standards identifiés mais non retenus

| Standard | Raison du rejet |
|----------|----------------|
| ABCD (TDWG) | 80% de recouvrement avec DwC, données XML, pas de CSV |
| Humboldt Extension | Trop récent (2024), quasi pas de datasets réels |
| Audiovisual Core | Métadonnées média, pas des données écologiques |
| Plinian Core | Fiches espèces, pas tabulaire |
| FLUXNET | Codes de capteurs très spécialisés, éloigné du cœur produit |
| WoSIS | Pédologie pure, éloigné du cœur produit tropical/biodiversité |
| EBV (GEO BON) | Format netCDF, pas tabulaire |
| VegX | XML natif, peu de données publiques |
| HISPID | Herbiers australiens, quasi tout déjà dans DwC |
| BioTIME | Tous les champs déjà couverts par les aliases existants |
| Living Planet Index | Tous les champs déjà couverts |

## Appendix C: Résumé des sources de téléchargement

| Standard | URL | Format | Inscription |
|----------|-----|--------|-------------|
| OpenObs (SINP) | https://openobs.mnhn.fr/ | CSV SINP v2 | Gratuit (compte INPN, indisponible temporairement) |
| TAXREF v18 | https://inpn.mnhn.fr/telechargement/referentielEspece/referentielTaxo | CSV/ZIP | Libre |
| ETS exemples | https://github.com/EcologicalTraitData/ETS | CSV | Libre |
| sPlotOpen | https://idata.idiv.de/ddm/Data/ShowData/3474 | CSV | Libre (inscription iDiv) |
| PREDICTS | https://data.nhm.ac.uk/dataset/the-2016-release-of-the-predicts-database | CSV | Libre |
| ForestGEO (Phase 5) | https://forestgeo.github.io/fgeo.data/ | R package | Libre |
| TRY (Phase 5) | https://www.try-db.org/ | TSV | Inscription + demande |

## References

### Internal
- `docs/03-ml-detection/archive/acquisition-history-and-source-strategy.md` — archived acquisition history and source strategy
- `docs/03-ml-detection/current-training-sources.md` — current source inventory actually wired into the code
- `docs/03-ml-detection/overview.md` — architecture ML
- `scripts/ml/concept_taxonomy.py` — taxonomie des concepts
- `scripts/ml/build_gold_set.py` — constructeur du gold set (SOURCES list)
- `scripts/ml/evaluate.py` — évaluation avec ProductScore et buckets
- `src/niamoto/core/imports/ml/column_aliases.yaml` — registre d'aliases
- `src/niamoto/core/imports/ml/alias_registry.py` — moteur d'aliases

### External
- [SINP OccTax v2.0 — Standard complet (HAL)](https://mnhn.hal.science/mnhn-04271727/file/OccTax_v2_COMPLET.pdf)
- [Standards SINP — Occurrences de taxon v2.0](https://standards-sinp.mnhn.fr/occurrences-de-taxon-v2-0/)
- [ETS — Ecological Trait-data Standard](https://ecologicaltraitdata.github.io/ETS/)
- [ETS GitHub](https://github.com/EcologicalTraitData/ETS)
- [sPlotOpen — iDiv data portal](https://idata.idiv.de/ddm/Data/ShowData/3474)
- [PREDICTS — NHM Data Portal](https://data.nhm.ac.uk/dataset/the-2016-release-of-the-predicts-database)
- [TRY Plant Trait Database](https://www.try-db.org/)
- [TAXREF v18](https://inpn.mnhn.fr/telechargement/referentielEspece/referentielTaxo)
- [OpenObs — MNHN](https://openobs.mnhn.fr/)
- [GeoNature — GitHub](https://github.com/PnX-SI/GeoNature)
- [Darwin Core Quick Reference](https://dwc.tdwg.org/terms/)
