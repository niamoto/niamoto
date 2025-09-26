# ML Detection System Overview

## Introduction

The Niamoto ML Detection system provides automatic field detection and mapping for imported data using machine learning techniques. This system analyzes data content to identify column types, semantic meaning, and suggest appropriate mappings.

## Core Components

### 1. ML Detector (`ml_detector.py`)
- **RandomForestClassifier** for column type detection
- Statistical feature extraction
- Semantic pattern recognition
- Confidence scoring

### 2. Auto Detector (`auto_detector.py`)
- Automatic configuration generation
- Field mapping suggestions
- Data profiling and analysis
- Integration with import pipeline

### 3. Bootstrap System (`bootstrap.py`)
- Initial configuration setup
- Template generation
- Quick start for new projects

### 4. Profiler (`profiler.py`)
- Data statistical analysis
- Pattern detection
- Quality assessment
- Feature extraction for ML

## Detection Capabilities

### Supported Field Types
- **Taxonomic**: species names, genus, family
- **Geographic**: latitude, longitude, coordinates
- **Temporal**: dates, timestamps, periods
- **Identifiers**: IDs, codes, references
- **Measurements**: numeric values with units
- **Categories**: classifications, types, status

### Detection Process

```python
# 1. Load and profile data
profiler = DataProfiler()
profile = profiler.analyze(dataframe)

# 2. Extract features
features = extract_features(profile)

# 3. Predict field types
detector = MLColumnDetector()
predictions = detector.predict(features)

# 4. Generate configuration
config = generate_config(predictions)
```

## Key Features

### Smart Detection
- Analyzes content patterns, not just column names
- Handles multiple languages and formats
- Adapts to domain-specific data

### Confidence Scoring
- Provides confidence levels for predictions
- Suggests manual review for low-confidence mappings
- Learns from user corrections

### Integration
- Seamless integration with import pipeline
- GUI support for visual configuration
- CLI commands for automation

## Architecture

```
┌─────────────────────┐
│   Input Data (CSV)  │
└──────────┬──────────┘
           │
    ┌──────▼──────┐
    │   Profiler  │
    └──────┬──────┘
           │
    ┌──────▼──────────┐
    │ Feature Extract │
    └──────┬──────────┘
           │
    ┌──────▼──────────┐
    │  ML Classifier  │
    └──────┬──────────┘
           │
    ┌──────▼──────────┐
    │ Config Generator│
    └──────┬──────────┘
           │
    ┌──────▼──────────┐
    │  import.yml     │
    └─────────────────┘
```

## Usage Examples

### CLI Usage
```bash
# Auto-detect and generate config
niamoto detect data.csv --output import.yml

# With custom model
niamoto detect data.csv --model custom_model.pkl
```

### Python API
```python
from niamoto.core.imports.ml_detector import MLColumnDetector
from niamoto.core.imports.auto_detector import AutoDetector

# Initialize detector
detector = MLColumnDetector()

# Detect column types
results = detector.detect_columns('data.csv')

# Generate configuration
auto_detector = AutoDetector()
config = auto_detector.generate_config(results)
```

## Training Custom Models

The system can be trained on domain-specific data:

```python
from niamoto.core.imports.ml_detector import train_detector

# Prepare training data
training_data = prepare_training_data()

# Train model
model = train_detector(training_data)

# Save model
model.save('custom_detector.pkl')
```

## Performance

- **Accuracy**: 85-95% on standard ecological data
- **Speed**: <1 second for typical CSV files
- **Scalability**: Handles files up to 1GB efficiently

## Future Enhancements

- Deep learning models for complex patterns
- Multi-language support expansion
- Real-time learning from user feedback
- Cloud-based model sharing

## Related Documentation

- [Implementation Details](implementation.md)
- [Training Guide](training-guide.md)
- [API Reference](detector-usage.md)
- [Roadmap](roadmap.md)
