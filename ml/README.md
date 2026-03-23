# ML Workspace

All offline ML work (training, evaluation, research) is centralized here.

## Directory structure

- `data/`
  - training sources, gold set, benchmarks, results, cache
- `models/`
  - trained artifacts (`header`, `value`, `fusion`)
- `programmes/`
  - autoresearch and steering playbooks
- `scripts/data/`
  - gold set construction and concept taxonomy
- `scripts/train/`
  - branch and fusion model training
- `scripts/eval/`
  - historical holdouts, eval suite, evaluation harnesses
- `scripts/research/`
  - surrogate cache and autoresearch runner

## Production runtime

The runtime classifier intentionally lives outside this workspace:

- `src/niamoto/core/imports/ml/`

## Useful commands

### Full rebuild

```bash
uv run python -m ml.scripts.data.build_gold_set
uv run python -m ml.scripts.train.train_header_model
uv run python -m ml.scripts.train.train_value_model
uv run python -m ml.scripts.train.train_fusion
uv run python -m ml.scripts.eval.run_eval_suite
```

### Partial retrain

```bash
uv run python -m ml.scripts.train.train_value_model
uv run python -m ml.scripts.train.train_fusion
```

### Gold-set / holdout evaluation

```bash
uv run python -m ml.scripts.eval.evaluate --model values --metric macro-f1 --splits 5
uv run python -m ml.scripts.eval.evaluate --model fusion --metric macro-f1 --splits 5
uv run python -m ml.scripts.eval.evaluate --model all --metric product-score --splits 3
uv run python -m ml.scripts.eval.evaluate --model all --metric niamoto-score --splits 3
```

### Real-dataset evaluation

```bash
uv run python -m ml.scripts.eval.run_eval_suite
uv run python -m ml.scripts.eval.run_eval_suite --tier 1
uv run python -m ml.scripts.eval.run_eval_suite --tier gbif
uv run python -m ml.scripts.eval.run_eval_suite --tier acceptance
```

### Fusion autoresearch

```bash
uv run python -m ml.scripts.research.build_fusion_surrogate_cache --gold-set ml/data/gold_set.json --splits 3
uv run python -m ml.scripts.eval.evaluate --model fusion --metric surrogate-fast --splits 3
uv run python -m ml.scripts.eval.evaluate --model fusion --metric surrogate-mid --splits 3
uv run python -m ml.scripts.research.run_fusion_surrogate_autoresearch --iterations 50
```

### Value-feature ablation

```bash
uv run python ml/scripts/research/ablation_run.py baseline
uv run python ml/scripts/research/ablation_run.py pct_round_values
uv run python ml/scripts/research/ablation_run.py range_ratio
```

## Where to look

- `ml/data/`: training sources, gold set, eval datasets, caches, results
- `ml/models/`: trained model artifacts
- `ml/programmes/`: autoresearch playbooks and decision rules
- `src/niamoto/core/imports/ml/`: production runtime classifier
