# ML Detection & Auto-Configuration

Machine learning-based column detection and automatic configuration generation for ecological datasets.

## Documentation

### Core

- **[Overview](overview.md)** — What ML detection does, how it works, training data, scores, and how to contribute
- **[Branch Architecture](branch-architecture.md)** — Architecture of the 3-branch hybrid pipeline (alias + header + values + fusion), product goals, evaluation metrics, and autoresearch role
- **[Training & Evaluation Guide](training-guide.md)** — Complete workflow: gold set → training → alias → evaluation → improvement cycle

### Integration & Status

- **[ML Integration Status](2026-03-19-ml-integration-status.md)** — Current state of ML integration in the app: what works, the gap between `ColumnDetector` (heuristics) and `ColumnClassifier` (ML), and the recommended merge strategy

### Autoresearch

- **[Autoresearch Surrogate Loop](autoresearch-surrogate-loop.md)** — Why full-stack autoresearch is too slow, and the pivot to a fusion-only surrogate loop with two validation levels

### Data Acquisition

- **[Acquisition Plan](acquisition-plan.md)** — Concrete plan: which datasets to acquire first, storage structure, benchmark tags, and progress tracking
- **[Candidate Data Sources](candidate-data-sources.md)** — Shortlist of 15 candidate datasets with priorities, access conditions, and selection criteria

### Experiments

- **[Experiment Logs](experiments/)** — Session logs and evaluation results (iteration logs, instance evaluation, session handoffs)

## Technical Stack

- **scikit-learn**: TF-IDF, LogisticRegression, HistGradientBoosting
- **DuckDB**: Data profiling and feature extraction
- **Fully offline**: ~3 MB models, no LLM dependency

## Quick Start

1. Read the **[Overview](overview.md)** to understand what the system does
2. See **[Training & Evaluation Guide](training-guide.md)** for the complete workflow
3. See **[Branch Architecture](branch-architecture.md)** for the technical design
4. Check **[ML Integration Status](2026-03-19-ml-integration-status.md)** for current app integration

## Related Documentation

- [Data Pipeline](../02-data-pipeline/README.md) — Integration with import process
- [Configuration](../08-configuration/README.md) — Configuration strategies
- [API Reference](../05-api-reference/README.md) — ML API documentation
