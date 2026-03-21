# Acceptance Benchmark

Frozen acceptance datasets used to measure product-adjacent ML quality outside
the training gold set.

Rules:

- datasets listed in `manifest.yml` must not be added to `scripts/ml/build_gold_set.py`
  unless they are explicitly removed from the acceptance benchmark first;
- acceptance results are diagnostic and should be reviewed alongside, not mixed
  into, training metrics;
- the initial benchmark contains:
  - `instances_real`: a real Niamoto instance not used for training
  - `coded_inventory`: a coded inventory stress test excluded from training
