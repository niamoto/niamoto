# Acquisition wave retrain and evaluation (2026-03-21)

## Objet

Mesurer l'impact réel de la vague d'acquisition `SINP 1A + ETS + sPlotOpen`
sur les modèles ML de détection sémantique, après reconstruction complète du
gold set puis réentraînement des trois branches (`header`, `values`,
`fusion`).

## Données intégrées avant retrain

### Intégrées au gold set

- `TAXREF v18` (`ml/data/silver/taxref/TAXREFv18.txt`)
- `ETS Occurrence_ext.csv`
- `ETS Taxon_ext.csv`
- `ETS Measurement_or_Fact_ext.csv`
- `sPlotOpen_header(3).txt`
- `sPlotOpen_DT(2).txt`
- `sPlotOpen_CWM_CWV(2).txt`
- `sPlotOpen_metadata(2).txt`

### Intégrées runtime uniquement

- bloc `sinp:` dans `column_aliases.yaml`
- bloc `ets:` dans `column_aliases.yaml`
- bloc `splot:` dans `column_aliases.yaml`

### Explicitement laissées de côté

- `OpenObs / SINP` : source indisponible côté MNHN
- `species_trait_data.csv` : trop spécialisé / sémantique fragile
- `PREDICTS` : conservé hors chemin critique

## Gold set obtenu

| Métrique | Valeur |
|----------|:------:|
| Colonnes labellisées | **2540** |
| Concepts coarse | **61** |
| Sources ajoutées dans cette vague | `taxref_v18`, `ets_*`, `splot_*` |

Apports visibles par source :

| Source | Colonnes |
|--------|:--------:|
| `taxref_v18` | 17 |
| `ets_occurrence_ext` | 9 |
| `ets_taxon_ext` | 17 |
| `ets_measurement_ext` | 4 |
| `splot_header` | 33 |
| `splot_dt` | 6 |
| `splot_cwm` | 40 |
| `splot_metadata` | 15 |

## Commandes exécutées

```bash
uv run python -m ml.scripts.data.build_gold_set
uv run python -m ml.scripts.train.train_header_model
uv run python -m ml.scripts.train.train_value_model
uv run python -m ml.scripts.train.train_fusion
uv run python -m ml.scripts.eval.run_eval_suite
```

## Résultats de training

| Modèle | Macro-F1 cross-val | Note |
|--------|:------------------:|------|
| Header | **0.753** | branche la plus robuste |
| Values | **0.378** | signal utile mais faible généralisation |
| Fusion | **0.639** | meilleure que `values`, inférieure à `header` seul |

### Avertissements

Le réentraînement `header` et `fusion` déclenche plusieurs
`ConvergenceWarning` (`max_iter` atteint avec solveur `sag`). Le fit est
terminé et les modèles sont sauvegardés, mais un réglage ultérieur de
`max_iter` ou du solveur reste souhaitable.

## Résultats d'évaluation

Fichier de sortie :
`ml/data/eval/results/20260321_194036.json`

### Benchmarks historiques recalculés après retrain

En complément de l'`eval suite`, les métriques historiques du protocole de
holdouts ont été relancées sur les modèles retrainés :

| Benchmark | Valeur |
|-----------|:------:|
| **ProductScore** | **80.8392** |
| **GlobalScore / NiamotoOfflineScore** | **82.764** |

Détail `ProductScore` :

| Bucket | Score |
|--------|:-----:|
| `gbif_core_standard` | 98.511 |
| `gbif_extended` | 91.018 |
| `en_field` | 82.672 |
| `tropical_field` | 75.093 |
| `research_traits` | 71.621 |
| `anonymous` | 63.634 |

Lecture :

- les métriques historiques restent globalement solides
- elles sont cohérentes avec l'`eval suite`
- le bucket le plus pénalisant est désormais clairement `anonymous`
- les headers codés / inventaires restent le principal plafond de
  généralisation du protocole holdout

### Suite complète (9 datasets, 478 colonnes)

| Dataset | Cols | Role % | Concept % |
|---------|:----:|:------:|:---------:|
| `niamoto-nc` | 57 | 96.5 | **91.2** |
| `niamoto-gb` | 27 | 100.0 | **100.0** |
| `guyadiv` | 61 | 83.6 | **83.6** |
| `gbif-nc` | 51 | 94.1 | **90.2** |
| `gbif-gabon` | 45 | 91.1 | **88.9** |
| `gbif-inst-gabon` | 41 | 90.2 | **87.8** |
| `silver` | 136 | 89.0 | **77.2** |
| `acceptance-niamoto-gb` | 27 | 100.0 | **100.0** |
| `acceptance-fia-or` | 33 | 75.8 | **63.6** |
| **TOTAL** | **478** | **90.4** | **84.7** |

### Vue "datasets produit + proches produit" (7 datasets, 418 colonnes)

| Agrégat | Role % | Concept % |
|---------|:------:|:---------:|
| Tier 1 + Tier 1b + Silver | **90.9** | **85.4** |

## Lecture

### Ce qui a bien marché

- `niamoto-gb` reste à **100%**
- `niamoto-nc` monte à **91.2%**
- `guyadiv` monte à **83.6%**
- les trois jeux GBIF proches produit sont tous entre **87.8%** et **90.2%**

La vague d'acquisition a donc bien renforcé le coeur produit et les cas
standardisés proches du produit.

### Ce qui reste faible

Le benchmark gelé hors-train reste polarisé par `acceptance-fia-or` :

| Dataset | Concept % |
|---------|:---------:|
| `acceptance-niamoto-gb` | 100.0 |
| `acceptance-fia-or` | **63.6** |

Les principales erreurs restantes :

- `measurement.biomass -> measurement.volume`
- `identifier.taxon -> taxonomy.species`
- `category.habitat -> (not found)`
- `SPCD`, `CR`, `VOLCFNET`, `VOLBFNET` toujours ratés en FIA
- `acceptedTaxonKey`, `speciesKey`, `genericName`,
  `infraspecificEpithet`, `scientificNameAuthorship` toujours ratés sur les
  exports GBIF

## Conclusion

Cette vague d'acquisition est rentable.

- Oui, elle améliore concrètement les datasets coeur Niamoto
- Oui, elle stabilise les cas GBIF réels
- Non, elle ne résout pas encore la généralisation sur inventaires codés

La suite logique n'est pas d'ouvrir un nouveau chantier d'acquisition
immédiatement, mais de faire une passe de correction ciblée sur :

1. les clés taxonomiques GBIF encore systématiquement ratées
2. les colonnes FIA codées (`SPCD`, `CR`, `VOLCFNET`, `VOLBFNET`)
3. `measurement.biomass`, `identifier.taxon`, `category.habitat`,
   `text.metadata`
