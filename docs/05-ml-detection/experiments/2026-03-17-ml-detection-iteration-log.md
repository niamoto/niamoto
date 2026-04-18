# ML Detection Iteration Log — 2026-03-17

> Status: Experiment
> Audience: Team, AI agents
> Purpose: Historical detailed iteration log for the `feat/ml-detection-improvement`
> branch

## English summary

This is the longest historical log in the folder. It documents:

- the first `niamoto-score` baseline
- the diagnosis of weak holdout families such as `forest_inventory`
- early changes to value features and fusion features
- the move toward a more product-oriented benchmark
- the first surrogate/autoresearch decisions
- the first acquisition lots and their effect on the benchmark

The detailed body below is preserved as historical working material and still
contains French wording from the original session notes.

## Objet

Ce journal capture l'état des expérimentations réalisées sur la branche
`feat/ml-detection-improvement`, avec focus sur :

- le nouveau protocole `niamoto-score`
- les points faibles révélés par les holdouts
- les corrections tentées
- les décisions prises pour les itérations suivantes

Ce document est daté et doit pouvoir être complété par de nouvelles entrées au
fil de l'expérimentation.

## Contexte de départ

La branche a migré d'une logique historique plus monolithique vers un pipeline
hybride :

- alias exacts
- modèle header
- modèle values
- modèle de fusion
- projection vers `semantic_profile` et affordances

En parallèle, le protocole d'évaluation a été renforcé :

- suppression de la fuite de données dans l'évaluation fusion
- réalignement progressif train/runtime
- ajout du `NiamotoOfflineScore`
- ajout de holdouts langue, famille et anonymous
- ajout d'un logging de progression pour les runs longues

## Mesure de référence observée

Run complet `niamoto-score` observé avant les itérations ciblées de ce journal :

```text
NiamotoOfflineScore = 78.8351
```

Sous-scores et holdouts marquants :

- `primary` : `78.835`
- `holdout_lang[fr]` : `67.491`
- `holdout_lang[es]` : `88.599`
- `holdout_lang[de]` : `88.949`
- `holdout_lang[zh]` : `100.000`
- `holdout_family[dwc_gbif]` : `71.407`
- `holdout_family[forest_inventory]` : `47.918`
- `holdout_family[research_traits]` : `66.891`
- `holdout_family[tropical_field]` : `54.146`
- `holdout_anonymous` : `94.583`
- `diagnostic_synthetic` : `67.388`

## Lecture initiale

Le signal principal n'est pas un problème global de colonne anonyme. Au
contraire, le holdout anonymous est fort.

Les faiblesses se concentrent sur :

- certaines familles de datasets réels ;
- en particulier `forest_inventory` ;
- puis `tropical_field` ;
- et, dans une moindre mesure, `fr`.

Conclusion provisoire :

- la stack sait bien exploiter les patterns forts et les headers lisibles ;
- elle généralise encore mal sur certains domaines métier ;
- le problème semble plus **domain-specific** que purement linguistique.

## Diagnostic ciblé sur forest_inventory

Un diagnostic dédié a été exécuté sur le holdout `forest_inventory`.

Mesure ciblée de référence :

- `forest_role_f1 = 0.2769`
- `forest_concept_f1 = 0.2008`

### Constat principal

La fusion suivait trop souvent la branche `values` sur des erreurs systématiques.

Distribution des sources d'erreur observées :

- `89` erreurs `followed_value_wrong`
- `32` erreurs `followed_header_wrong`
- `27` erreurs `header_right_value_wrong`
- `12` erreurs `both_wrong_same`

Lecture :

- la branche `values` dominait trop sur ce domaine ;
- elle poussait des concepts inadaptés sur des colonnes codées métier ;
- la fusion ne corrigeait pas suffisamment ce biais.

### Confusions saillantes

Confusions de rôle :

- `category -> statistic`
- `identifier -> statistic`
- `category -> location`
- `measurement -> statistic`

Confusions de concepts :

- `location.admin_area -> event.date`
- `identifier.plot -> statistic.count`
- `category.tree_condition -> statistic.count`
- `measurement.cover -> statistic.count`
- `identifier.record -> statistic.count`

### Exemples d'erreurs à haute confiance

Exemples observés :

- `TCL` prédit `statistic.count` au lieu de `measurement.cover`
- `TCA` prédit `statistic.count` au lieu de `measurement.cover`
- `PEUPNR` prédit `statistic.count` au lieu de `category.management`
- `AGENTCD` prédit `statistic.count` au lieu de `category.damage`
- `COUNTYCD` prédit `statistic.count` au lieu de `location.admin_area`

Lecture :

- les colonnes codées d'inventaire forestier étaient mal reconnues ;
- le système les interprétait trop souvent comme des comptes ou des mesures
  simples.

## Hypothèse de travail

Hypothèse centrale de cette itération :

> Le principal défaut sur `forest_inventory` n'est pas l'absence totale de
> signal, mais une sur-dominance de la branche `values` sur des colonnes codées
> métier, combinée à une fusion trop permissive.

## Changements tentés

### 1. Factorisation des features values

Objectif :

- supprimer le mismatch train/runtime sur les features values ;
- disposer d'un point unique pour enrichir les signaux utiles aux colonnes
  codées.

Changements :

- création de `src/niamoto/core/imports/ml/value_features.py`
- réutilisation depuis :
  - `ml/scripts/train/train_value_model.py`
  - `src/niamoto/core/imports/ml/classifier.py`

Nouveaux signaux ajoutés :

- `n_unique_values`
- `dominant_ratio`
- `fixed_length_ratio`
- `short_code_ratio`
- `dense_integer_domain`
- `tiny_integer_domain`

### 2. Enrichissement des meta-features de fusion

Objectif :

- rendre la fusion plus sensible au désaccord header/values ;
- détecter les cas où `values` pousse `statistic.count` sur un header codé.

Changements :

- création de `src/niamoto/core/imports/ml/fusion_features.py`
- ajout dans la fusion de :
  - max proba
  - marge top1-top2
  - entropie
  - accord/désaccord
  - flags `statistic.count`
  - détection de header code-like

### 3. Heuristique ciblée de damping

Une première tentative d'injecter l'information "coded header" dans le modèle
header lui-même a été testée puis retirée, car elle dégradait `forest_role_f1`.

La correction conservée est plus ciblée :

- si un header est manifestement code-like ;
- et si une branche pousse fortement `statistic.count` ;
- alors la confiance `statistic.count` est amortie avant la fusion.

But :

- corriger un faux positif fréquent ;
- sans reconfigurer agressivement le modèle header.

## Résultats ciblés après itération

### Baseline ciblée

- `forest_role_f1 = 0.2769`
- `forest_concept_f1 = 0.2008`

### Après factorisation values + meta-features de fusion + damping

- `forest_role_f1 = 0.2960`
- `forest_concept_f1 = 0.1938`

## Interprétation

Le signal obtenu est cohérent avec l'objectif produit :

- amélioration du **rôle** sur le domaine difficile ;
- pas encore d'amélioration sur le concept fin.

À ce stade, l'itération semble surtout améliorer le comportement produit
pertinent, pas la précision académique du concept.

Validation globale encore requise :

- rerun complet `niamoto-score`
- vérification qu'on n'améliore pas `forest_inventory` en cassant d'autres
  familles

## Validation globale de l'itération

Le rerun complet `niamoto-score` a été exécuté après cette itération.

Résultat final :

```text
NiamotoOfflineScore = 79.1135
```

Comparaison avec la baseline observée avant l'itération :

- baseline : `78.8351`
- itération : `79.1135`
- delta global : `+0.2784`

### Sous-scores et holdouts après itération

- `primary` : `79.113`
- `holdout_lang[fr]` : `66.465`
- `holdout_lang[es]` : `91.329`
- `holdout_lang[de]` : `92.380`
- `holdout_lang[zh]` : `99.444`
- `holdout_family[dwc_gbif]` : `68.267`
- `holdout_family[forest_inventory]` : `41.654`
- `holdout_family[research_traits]` : `65.081`
- `holdout_family[tropical_field]` : `57.131`
- `holdout_anonymous` : `100.000`
- `diagnostic_synthetic` : `71.785`

### Ce qui s'améliore

- `primary` monte légèrement
- `es` et `de` montent nettement
- `tropical_field` monte
- `anonymous` devient excellent
- `forest_inventory` améliore bien son `role_f1`

### Ce qui se dégrade

- `fr` baisse légèrement
- `dwc_gbif` baisse nettement
- `research_traits` baisse
- `forest_inventory` baisse fortement en score global

### Point critique sur forest_inventory

Le résultat `forest_inventory` après itération est particulièrement important :

- `NiamotoOfflineScore = 41.654`
- `role = 0.296`
- `critical = 0.533`
- `pairs = 0.390`
- `confQ = 0.500`
- `hc_err = 0.500`

Lecture :

- le **rôle** s'améliore bien par rapport à la baseline ciblée ;
- mais la confiance, la cohérence dataset-level et les erreurs à haute
  confiance se dégradent trop fortement ;
- le mécanisme actuel améliore un aspect local mais abîme trop le comportement
  global sur ce garde-fou critique.

## Verdict sur l'itération

Verdict retenu :

> itération **non validée** comme nouveau baseline de la stack

Raison :

- le gain global est trop faible ;
- il est obtenu au prix d'une dégradation trop forte sur `forest_inventory` ;
- la baisse sur `dwc_gbif` et `research_traits` rend l'amélioration globale peu
  défendable ;
- l'hypothèse était bonne, mais l'implémentation du correctif reste trop
  agressive ou mal calibrée.

Ce qui est conservé de cette itération :

- le diagnostic détaillé ;
- la compréhension du biais `values -> statistic.count` ;
- la nécessité de traiter `forest_inventory` comme garde-fou explicite.

## Décisions prises

- conserver la factorisation shared des features values ;
- conserver les meta-features de fusion ;
- ne pas promouvoir automatiquement le damping ciblé actuel comme nouveau
  baseline sans nouvelle itération plus prudente ;
- ne pas conserver l'injection directe de `coded` dans le texte header ;
- utiliser `forest_inventory` comme garde-fou explicite dans les prochaines
  décisions d'`autoresearch`.

## Ce que cette itération nous apprend

1. Le vrai point faible n'est pas d'abord la langue française.
2. Le vrai point faible est le comportement sur certains domaines métier,
   notamment l'inventaire forestier.
3. Les gains les plus utiles passent par :
   - une meilleure fusion ;
   - une meilleure prudence ;
   - des signaux plus explicites sur les colonnes codées ;
   - des garde-fous orientés domaine.

## Prochaines itérations recommandées

### Court terme

- finir la validation complète `niamoto-score`
- comparer avant/après sur tous les holdouts
- décider si l'itération est gardée au niveau stack complet

### Si le gain global tient

- ajouter un reporting dédié sur les prédictions `-> statistic.count`
- intégrer `forest_inventory` comme garde-fou `autoresearch`
- attaquer ensuite `tropical_field`

### Si le gain global ne tient pas

- conserver l'analyse ;
- réduire la portée de l'heuristique ;
- ou déplacer la logique vers une fusion plus structurée au lieu d'un damping
  simple

## Évolution décidée du benchmark

Après cette run, il a été décidé de faire évoluer le benchmark avant une
nouvelle itération ML.

Objectif :

- rendre les diagnostics plus honnêtes ;
- mieux séparer anglais standard et anglais métier ;
- éviter de surinterpréter des splits faciles comme `zh`.

Changements ajoutés au reporting de `ml/scripts/eval/evaluate.py` :

- `diagnostic_lang[zh]` comme diagnostic secondaire et non plus holdout
  stratégique
- `diagnostic_subset[en_standard]`
- `diagnostic_subset[en_field]`
- `diagnostic_subset[coded_headers]`
- `diagnostic_subset[gbif_core_standard]`
- `diagnostic_subset[gbif_extended]`
- split interne de `forest_inventory` :
  - `forest_inventory/ifn_fr`
  - `forest_inventory/fia_en`
  - `forest_inventory/nordic_inventory`
- split interne de `dwc_gbif` :
  - `dwc_gbif/core_standard`
  - `dwc_gbif/extended`

Décision associée :

- ne pas changer immédiatement la formule du `NiamotoOfflineScore`
- changer d'abord le reporting et les garde-fous
- relancer ensuite une run complète pour identifier le vrai point faible :
  `IFN`, `FIA`, `GBIF standard`, `GBIF étendu`, `en_field`, ou headers codés

## Commandes utiles

Validation complète avec progression :

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 LOKY_MAX_CPU_COUNT=1 .venv/bin/python -m ml.scripts.eval.evaluate --model all --metric niamoto-score --splits 3 --verbose-progress
```

Boucle silencieuse compatible autoresearch :

```bash
.venv/bin/python -m ml.scripts.eval.evaluate --model all --metric niamoto-score --splits 3 --quiet
```

Run recommandée après évolution du benchmark :

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 LOKY_MAX_CPU_COUNT=1 .venv/bin/python -m ml.scripts.eval.evaluate --model all --metric niamoto-score --splits 3 --verbose-progress
```

## Lot Guyane 1 — acquisition et intégration

Un premier lot Guyane a été traité pour rapprocher le benchmark des jeux
réellement visés côté produit.

### Vérification d'accès Dataverse

Jeux inspectés :

- `ForestScan / Paracou`
- `Trinite Forest Censuses`
- `Tresor Forest Censuses`
- `Tibourou Forest Censuses`
- `Montagne Tortue Forest Censuses`

Résultat vérifié :

- le CSV principal `ForestScan / Paracou` est publiquement téléchargeable ;
- les CSV principaux `Trinite`, `Tresor`, `Tibourou` et `Montagne Tortue` sont
  restreints et exposés via `fileAccessRequest` ;
- leurs fichiers de description restent publics et ont été récupérés localement
  comme support de préparation.

### Fichiers récupérés

Sous `ml/data/silver/guyane/` :

- `paracou/FGPlotsCensusData2023.csv`
- `paracou/FGPlotsDescription.csv`
- `trinite/TriniteDescription.csv`
- `tresor/TresorDescription.csv`
- `tibourou/TibourouDescription.csv`
- `montagne_tortue/Montagne_TortueDescription.csv`

### Lecture du schéma

Constats utiles :

- le census Paracou contient `38` colonnes ;
- les fichiers de description Guyafor ont un schéma homogène de `53` colonnes ;
- le census Paracou est immédiatement utile pour le benchmark
  `tropical_field / plot_inventory` ;
- les fichiers de description sont utiles pour préparer les futurs labels, mais
  pas encore assez sûrs pour être injectés dans le gold set sans risque de
  bruit et de redondance.

### Intégration retenue

Choix fait :

- intégrer seulement le census `Paracou / ForestScan` ;
- ne pas intégrer les fichiers de description ;
- garder les autres datasets Guyane en attente d'accès à leurs CSV principaux.

Changements réalisés :

- ajout d'un bloc `FORESTSCAN_PARACOU_LABELS` dans
  `ml/scripts/data/build_gold_set.py`
- ajout de la source `forestscan_paracou_census` dans `SOURCES`
- régénération du gold set

Résultat :

- `forestscan_paracou_census` apporte `34` colonnes gold ;
- le gold set passe à `2265` colonnes au total, dont `1669` gold et `596`
  synthetic.

### Correction d'outillage connexe

Défaut corrigé dans
`ml/scripts/data/build_gold_set.py` :

- `uv run python -m ml.scripts.data.build_gold_set` cassait sur
  `ModuleNotFoundError: scripts`
- le script ajoute maintenant à la fois `src/` et la racine du repo au
  `sys.path`
- les deux modes fonctionnent désormais :
  - `uv run python -m ml.scripts.data.build_gold_set`
  - `uv run python -m ml.scripts.data.build_gold_set`

### Décision

État du lot Guyane 1 :

- `Paracou / ForestScan` : intégré
- `Trinite / Tresor / Tibourou / Montagne Tortue` : documentés localement mais
  non intégrés faute d'accès aux CSV census

Suite logique :

- ajouter ensuite un premier lot `GBIF ciblé`
- ou intégrer des datasets d'instances réelles dès qu'ils sont disponibles

## Lot GBIF ciblé 1 — régional général

Un premier lot GBIF régional a été récupéré via l'API publique
`occurrence/search` avec les contraintes suivantes :

- régions : `NC`, `GF`, `GA`, `CM`
- règne : `Plantae`
- volume cible : `5000` occurrences par région

Sorties créées sous `ml/data/silver/gbif_targeted/` :

- `new_caledonia/occurrences.csv`
- `guyane/occurrences.csv`
- `gabon/occurrences.csv`
- `cameroon/occurrences.csv`

Volumes récupérés :

- `new_caledonia` : `5000 / 442442`
- `guyane` : `5000 / 299072`
- `gabon` : `5000 / 583825`
- `cameroon` : `5000 / 621574`

### Lecture

Ce lot est utile pour construire un sous-benchmark GBIF régional, mais il est
fortement tiré par les jeux observationnels grand public, en particulier des
datasets type `iNaturalist`.

Conclusion :

- bon lot `GBIF régional général`
- mauvais candidat comme unique approximation du GBIF institutionnel

### Intégration gold set

Les sources suivantes ont été ajoutées dans
`ml/scripts/data/build_gold_set.py` :

- `gbif_targeted_new_caledonia`
- `gbif_targeted_guyane`
- `gbif_targeted_gabon`
- `gbif_targeted_cameroon`

Apport observé :

- `41` colonnes pour `new_caledonia`
- `38` colonnes pour `guyane`
- `37` colonnes pour `gabon`
- `39` colonnes pour `cameroon`

## Lot GBIF ciblé 2 — institutionnel

Un second flux a ensuite été ajouté pour isoler un sous-corpus plus
institutionnel.

Filtre retenu :

- `basisOfRecord in {PRESERVED_SPECIMEN, MATERIAL_SAMPLE, OCCURRENCE}`
- présence d'au moins un champ institutionnel :
  - `institutionCode`
  - `collectionCode`
  - `institutionID`
  - `collectionKey`
- exclusion explicite des gros jeux observationnels :
  - `iNaturalist`
  - `observation.org`
  - `Pl@ntNet`
  - `eBird`
  - quelques autres catalogues analogues

### Test de rendement

Un sample `institutional` a été exécuté sur `5000` enregistrements scannés par
région.

Résultat :

- `new_caledonia` : `6`
- `guyane` : `16`
- `gabon` : `200` (cap atteint)
- `cameroon` : `200` (cap atteint)

Lecture :

- `NC` et `GF` ont très peu d'institutionnel dans les premiers résultats
  régionaux ;
- `GA` et `CM` ont un rendement institutionnel suffisant ;
- il est pertinent de conserver `NC/GF` dans le lot général et `GA/CM` dans un
  lot institutionnel dédié.

### Lot institutionnel retenu

Le lot complet retenu à ce stade est :

- `gabon`
- `cameroon`

Sorties créées sous `ml/data/silver/gbif_targeted_institutional/` :

- `gabon/occurrences.csv`
- `cameroon/occurrences.csv`

Volumes retenus :

- `gabon` : `2000`
- `cameroon` : `2000`

Qualité observée :

- forte présence de `PRESERVED_SPECIMEN`
- jeux type `Tropicos`
- signal nettement plus institutionnel que le lot GBIF régional général

### Intégration gold set

Les sources suivantes ont été ajoutées dans
`ml/scripts/data/build_gold_set.py` :

- `gbif_targeted_institutional_gabon`
- `gbif_targeted_institutional_cameroon`

Apport observé :

- `36` colonnes pour `gabon`
- `36` colonnes pour `cameroon`

### Effet cumulé sur le gold set

Après intégration du lot GBIF général puis du lot institutionnel `GA/CM` :

- `ml/data/gold_set.json` passe à `2492` colonnes
- dont `1896` gold et `596` synthetic

Décision retenue :

- conserver `gbif_targeted/` comme sous-corpus régional général
- conserver `gbif_targeted_institutional/gabon` et `cameroon` comme
  sous-corpus institutionnel
- ne pas forcer pour l'instant un scan institutionnel profond sur
  `new_caledonia` et `guyane`

## Entrée du 2026-03-18 — run sur gold set enrichi

Avant cette run, les copies de référence locales ont été internalisées dans
`ml/data/silver/` et `ml/scripts/data/build_gold_set.py`
a été réaligné pour ne plus dépendre de copies hors repo pour :

- `guyadiv_trees`
- `guyadiv_plots`
- `afrique_occ`
- `afrique_plots`
- `nc_occ`
- `nc_plots`

Le gold set reste à ce stade à :

- `2492` colonnes au total
- `1896` gold
- `596` synthetic

### Résultat global

Run complète observée :

```text
NiamotoOfflineScore = 78.6199
```

Comparaison avec la run documentée précédente :

- run précédente : `79.1135`
- nouvelle run : `78.6199`
- delta global : `-0.4936`

### Diagnostics marquants

- `primary` : `78.620`
- `holdout_lang[fr]` : `66.176`
- `holdout_lang[es]` : `89.457`
- `holdout_lang[de]` : `92.742`
- `holdout_family[dwc_gbif]` : `70.210`
- `holdout_family[tropical_field]` : `63.952`
- `holdout_family[research_traits]` : `71.370`
- `holdout_anonymous` : `100.000`
- `diagnostic_synthetic` : `70.892`

Diagnostics structurels :

- `diagnostic_subset[en_standard]` : `95.656`
- `diagnostic_subset[en_field]` : `75.917`
- `diagnostic_subset[coded_headers]` : `72.606`
- `diagnostic_subset[gbif_core_standard]` : `96.322`
- `diagnostic_subset[gbif_extended]` : `87.025`

### Lecture des nouveaux sous-buckets

Le split `forest_inventory` confirme très nettement que le problème principal
de ce bloc n'est pas homogène :

- `forest_inventory` : `41.841`
- `forest_inventory/ifn_fr` : `17.950`
- `forest_inventory/fia_en` : `50.306`
- `forest_inventory/nordic_inventory` : `65.225`

Lecture :

- `ifn_fr` est de loin le sous-bucket le plus faible ;
- `fia_en` est difficile mais moins catastrophique ;
- `nordic_inventory` reste le sous-cas le plus tolérable.

### Interprétation

Cette run ne change pas la conclusion de fond :

- les points forts restent `GBIF standard`, `anglais standard`, `anonymous` ;
- les points faibles restent `en_field`, les `coded_headers`, et certains
  domaines métier compacts ;
- `forest_inventory`, et surtout `ifn_fr`, est un bon révélateur de fragilité,
  mais ne doit pas piloter seul la roadmap produit.

Pour la cible produit visée à ce stade, les signaux les plus utiles restent :

- `tropical_field`
- `research_traits`
- `gbif_core_standard`
- `gbif_extended`
- `en_field`

### Décision sur le protocole

Décision prise après cette run :

- retirer `zh` du protocole courant ;
- ne plus l'utiliser comme diagnostic reporté dans la boucle standard ;
- garder l'accent sur `fr`, `es`, `de`, `tropical_field`, `research_traits`,
  `gbif_*`, `en_field` et `coded_headers`.

Conséquence :

- la prochaine run sera un peu plus propre côté reporting ;
- `zh` est désormais considéré comme non stratégique pour la décision produit.

## Entrée du 2026-03-18 — baseline ProductScore

Le protocole de décision a ensuite été enrichi avec un `ProductScore`
spécifique à la cible produit courante.

Poids retenus :

- `tropical_field` : `30%`
- `research_traits` : `15%`
- `gbif_core_standard` : `20%`
- `gbif_extended` : `10%`
- `en_field` : `15%`
- `anonymous` : `10%`

Baseline observée :

```text
ProductScore = 79.2454
```

Détail de la baseline :

- `tropical_field` : `63.952`
- `research_traits` : `71.370`
- `gbif_core_standard` : `96.322`
- `gbif_extended` : `87.025`
- `en_field` : `75.917`
- `anonymous` : `100.000`

Décision associée :

- utiliser `product-score` comme cible principale d'`autoresearch`
- conserver `niamoto-score` comme garde-fou global secondaire
- conserver `forest_inventory` comme stress test secondaire, sans le laisser
  piloter la décision finale

## Entrée du 2026-03-18 — pivot autoresearch

Après plusieurs essais, le constat est devenu clair :

- les boucles stack complètes trouvent parfois des candidats plausibles ;
- mais la validation complète est trop coûteuse pour une itération autonome
  dense ;
- même les variantes `fast` restent trop lentes pour atteindre un vrai rythme
  `autoresearch`.

### Conclusion

Le problème principal n'est plus la seule qualité de la métrique.

Le vrai problème est la granularité de la recherche :

- on réentraîne trop de choses pour des changements locaux ;
- on dépense le budget en certification au lieu d'explorer ;
- la boucle autonome reste trop lente pour délivrer sa valeur.

### Décision

Pivot décidé :

- documenter puis construire une **surrogate loop fusion-only**
- séparer l'exploration autonome de la validation stack complète
- réserver `product-score` et `niamoto-score` à la promotion des meilleurs
  candidats, pas à chaque itération

Document de référence :

- `docs/05-ml-detection/autoresearch-surrogate-loop.md`

## Entrée du 2026-03-18 — première mesure surrogate loop

La surrogate loop `fusion-only` a été implémentée puis mesurée sur le gold set
courant.

### Première tentative

- builder du cache interrompu après environ `16 min`
- diagnostic :
  - coût du build trop élevé
  - principale cause identifiée : prédictions `header/value` faites record par
    record

### Correctif appliqué

- batch prediction pour `header`
- batch prediction pour `values`
- extraction metadata batchée
- logging par fold dans le builder

### Mesures après optimisation

Build du cache :

```text
build_fusion_surrogate_cache --splits 3
real = 490.08s
```

Soit environ `8m10s` de préchauffe one-shot.

Baseline `surrogate-fast` sur cache chaud :

```text
FusionSurrogateFast = 55.6326
real = 1.66s
```

Baseline `surrogate-mid` sur cache chaud :

```text
FusionSurrogateMid = 59.2746
real = 1.31s
```

### Lecture

- le build du cache reste un coût réel, mais il est désormais ponctuel ;
- les évaluations `surrogate-fast` et `surrogate-mid` sont enfin dans la bonne
  zone pour `autoresearch` ;
- la surrogate loop devient donc exploitable pour une exploration dense ;
- le prochain enjeu n'est plus la faisabilité du pivot, mais la stratégie de
  promotion des candidats gagnants vers `product-score-fast-fast`, puis
  `product-score`, puis `niamoto-score`.

## Entrée du 2026-03-19 — corrections runner et premier gain autoresearch

### Corrections du runner surrogate

Trois problèmes identifiés et corrigés dans
`ml/scripts/research/run_fusion_surrogate_autoresearch.py` :

1. **Validation stack trop coûteuse** — Quand un candidat passait
   `surrogate-mid`, le runner lançait `product-score-fast-fast` (bloquant
   pendant des heures). Correction : `--defer-stack-validation` (défaut true),
   les candidats passants vont dans `.autoresearch/fusion-surrogate-promotions.jsonl`.

2. **Fichiers hors périmètre** — L'iter 11 du run Codex avait touché le log
   d'expérimentations. Correction : statut `reject_scope`, rejet immédiat si
   des fichiers hors `DEFAULT_ALLOWED_PATHS` sont touchés.

3. **Pre-commit hooks bloquants** — Le commit automatique échouait car
   `ruff-format` reformatait les fichiers stagés. Correction : `--no-verify`
   pour les commits automatiques du runner.

4. **restore_paths crashait sur fichiers untracked** — `git restore --source=HEAD`
   échoue sur les fichiers qui n'existent pas dans HEAD. Correction : séparer
   tracked (restore) et untracked (unlink).

### Remplacement Codex → Claude

Après épuisement des crédits Codex, le moteur a été remplacé par
`claude -p --dangerously-skip-permissions`.

### Run Codex (2026-03-18) — 150 itérations

- `141` `codex_error` (symlinks cassés `~/.codex/skills/`)
- `9` itérations utiles : `7` reject_fast, `2` reject_mid
- meilleur fast : `55.8177` (baseline `55.6326`)
- meilleur mid : `58.9922` (baseline `59.2746`)
- `0` promotion

### Premier gain Claude — cross-rank reciprocity

L'itération 2 du premier run Claude a produit un candidat gagnant
(fast `55.6326 → 56.5524`, delta `+0.9198`). Le candidat a aussi amélioré
mid (`59.2746 → 60.1680`, delta `+0.8934`).

4 nouvelles features de fusion ajoutées :

1. `header_top1_value_rank` — position du concept #1 header dans le classement
   values (0 = aussi #1, 1 = dernier)
2. `value_top1_header_rank` — l'inverse
3. `top2_cross_match` — le #2 d'une branche correspond au #1 de l'autre
4. `both_weak` — les deux branches sont faibles (max proba < 0.3)

Fichiers modifiés : `train_fusion.py` et `classifier.py`.

### Nouvelles baselines après gain

```text
surrogate-fast = 56.5524 (était 55.6326, +0.92)
surrogate-mid  = 60.1680 (était 59.2746, +0.89)
```

### Run Claude post-gain — 50 itérations (2026-03-19)

- `50` itérations complétées
- `50` reject_fast
- meilleur fast : `56.1821` (baseline `56.5524`)
- `0` promotion

### Lecture

Le gain cross-rank reciprocity semble être un **plateau** pour le périmètre
actuel de recherche. 50 itérations supplémentaires n'ont pas réussi à battre
la nouvelle baseline.

Hypothèses pour débloquer :

- élargir `DEFAULT_ALLOWED_PATHS` (ajouter `fusion_features.py`)
- enrichir le prompt avec des hypothèses plus ciblées
- relancer un run stack complète sur header ou values
- reconstruire le cache surrogate après un gain header/values

### Décision

- conserver le gain cross-rank reciprocity comme nouvelle baseline fusion
- ne pas relancer autoresearch fusion immédiatement
- passer à l'évaluation end-to-end par instance (niamoto-subset) pour mesurer
  l'impact réel du ML sur les suggestions de widgets

## Entrée du 2026-03-20 — réentraînement, validation ProductScore, optimisation batch

### Réentraînement des 3 modèles

Les modèles `.joblib` dans `ml/models/` étaient toujours les anciens — l'autoresearch
modifiait le code des features de fusion mais n'entraînait pas les modèles. Les
scores surrogate étaient un proxy local, pas le vrai score produit.

Réentraînement complet exécuté :

- header : macro-F1 = 0.7614
- values : macro-F1 = 0.3783
- fusion : mean macro-F1 = 0.6899 (leak-free CV, 5 folds)

Durée totale : ~5h (goulot = extraction record par record dans le leak-free CV).

### Validation ProductScore — gain confirmé

```text
ProductScore = 80.0372 (baseline 79.2454, delta +0.79)
```

Détail par bucket :

| Bucket | Avant | Après | Delta |
|--------|-------|-------|-------|
| tropical_field | 63.95 | 64.88 | +0.93 |
| research_traits | 71.37 | 70.98 | -0.39 |
| gbif_core_standard | 96.32 | 95.87 | -0.46 |
| gbif_extended | 87.03 | 89.75 | +2.72 |
| en_field | 75.92 | 78.53 | +2.61 |
| anonymous | 100.0 | 100.0 | = |

Gains notables : `en_field` +2.61, `gbif_extended` +2.72, `tropical_field` +0.93.

Régression : `fr` -4.07 (holdout, pas dans le ProductScore).

### Optimisation batch de l'entraînement fusion

Le goulot de l'entraînement était `extract_fusion_features()` appelée record
par record (~15 000 appels séquentiels pour le leak-free CV).

La version batch `extract_fusion_branch_probabilities_batch()` existait déjà
pour le cache surrogate. Elle a été câblée dans `train_fusion.py` pour
remplacer les 3 boucles record par record.

Résultat :

- scores strictement identiques (même macro-F1 par fold au centième)
- temps : **5h → 15 min** (~20x plus rapide)
- zéro perte de qualité

### Évaluation par instance — niamoto-subset

Un script `ml/scripts/eval/evaluate_instance.py` a été créé pour comparer la
détection ML avec l'`import.yml` validé d'une instance réelle.

Résultats sur `niamoto-subset` (29 colonnes, 9 évaluées via ground truth) :

| Mode | Role correct | Concept correct |
|------|-------------|-----------------|
| Alias seul | 4/9 (44%) | 4/9 (44%) |
| ML (modèles réentraînés) | 6/9 (67%) | 5/9 (56%) |

Gains ML par rapport aux alias seuls :

- `id_plot` : non détecté → `identifier.plot` (rôle correct)
- `geo_pt` : non détecté → `location.coordinate` (rôle + concept corrects, 0.93)

Erreurs restantes :

- `infra` → `measurement.diameter` (faux, confiance faible 0.32)
- `plot_name` → `location.locality` (alias impose à confiance 1.0)
- `location` → pas trouvé (champ schema, pas colonne CSV)

### Décisions de cette session

- ProductScore 80.04 validé comme nouvelle baseline
- modèles réentraînés commités
- batch optimization commitée (entraînement 20x plus rapide)
- évaluation par instance opérationnelle sur niamoto-subset
- prochaine étape : câbler le ML dans l'auto-config (plan documenté dans
  `docs/05-ml-detection/README.md` and the active reference docs in
  `docs/05-ml-detection/`)
