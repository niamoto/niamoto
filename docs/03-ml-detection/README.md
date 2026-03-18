# ML Detection & Auto-Configuration

Machine learning-based column detection and automatic configuration generation.

## 📚 Documents in this Section

- **[Overview](overview.md)** - Introduction to ML detection system
- **[Branch Architecture](branch-architecture.md)** - Current branch architecture and product goal
- **[Autoresearch Surrogate Loop](autoresearch-surrogate-loop.md)** - Why end-to-end autoresearch is too slow and how to pivot to a fusion-only surrogate loop
- **Fusion Surrogate Runner** - `uv run python -m scripts.ml.run_fusion_surrogate_autoresearch --iterations 50`
- **[Acquisition Plan](acquisition-plan.md)** - Concrete plan to acquire and integrate new benchmark data
- **[Candidate Data Sources](candidate-data-sources.md)** - Shortlist of external datasets to strengthen the benchmark
- **[Current State](current-state.md)** - Current implementation status
- **[Experiment Log](experiments/2026-03-17-ml-detection-iteration-log.md)** - Dated journal of current ML iterations
- **[Training Guide](training-guide.md)** - Train custom detection models
- **[Implementation](implementation.md)** - Technical implementation details
- **[Detector Usage](detector-usage.md)** - Using the ML detector
- **[Synthetic Data](synthetic-data.md)** - Generate training data
- **[Semantic Detection](semantic-detection.md)** - Semantic type analysis
- **[Auto Configuration](auto-config-roadmap.md)** - Automatic config generation
- **[Roadmap](roadmap.md)** - Future development plans

## 🤖 Key Features

- **Automatic Column Detection**: Identifies data types and semantic meaning
- **Smart Mapping**: Suggests column mappings based on content
- **Configuration Generation**: Creates import configs automatically
- **Custom Training**: Train models on your specific data patterns

## 🚀 Quick Start

1. **Basic Usage**: Start with [Detector Usage](detector-usage.md)
2. **Understanding**: Read the [Overview](overview.md)
3. **Training**: Follow the [Training Guide](training-guide.md)
4. **Advanced**: Explore [Implementation](implementation.md)

## 🔬 Technical Stack

- **scikit-learn**: Classification models
- **pandas**: Data profiling
- **Custom features**: Statistical and semantic analysis

## 📖 Related Documentation

- [Data Pipeline](../02-data-pipeline/README.md) - Integration with import process
- [Configuration](../08-configuration/README.md) - Configuration strategies
- [API Reference](../05-api-reference/README.md) - ML API documentation

---
*Status: Active development - see [Current State](current-state.md) and [Roadmap](roadmap.md)*
