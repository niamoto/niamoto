# ML Workspace

Tout le chantier ML hors runtime produit est centralise ici.

## Arborescence

- `data/`
  - sources d'entrainement, gold set, benchmarks, resultats, cache
- `models/`
  - artefacts entraines (`header`, `value`, `fusion`)
- `programmes/`
  - playbooks d'autoresearch et de pilotage
- `scripts/data/`
  - construction et taxonomie du gold set
- `scripts/train/`
  - entrainement des branches et de la fusion
- `scripts/eval/`
  - holdouts historiques, eval suite, harnesses d'evaluation
- `scripts/research/`
  - cache surrogate et runner autoresearch

## Runtime produit

Le runtime reste volontairement hors de ce hub :

- `src/niamoto/core/imports/ml/`

## Commandes utiles

```bash
uv run python -m ml.scripts.data.build_gold_set
uv run python -m ml.scripts.train.train_header_model
uv run python -m ml.scripts.train.train_value_model
uv run python -m ml.scripts.train.train_fusion
uv run python -m ml.scripts.eval.run_eval_suite
uv run python -m ml.scripts.eval.evaluate --model all --metric niamoto-score
```
