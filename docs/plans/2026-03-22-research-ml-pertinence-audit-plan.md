---
title: Position interne — pertinence ML et pistes avant autoresearch
type: research
date: 2026-03-22
---

# Position interne : stack ML de détection vs littérature récente

Note d'orientation, pas revue académique. Objectif : vérifier que l'approche reste défendable et identifier 2 axes d'exploration pour la prochaine passe autoresearch.

## État actuel (après retrain 2026-03-21)

| Branche | Algorithme | Features | Macro-F1 |
|---------|-----------|----------|----------|
| Header | TF-IDF char_wb (2,5) + LogReg L1 (C=130) | Nom enrichi (dtype, sparsity, length) × 3 | 77% |
| Values | HistGradientBoosting (500 iter, depth 10) | 43 features statistiques/patterns | 35% |
| Fusion | LogReg (C=1.0, balanced) | ~70 meta-features (probas + confiance + gardes) | — |

- **Gold set** : 2 540 colonnes, 104 datasets, ~61 concepts coarse
- **ProductScore** : 80.84 — **GlobalScore** : 82.76
- **EvalSuite** : 90.4% rôle, 84.7% concept (478 colonnes, 9 datasets)
- **Contraintes** : offline, rapide, déterministe, pas de dépendance LLM

## Ce que la littérature récente valide

| Aspect | Notre choix | Appui |
|--------|------------|-------|
| Architecture header + values + fusion | 3 branches parallèles | Consensus depuis Sherlock (KDD 2019), confirmé par SATO (VLDB 2020). L'idée de combiner nom et valeurs reste le pattern dominant. |
| TF-IDF char n-grams sur headers | char_wb (2,5) + LogReg | Baseline pragmatique et naturellement cross-langue. Sherlock et SATO s'appuient sur des features similaires pour les noms. |
| Features statistiques pour valeurs | 43 features | Pythagoras (EDBT 2024) montre qu'un traitement spécialisé des colonnes numériques peut apporter des gains significatifs (+22% F1 sur numériques vs Sherlock, mais sur un benchmark et un label set différents des nôtres). |
| GroupKFold par dataset | Pas de fuite inter-colonnes | Standard dans les travaux sérieux. |
| Offline / pas de LLM | Millisecondes par colonne | Avantage concret. Korini & Bizer (2025) montrent que les approches LLM sont sensibles au setup et au coût — pas qu'elles écrasent forcément une stack classique sur un use case spécialisé. |

**Diagnostic : l'architecture est défendable.** Pas de signal dans la littérature récente qui justifierait une refonte.

## Pistes d'amélioration pour l'autoresearch

### Piste 1 — Features numériques enrichies (values branch)

**Intuition** : Pythagoras (EDBT 2024) suggère que la forme de la distribution et les patterns numériques fins apportent un pouvoir discriminant supplémentaire pour les colonnes numériques. Nos features actuelles couvrent les statistiques de base (mean, std, skew, kurtosis, ranges) mais manquent certains signaux :

- Forme de distribution (bimodale, log-normale, uniforme)
- Proportion de valeurs rondes (10, 20, 50...)
- Proportion de valeurs consécutives
- Ratio range/std (distingue uniforme vs concentré)

**Hypothèse de travail** : Ces features pourraient aider à mieux distinguer les concepts numériques proches (diameter vs height, biomass vs volume — les top confusions actuelles), mais le gain réel est à mesurer empiriquement via l'autoresearch.

**Effort** : Faible. Ajout dans `value_features.py` / `extract_value_features_from_series`.
**Compatible autoresearch** : Oui — values branch.

### Piste 2 — Contexte inter-colonnes (reranking ou changement d'API)

**Intuition** : SATO (VLDB 2020) a montré que le contexte de table améliore la détection. Le sujet reste actif — SIGMOD 2026 a accepté un papier sur la sélection de contexte pour l'annotation de colonnes (le titre exact et la portée restent à confirmer via les proceedings).

**État actuel** : Niamoto fait déjà de la cohérence dataset-level en post-traitement (`pair_consistency`, familles structurelles lat/lon, taxonomy_lineage). Mais ce n'est pas un signal qui influence les prédictions.

**Contrainte runtime** : le classifieur traite les colonnes une par une (`classifier.py:119`). Injecter des features dataset-level directement dans la fusion créerait une divergence train/runtime.

**Deux approches possibles** :
- **A. Reranking post-classification** : après avoir classé toutes les colonnes, ajuster les confiances en fonction du contexte (présence lat/lon, colonnes taxonomiques). Se fait dans `profiler.py`, sans toucher au modèle de fusion.
- **B. Passage de contexte au classifieur** : modifier `classify()` pour accepter un contexte dataset optionnel. Plus propre mais nécessite de mettre à jour train ET runtime en cohérence stricte.

**Hypothèse de travail** : Pourrait améliorer la cohérence structurelle sur les paires coordonnées et les hiérarchies taxonomiques. Impact à mesurer.

**Effort** : Moyen à élevé selon l'approche choisie.
**Compatible autoresearch** : Non directement — nécessite un choix d'approche et un cadrage d'implémentation avant de lancer l'autoresearch sur cet axe.

## Ce qu'on n'ouvre pas maintenant

| Piste | Pourquoi pas |
|-------|-------------|
| **Embeddings transformers** (CoLeM, Watchog) | Dépendance lourde (torch), contre contrainte offline léger. À reconsidérer si gold set > 10K colonnes. |
| **LLM adaptation** (ZTab, Korini/Bizer) | Notre gold set existe déjà. ZTab résout un problème qu'on n'a pas. Coût et déterminisme incompatibles. |
| **Weak supervision produit** (AdaTyper) | Feature produit, pas un axe d'autoresearch. Logger les corrections utilisateur reste une bonne idée pour plus tard. |

## Plan d'exécution

### Phase 1 : Mise à jour des programmes autoresearch

- [x] Ajouter l'axe "features numériques enrichies" dans `ml/programmes/niamoto-values-model.md`
  - Candidates : `bimodality_coefficient`, `pct_positive_log_skew`, `pct_round_values`, `pct_sequential` (sur valeurs triées uniques), `range_ratio`
- [x] Ajouter l'axe "contexte inter-colonnes" dans `ml/programmes/niamoto-fusion.md`
  - Cadré comme reranking post-classification OU changement d'API classifieur (pas de feature fusion directe sans choix d'approche)

### Phase 2 : Autoresearch

- [ ] Passe autoresearch values branch (features numériques)
- [ ] Choix d'approche pour le contexte inter-colonnes (reranking vs API)
- [ ] Implémentation du contexte inter-colonnes selon l'approche choisie
- [ ] Validation ProductScore et GlobalScore (baseline : 80.84 / 82.76)

## Vérification

- Tests : `uv run pytest tests/core/imports/ -x -q`
- Eval : `uv run python -m ml.scripts.eval.evaluate --model all --metric niamoto-score --splits 3`
- Comparer ProductScore avant/après (baseline : 80.84)

## Sources

Références vérifiées :
- Sherlock (KDD 2019) — https://vis.csail.mit.edu/pubs/sherlock/
- SATO (VLDB 2020) — https://github.com/megagonlabs/sato
- Pythagoras (EDBT 2024) — https://www.dfki.de/web/forschung/projekte-publikationen/publikation/16444
- Watchog (SIGMOD 2024) — https://2024.sigmod.org/toc.html
- CoLeM (ACL 2025 SRW) — https://aclanthology.org/2025.acl-srw.52/
- Korini & Bizer (2025) — https://dblp.org/rec/journals/corr/abs-2503-02718.html
- SIGMOD 2026 accepted papers — https://2026.sigmod.org/sigmod_papers.shtml

Références à confirmer (intuition solide, citation à préciser) :
- ZTab (ICDE 2026, mars) — zero-shot CTA via pseudo-tables, arXiv 2603.11436
- StraTyper (fév 2026) — découverte dynamique de types, arXiv 2602.04004
- ConTextTab — plus large que CTA strict, pas directement comparable à notre pipeline
