# Autoresearch Surrogate Loop

## Objet

Ce document formalise le pivot suivant :

- arrêter de faire tourner `autoresearch` directement sur une métrique
  end-to-end trop coûteuse ;
- recentrer la boucle autonome sur une **surrogate loop fusion-only** ;
- réserver les métriques stack complètes à la validation différée des meilleurs
  candidats.

## Problème constaté

Le pattern `autoresearch` n'a d'intérêt que s'il peut enchaîner beaucoup
d'itérations de façon autonome.

Sur cette branche, même les variantes récentes de métriques rapides restent trop
chères :

- `product-score` : trop lent pour une boucle autonome ;
- `product-score-mid` : encore trop coûteux pour une exploration large ;
- `product-score-fast-fast` : plus court, mais encore trop long pour viser
  50+ runs par session.

Le vrai problème n'est donc pas seulement la métrique. C'est la **granularité de
la recherche** :

- on réentraîne toute la stack pour un changement souvent local ;
- on paie un coût complet pour une modification qui concerne seulement la
  fusion ;
- la boucle autonome dépense son budget en certification au lieu de chercher.

## Décision

Le prochain mode `autoresearch` ne doit plus être :

- `stack complète -> métrique complète -> garde-fous complets`

à chaque itération.

Il doit devenir :

- `surrogate locale très bon marché -> beaucoup d'itérations`
- puis `validation différée` sur les meilleurs candidats seulement.

## Principe de la boucle fusion-only

La fusion est aujourd'hui le meilleur point d'entrée pour une surrogate loop,
parce que :

- son périmètre est borné ;
- ses changements sont souvent locaux ;
- elle consomme des signaux déjà produits par `header` et `values` ;
- elle peut être réentraînée beaucoup plus vite si on met les bons caches en
  place.

L'idée est de figer, pour un benchmark donné :

- les splits ;
- les sorties de la branche `header` ;
- les sorties de la branche `values` ;
- les labels cibles ;
- les features de fusion de base.

Ensuite, la boucle `autoresearch` ne réentraîne plus que le modèle de fusion,
ou une petite variante de ses features, sans refaire la stack complète à chaque
run.

## Ce que la surrogate loop doit optimiser

La métrique locale ne doit pas prétendre remplacer la vérité produit. Elle doit
être :

- rapide ;
- stable ;
- sensible aux vrais gains de fusion ;
- suffisamment corrélée à la validation stack pour servir de filtre.

Dans ce mode, on optimise un **FusionSurrogateScore** calculé à partir de folds
préparés à l'avance.

Ce score doit surtout récompenser :

- la bonne combinaison `header/values` ;
- la robustesse sur les colonnes anonymes ;
- la qualité sur `en_field` ;
- la qualité sur `tropical_field` et `research_traits` si ces exemples sont
  présents dans le cache ;
- la réduction des faux positifs `statistic.count` sur les colonnes codées.

## Caches à produire

La clé de vitesse est ici.

Pour chaque fold figé, on veut stocker :

- `train_records`
- `test_records`
- probabilités `header` alignées sur tous les concepts
- probabilités `values` alignées sur tous les concepts
- méta-features de base de fusion
- labels cibles
- métadonnées de bucket :
  - `tropical_field`
  - `research_traits`
  - `en_field`
  - `gbif_core_standard`
  - `anonymous`

Format recommandé :

- `data/cache/ml/fusion_surrogate/<cache_version>/fold_*.npz`
- plus un `manifest.json` décrivant :
  - hash du gold set
  - liste des concepts
  - protocole
  - version des features

## Deux niveaux de surrogate

### 1. Surrogate ultra-rapide

But :

- explorer beaucoup ;
- rejeter vite ;
- accepter qu'elle soit un peu approximative.

Contenu recommandé :

- quelques folds fixes ;
- buckets critiques seulement ;
- réentraînement fusion uniquement ;
- pas de rerun header/value.

### 2. Surrogate de promotion

But :

- confirmer les meilleurs candidats ;
- vérifier qu'un gain local fusion ne part pas dans une direction trompeuse.

Contenu recommandé :

- même cache, mais plus de folds ou plus de buckets ;
- toujours sans réentraîner toute la stack ;
- coût plus élevé que l'ultra-rapide, mais encore bien inférieur au
  `product-score` complet.

## Chaîne de validation recommandée

La nouvelle chaîne doit devenir :

1. `fusion-surrogate-fast`
2. `fusion-surrogate-mid`
3. `product-score-fast-fast`
4. `product-score-mid`
5. `product-score`
6. `niamoto-score`

Interprétation :

- les deux premiers niveaux servent à l'exploration autonome ;
- les niveaux 3 à 6 servent à la promotion des vrais gagnants.

## Règle d'acceptation recommandée

Un candidat peut être :

- `candidate`
  - bat `fusion-surrogate-fast`
- `provisional`
  - bat `fusion-surrogate-mid`
- `promotable`
  - bat `product-score-fast-fast`
- `validated`
  - bat `product-score-mid`
- `certified`
  - bat `product-score`
  - ne casse pas `niamoto-score`

Le point important :

- la boucle autonome ne doit pas attendre `certified` pour continuer à vivre ;
- elle doit surtout produire une file de candidats prometteurs.

## Périmètre initial recommandé

Premier chantier conseillé :

- boucle `fusion-only`

Fichiers concernés :

- `scripts/ml/train_fusion.py`
- `src/niamoto/core/imports/ml/classifier.py`
- futur script de cache surrogate

À ne pas mettre dans la première boucle :

- alias registry
- règles de profiler
- gold set
- dashboard
- docs produit

## Non-objectifs

Ce pivot ne cherche pas à :

- remplacer la validation produit réelle ;
- masquer les régressions globales ;
- supprimer le `product-score` ou le `niamoto-score`.

Il cherche à :

- rendre `autoresearch` enfin praticable ;
- redonner de la cadence à l'exploration ;
- séparer clairement exploration et certification.

## État courant

Les briques minimales sont maintenant en place :

1. construire le cache `fusion_surrogate`
   via :

```bash
uv run python -m scripts.ml.build_fusion_surrogate_cache --gold-set data/gold_set.json --splits 3
```

2. exposer une commande type :

```bash
uv run python -m scripts.ml.evaluate --model fusion --metric surrogate-fast
```

3. exposer aussi :

```bash
uv run python -m scripts.ml.evaluate --model fusion --metric surrogate-mid
```

4. faire tourner `autoresearch` uniquement sur ces métriques
5. ne promouvoir en validation stack complète que les meilleurs candidats

Runner local ajouté :

```bash
uv run python -m scripts.ml.run_fusion_surrogate_autoresearch --iterations 50
```

Comportement :

- calcule les baselines `surrogate-fast`, `surrogate-mid`
- diffère `product-score-fast-fast` jusqu'au premier candidat qui passe `surrogate-mid`
- lance une itération `codex` par candidat
- évalue lui-même les gates
- revert les perdants
- committe automatiquement les gagnants pour garder un worktree propre
- écrit un journal JSONL sous `.autoresearch/`

## Premières mesures

Sur le gold set courant :

- build du cache `fusion_surrogate` (`splits=3`) :
  - environ `490s` (`~8m10s`)
- `surrogate-fast` sur cache chaud :
  - environ `1.66s`
- `surrogate-mid` sur cache chaud :
  - environ `1.31s`

Lecture :

- le build initial reste un coût one-shot notable ;
- en revanche, les runs fusion-only sont enfin suffisamment rapides pour
  supporter une vraie boucle `autoresearch`.

## Décision de référence

Tant que cette surrogate loop n'existe pas, `autoresearch` stack complet reste
structurellement trop lent pour délivrer sa vraie valeur.
