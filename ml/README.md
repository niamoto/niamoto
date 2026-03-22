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

```bash
uv run python -m ml.scripts.data.build_gold_set
uv run python -m ml.scripts.train.train_header_model
uv run python -m ml.scripts.train.train_value_model
uv run python -m ml.scripts.train.train_fusion
uv run python -m ml.scripts.eval.run_eval_suite
uv run python -m ml.scripts.eval.evaluate --model all --metric niamoto-score
```
