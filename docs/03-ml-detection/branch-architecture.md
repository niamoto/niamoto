# Architecture de la Branche ML Detection

## Objet

Ce document décrit ce que la branche `feat/ml-detection-improvement` cherche à
obtenir, l'architecture adoptée, et la manière dont `autoresearch` doit être
utilisé dans Niamoto.

Le sujet n'est plus seulement "détecter un type de colonne". Le but est de
produire une détection suffisamment bonne pour auto-configurer un import,
construire un `semantic_profile`, et proposer des affordances et suggestions
utiles sans dépendre d'un LLM.

## Objectif produit

L'objectif produit n'est pas la perfection académique sur le concept fin. Le
système doit surtout :

- reconnaître le bon **rôle** d'une colonne ;
- reconnaître quelques **concepts critiques** qui changent le comportement
  produit ;
- bien se comporter sur des datasets nouveaux, multilingues et partiellement
  anonymes ;
- éviter les faux positifs à haute confiance ;
- alimenter un `semantic_profile` exploitable pour les suggestions
  transformer/widget.

En pratique, une confusion `measurement.height` vs `measurement.diameter` est
moins grave qu'une confusion `identifier.plot` vs `statistic.count`.

## Architecture adoptée

La branche a convergé vers un pipeline hybride local, compact et explicable :

1. **Alias exacts**
2. **Branche header**
3. **Branche values**
4. **Fusion**
5. **Projection sémantique produit**

### 1. Alias exacts

Les alias fournissent un fast-path haute précision pour les noms de colonnes
connus. Ils restent essentiels, mais doivent être conservateurs :

- un alias ambigu doit être désactivé ;
- un alias exact ne doit pas bypasser le classifieur si cela crée des faux
  positifs à confiance 1.0.

Références :

- [alias_registry.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/imports/ml/alias_registry.py)
- [column_aliases.yaml](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/imports/ml/column_aliases.yaml)

### 2. Branche header

La branche `header` classe le nom de colonne à partir d'un texte enrichi
normalisé. C'est la branche la plus performante quand le header est informatif.

Technologie :

- TF-IDF char n-grams
- Logistic Regression

Références :

- [train_header_model.py](/Users/julienbarbe/Dev/clients/niamoto/scripts/ml/train_header_model.py)
- [header_features.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/imports/ml/header_features.py)

### 3. Branche values

La branche `values` apprend à partir de statistiques et de patterns extraits des
valeurs :

- distributions numériques ;
- regex simples ;
- binaires, dates, coordonnées ;
- signaux de colonnes codées/catégorielles.

Elle est moins précise seule que `header`, mais elle est décisive pour :

- les headers anonymes ;
- les cas ambigus ;
- certains concepts fortement détectables par pattern.

Références :

- [train_value_model.py](/Users/julienbarbe/Dev/clients/niamoto/scripts/ml/train_value_model.py)
- [value_features.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/imports/ml/value_features.py)

### 4. Fusion

La fusion combine les deux branches dans un espace commun de concepts. Elle ne
doit pas être une simple moyenne implicite :

- elle reçoit les probabilités alignées des deux branches ;
- elle utilise des méta-features de confiance et de désaccord ;
- elle peut intégrer des garde-fous ciblés sur des erreurs fréquentes.

La fusion est la bonne couche pour corriger les cas où une branche devient trop
dominante sur un domaine particulier.

Références :

- [train_fusion.py](/Users/julienbarbe/Dev/clients/niamoto/scripts/ml/train_fusion.py)
- [fusion_features.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/imports/ml/fusion_features.py)

### 5. Projection sémantique produit

La vraie sortie produit n'est pas juste un concept brut. La branche actuelle
projette la détection vers :

- un `role`
- un `concept`
- des affordances et suggestions

Cette couche est ce qui aligne la détection avec le produit Niamoto.

Références :

- [semantic_profile.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/imports/ml/semantic_profile.py)
- [affordance_matcher.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/imports/ml/affordance_matcher.py)
- [profiler.py](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/core/imports/profiler.py)

## Pourquoi ce choix d'architecture

Cette architecture est adaptée aux contraintes réelles du projet :

- peu de données annotées au regard du nombre de concepts ;
- grande hétérogénéité de jeux de données ;
- multi-langues ;
- besoin d'explicabilité ;
- exécution locale ;
- coût d'entraînement court ;
- valeur produit plus proche du bon rôle et de la bonne suggestion que du
  concept fin parfait.

Une approche end-to-end plus "grosse" serait plus fragile ici qu'un système
hybride compact avec règles ciblées.

## Ce qu'on essaie vraiment d'améliorer

La branche ne cherche pas à maximiser un simple score de classification. Elle
cherche à améliorer :

- le taux d'auto-configuration correcte ;
- la robustesse sur datasets nouveaux ;
- la gestion des colonnes anonymes ;
- la qualité des suggestions en sortie ;
- la capacité à s'abstenir ou à rester prudente sur les cas durs.

## Vérité d'évaluation retenue

La métrique finale visée par la branche est le `NiamotoOfflineScore`, calculé
dans [evaluation.py](/Users/julienbarbe/Dev/clients/niamoto/scripts/ml/evaluation.py)
et exposé par [evaluate.py](/Users/julienbarbe/Dev/clients/niamoto/scripts/ml/evaluate.py).

Le score combine :

- `role_macro_f1`
- `critical_concept_macro_f1`
- `anonymous_role_macro_f1`
- `pair_consistency`
- `confidence_quality`
- `dataset_outcome`

Les holdouts importants sont :

- langues : `fr`, `es`, `de`, `zh`
- familles : `dwc_gbif`, `forest_inventory`, `tropical_field`,
  `research_traits`
- colonnes anonymes

## Rôle d'autoresearch

`autoresearch` ne doit pas décider de l'architecture. Il doit optimiser
localement un système déjà bien cadré.

Rôle attendu :

- proposer des variantes bornées ;
- évaluer rapidement ;
- garder les améliorations ;
- rejeter les régressions ;
- accélérer le tuning.

Ce qu'il ne doit pas faire :

- changer la vérité produit ;
- optimiser un score proxy au détriment des garde-fous ;
- introduire des règles agressives non validées ;
- dégrader silencieusement un holdout difficile pour gagner ailleurs.

## Programmes autoresearch recommandés

Trois niveaux de boucle sont utiles :

- [niamoto-header-model.md](/Users/julienbarbe/Dev/clients/niamoto/programmes/niamoto-header-model.md)
- [niamoto-values-model.md](/Users/julienbarbe/Dev/clients/niamoto/programmes/niamoto-values-model.md)
- [niamoto-fusion.md](/Users/julienbarbe/Dev/clients/niamoto/programmes/niamoto-fusion.md)

Le programme `fusion` joue désormais le rôle de programme de **stack complète**.

## Garde-fous actuels

Les résultats observés sur la branche indiquent que certains domaines doivent
être traités comme garde-fous explicites :

- `forest_inventory`
- `tropical_field`
- `fr`

Le plus gros risque constaté à ce stade est la sur-prédiction de concepts
inadaptés comme `statistic.count` sur des colonnes codées métier.

## Direction recommandée

La bonne direction n'est pas "plus de modèle". La bonne direction est :

- meilleure cohérence train/runtime ;
- meilleure évaluation ;
- meilleure fusion ;
- règles prudentes ciblées ;
- meilleur usage du contexte dataset-level.

La partie la plus prometteuse de la branche reste l'alignement :

`détection -> semantic_profile -> affordances -> suggestions`

et non pas la seule optimisation d'un classifieur isolé.
