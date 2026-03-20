# Assistant de Configuration Niamoto : Approche Réaliste et Pragmatique

## Le Vrai Besoin : Simple et Efficace

**Objectif** : Un assistant qui analyse les données uploadées et suggère automatiquement la configuration appropriée (extraction → transformation → visualisation).

## Exemple Concret du Workflow Souhaité

```
1. Upload: occurrences.csv
   ↓
2. Détection: "dbh", "leaf_area", "family", "genus"...
   ↓
3. Suggestion automatique:
   - Extraction taxonomie depuis family/genus
   - Distribution DBH avec bins standards
   - Stats sur leaf_area
   ↓
4. Configuration générée prête à l'emploi
```

## Architecture Minimaliste : 3 Approches Possibles

### Option 1 : Règles + ML Classique (Sans LLM)

**Le plus simple et suffisant pour 80% des cas**

```python
class ConfigAssistant:
    """Assistant basé sur règles et ML classique"""

    def __init__(self):
        # Base de connaissances des patterns
        self.patterns = {
            'taxonomy': {
                'triggers': ['family', 'famille', 'genus', 'genre', 'species'],
                'suggest': 'taxonomy_extractor'
            },
            'measurements': {
                'dbh': {
                    'triggers': ['dbh', 'diameter', 'diametre'],
                    'transform': 'binned_distribution',
                    'params': {'bins': [10, 20, 30, 40, 50, 75, 100, 200]},
                    'viz': 'bar_plot'
                },
                'leaf_area': {
                    'triggers': ['leaf_area', 'surface_foliaire', 'la'],
                    'transform': 'statistical_summary',
                    'viz': 'box_plot'
                },
                'wood_density': {
                    'triggers': ['wood_density', 'densite_bois', 'wd'],
                    'transform': 'binned_distribution',
                    'params': {'bins': [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]},
                    'viz': 'histogram'
                }
            },
            'spatial': {
                'triggers': ['lat', 'lon', 'x', 'y', 'geo_pt', 'coordinates'],
                'suggest': 'spatial_validator',
                'viz': 'interactive_map'
            }
        }

        # Petit modèle de classification (Random Forest)
        self.classifier = self._load_simple_classifier()

    def analyze(self, df: pd.DataFrame) -> Dict:
        """Analyse les colonnes et suggère config"""

        suggestions = {
            'extract': [],
            'transform': [],
            'visualize': []
        }

        for col in df.columns:
            col_lower = col.lower()

            # 1. Détection par patterns
            for pattern_type, rules in self.patterns.items():
                if pattern_type == 'measurements':
                    for measure, config in rules.items():
                        if any(t in col_lower for t in config['triggers']):
                            suggestions['transform'].append({
                                'column': col,
                                'plugin': config['transform'],
                                'params': config.get('params', {}),
                                'confidence': 0.9
                            })
                            suggestions['visualize'].append({
                                'plugin': config['viz'],
                                'source': col
                            })

            # 2. Analyse statistique pour affiner
            if pd.api.types.is_numeric_dtype(df[col]):
                stats = self._analyze_distribution(df[col])
                if stats['is_continuous'] and stats['range'] > 100:
                    # Suggère binned_distribution
                    bins = self._suggest_bins(df[col])
                    suggestions['transform'].append({
                        'column': col,
                        'plugin': 'binned_distribution',
                        'params': {'bins': bins},
                        'confidence': 0.7
                    })

        # 3. Détection de relations
        suggestions['relationships'] = self._detect_relationships(df)

        return suggestions

    def _suggest_bins(self, series: pd.Series) -> List[float]:
        """Suggère des bins intelligents basés sur la distribution"""
        # Utilise quantiles ou Sturges' rule
        q = series.quantile([0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0])
        return list(q.round().astype(int).unique())

    def _detect_relationships(self, df: pd.DataFrame) -> List:
        """Détecte les relations entre colonnes"""
        relationships = []

        # Cherche les foreign keys potentielles
        for col in df.columns:
            if 'id_' in col.lower() or col.lower().endswith('_id'):
                relationships.append({
                    'type': 'foreign_key',
                    'column': col,
                    'references': col.replace('id_', '').replace('_id', '')
                })

        return relationships

    def generate_config(self, suggestions: Dict) -> str:
        """Génère la configuration YAML finale"""

        config = {
            'import': {},
            'transform': [],
            'export': []
        }

        # Génère les transformations
        for transform in suggestions['transform']:
            config['transform'].append({
                'name': f"{transform['column']}_distribution",
                'plugin': transform['plugin'],
                'params': transform['params']
            })

        # Génère les visualisations
        for viz in suggestions['visualize']:
            config['export'].append({
                'type': viz['plugin'],
                'source': viz['source']
            })

        return yaml.dump(config)
```

**Avantages** :
- ✅ Simple, rapide, prédictible
- ✅ Pas de dépendances lourdes
- ✅ Facilement extensible avec nouvelles règles
- ✅ Transparent (on sait pourquoi il suggère)

**Limitations** :
- ❌ Rigide pour cas non prévus
- ❌ Maintenance manuelle des règles

### Option 2 : Small Language Model (SLM) Spécialisé

**Un petit modèle entraîné spécifiquement pour cette tâche**

```python
class SLMConfigAssistant:
    """Petit modèle de langage spécialisé (< 1GB)"""

    def __init__(self):
        # Modèle BERT-like fine-tuné sur configs écologiques
        self.model = AutoModelForSequenceClassification.from_pretrained(
            "niamoto/config-bert-small",  # 100M params
            num_labels=len(PLUGIN_TYPES)
        )
        self.tokenizer = AutoTokenizer.from_pretrained("niamoto/config-bert-small")

    def suggest_plugin(self, column_name: str, sample_values: List) -> str:
        """Suggère le plugin approprié"""

        # Crée un prompt structuré
        prompt = f"""
        Column: {column_name}
        Sample values: {sample_values[:5]}
        Data type: {type(sample_values[0])}
        Unique ratio: {len(set(sample_values))/len(sample_values):.2f}
        """

        # Encode et prédit
        inputs = self.tokenizer(prompt, return_tensors="pt")
        outputs = self.model(**inputs)

        # Top-3 plugins suggérés
        probs = torch.softmax(outputs.logits, dim=-1)
        top3 = torch.topk(probs, k=3)

        suggestions = []
        for idx, prob in zip(top3.indices[0], top3.values[0]):
            plugin_name = PLUGIN_TYPES[idx]
            confidence = prob.item()

            # Génère les paramètres appropriés
            params = self._generate_params(column_name, sample_values, plugin_name)

            suggestions.append({
                'plugin': plugin_name,
                'confidence': confidence,
                'params': params
            })

        return suggestions[0]  # Meilleure suggestion

    def _generate_params(self, col_name: str, values: List, plugin: str) -> Dict:
        """Génère les paramètres du plugin"""

        if plugin == 'binned_distribution':
            # Analyse la distribution
            if 'dbh' in col_name.lower():
                return {'bins': [10, 20, 30, 40, 50, 75, 100, 200]}
            else:
                # Bins automatiques basés sur quantiles
                arr = np.array(values)
                bins = np.quantile(arr, [0, 0.2, 0.4, 0.6, 0.8, 1.0])
                return {'bins': bins.tolist()}

        elif plugin == 'statistical_summary':
            return {
                'metrics': ['mean', 'median', 'std', 'min', 'max'],
                'group_by': None  # À détecter
            }

        return {}
```

**Entraînement du modèle** :
```python
# Dataset d'entraînement : configs existantes annotées
training_data = [
    {"column": "dbh", "values": [15, 23, 45], "label": "binned_distribution"},
    {"column": "family", "values": ["Arecaceae"], "label": "taxonomy_extractor"},
    {"column": "leaf_area", "values": [12.5, 8.3], "label": "statistical_summary"},
    # ... milliers d'exemples
]

# Fine-tuning sur BERT-small (prend 2h sur GPU)
```

**Avantages** :
- ✅ Plus flexible que règles pures
- ✅ Apprend des patterns complexes
- ✅ Taille raisonnable (100MB-1GB)
- ✅ Rapide en inférence

**Limitations** :
- ❌ Nécessite données d'entraînement
- ❌ Boîte noire relative

### Option 3 : LLM Léger avec Few-Shot Learning

**Utilise un LLM existant mais petit et efficace**

```python
class LLMConfigAssistant:
    """LLM léger pour génération de config"""

    def __init__(self):
        # Modèles possibles : Mistral-7B, Llama3-8B, Phi-3
        self.model = AutoModelForCausalLM.from_pretrained(
            "microsoft/Phi-3-mini-4k-instruct",  # 3.8B params
            torch_dtype=torch.float16,
            device_map="auto"
        )

    def generate_config(self, data_profile: Dict) -> str:
        """Génère config avec few-shot prompting"""

        prompt = f"""
Tu es un assistant pour générer des configurations Niamoto.
Analyse ces données et suggère la configuration appropriée.

Exemples:
1. Colonne "dbh" avec valeurs [15, 23, 45, 67] →
   transform:
     - plugin: binned_distribution
       params:
         field: dbh
         bins: [10, 20, 30, 40, 50, 75, 100]

2. Colonnes "family", "genus", "species" →
   extract:
     - plugin: taxonomy_extractor
       params:
         hierarchy: [family, genus, species]

3. Colonne "leaf_area" avec valeurs numériques →
   transform:
     - plugin: statistical_summary
       params:
         field: leaf_area
         metrics: [mean, std]

Maintenant, analyse ces données:
Colonnes détectées: {data_profile['columns']}
Types: {data_profile['types']}
Échantillons: {data_profile['samples']}

Configuration suggérée:
"""

        # Génération avec contraintes
        output = self.model.generate(
            prompt,
            max_length=500,
            temperature=0.3,  # Peu de créativité
            do_sample=True
        )

        # Parse et valide YAML
        config_text = output.split("Configuration suggérée:")[-1]
        return self._validate_yaml(config_text)
```

**Avantages** :
- ✅ Très flexible, comprend le contexte
- ✅ Pas besoin d'entraînement spécifique
- ✅ Peut gérer cas imprévus
- ✅ Explications en langage naturel

**Limitations** :
- ❌ Plus lourd (3-8GB)
- ❌ Plus lent (1-5 secondes)
- ❌ Peut halluciner

## Recommandation : Approche Hybride Progressive

### Phase 1 : Règles + ML Classique (3 mois)
```python
class HybridAssistant:
    def __init__(self):
        self.rule_engine = RuleBasedDetector()      # 90% des cas
        self.ml_fallback = RandomForestClassifier()  # Cas ambigus

    def suggest(self, data):
        # 1. Essaie les règles
        if self.rule_engine.confidence(data) > 0.8:
            return self.rule_engine.suggest(data)

        # 2. Fallback ML pour cas complexes
        return self.ml_fallback.predict(data)
```

**Pourquoi commencer par là** :
- ✅ Rapide à implémenter
- ✅ Contrôle total
- ✅ Pas de dépendances lourdes
- ✅ Collecte des données pour Phase 2

### Phase 2 : Small LM Fine-tuné (6 mois)
- Entraîner un BERT-small sur les configs collectées
- Remplacer progressivement les règles
- Garder règles pour validation

### Phase 3 : LLM Optionnel (12 mois)
- Seulement si nécessaire
- Pour cas très complexes
- Interface conversationnelle

## Implémentation Concrète pour Niamoto

```python
# niamoto/core/assistant/config_assistant.py
class NiamotoConfigAssistant:
    """Assistant minimaliste pour Niamoto"""

    # Mappings écologie connus
    ECOLOGY_MAPPINGS = {
        'dbh': {
            'transform': 'binned_distribution',
            'bins': [10, 20, 30, 40, 50, 75, 100, 200],
            'viz': 'bar_plot'
        },
        'height': {
            'transform': 'binned_distribution',
            'bins': [5, 10, 15, 20, 25, 30, 40],
            'viz': 'bar_plot'
        },
        'leaf_area': {
            'transform': 'statistical_summary',
            'viz': 'box_plot'
        },
        'wood_density': {
            'transform': 'binned_distribution',
            'bins': [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            'viz': 'histogram'
        }
    }

    def analyze_file(self, file_path: Path) -> Dict:
        """Point d'entrée principal"""

        df = pd.read_csv(file_path, nrows=1000)  # Sample

        config = {
            'import': self._suggest_import(df),
            'transform': self._suggest_transforms(df),
            'export': self._suggest_exports(df)
        }

        return config

    def _suggest_transforms(self, df: pd.DataFrame) -> List:
        """Suggère les transformations appropriées"""

        transforms = []

        for col in df.columns:
            col_lower = col.lower()

            # Check mappings connus
            for pattern, config in self.ECOLOGY_MAPPINGS.items():
                if pattern in col_lower:
                    transforms.append({
                        'name': f"{col}_distribution",
                        'plugin': config['transform'],
                        'params': {
                            'source': 'occurrences',
                            'field': col,
                            'bins': config.get('bins'),
                            'include_percentages': True
                        }
                    })

                    # Ajoute la viz correspondante
                    self.suggested_viz.append({
                        'widget': config['viz'],
                        'data': f"{col}_distribution"
                    })

        return transforms
```

## Est-ce Possible ? OUI !

**Faisabilité technique** : ✅ 100%
- Les patterns écologiques sont prévisibles
- Les plugins Niamoto ont une logique claire
- Beaucoup peut être fait avec des règles simples

**Effort requis** :
- Version basique (règles) : 2 semaines
- Version ML classique : 1 mois
- Version SLM : 3 mois

**ROI** :
- 80% d'automatisation avec règles simples
- 95% avec ML classique + règles
- 99% avec LLM (mais overkill)

## Conclusion

Pour Niamoto, **commencer simple avec règles + ML classique** est la bonne approche. C'est :
- Suffisant pour détecter dbh → binned_distribution → bar_plot
- Extensible progressivement
- Transparent et maintenable
- Sans dépendances lourdes

Un LLM n'est pas nécessaire pour ce niveau d'assistance. Les patterns écologiques sont suffisamment standardisés pour être gérés par des règles et du ML classique.
