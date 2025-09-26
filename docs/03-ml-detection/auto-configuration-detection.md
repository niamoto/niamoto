# Assistant Intelligent : Détection par Analyse des Valeurs

## Le Vrai Problème : Variabilité Infinie des Noms

Les utilisateurs peuvent nommer leurs colonnes :
- `dbh`, `diameter`, `D130`, `diam_1.3m`, `circonference`, `girth`
- `superficie_foliaire`, `leaf_surface`, `LA`, `surface_feuille`
- `espece`, `sp`, `taxon`, `nom_scientifique`, `latin_name`

**On ne peut PAS maintenir une liste de synonymes !**

## Solution : Analyse Intelligente des Valeurs + Contexte

### Approche 1 : Détection par Signatures Statistiques

```python
class SmartColumnDetector:
    """Détecte le type de données par analyse des valeurs, pas des noms"""

    def detect_column_type(self, series: pd.Series, column_name: str,
                          context: Dict) -> Dict:
        """
        Analyse les VALEURS pour deviner le type de données
        """

        # 1. Analyse statistique de base
        profile = self._profile_values(series)

        # 2. Détection par patterns de valeurs
        detected_type = self._detect_by_values(profile)

        # 3. Utilise le contexte pour affiner
        refined_type = self._refine_with_context(detected_type, context)

        return {
            'type': refined_type,
            'confidence': profile['confidence'],
            'reasoning': profile['reasoning']
        }

    def _profile_values(self, series: pd.Series) -> Dict:
        """Profile statistique des valeurs"""

        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()
            return {
                'dtype': 'numeric',
                'range': (clean.min(), clean.max()),
                'mean': clean.mean(),
                'std': clean.std(),
                'distribution': self._check_distribution(clean),
                'typical_values': clean.value_counts().head(10).to_dict(),
                'unique_ratio': len(clean.unique()) / len(clean)
            }

        elif pd.api.types.is_object_dtype(series):
            return {
                'dtype': 'text',
                'unique_count': series.nunique(),
                'sample_values': series.dropna().head(20).tolist(),
                'avg_length': series.astype(str).str.len().mean(),
                'patterns': self._detect_text_patterns(series)
            }

    def _detect_by_values(self, profile: Dict) -> str:
        """
        Détecte le type basé sur les valeurs, PAS le nom
        """

        if profile['dtype'] == 'numeric':
            range_min, range_max = profile['range']

            # DBH : généralement entre 5 et 500 cm
            if 5 <= range_min <= 20 and 50 <= range_max <= 500:
                if profile['distribution'] == 'right_skewed':  # DBH est typiquement skewed
                    return 'diameter_measurement'

            # Height : généralement entre 1 et 60 m
            elif 0.5 <= range_min <= 5 and 10 <= range_max <= 60:
                if profile['std'] / profile['mean'] < 0.8:  # Moins variable que DBH
                    return 'height_measurement'

            # Leaf area : généralement petites valeurs
            elif 0.1 <= range_min <= 1 and 10 <= range_max <= 1000:
                if profile['unique_ratio'] > 0.7:  # Très variable
                    return 'leaf_area'

            # Wood density : entre 0.1 et 1.5
            elif 0.1 <= range_min <= 0.3 and 0.5 <= range_max <= 1.5:
                if profile['std'] < 0.3:  # Peu de variation
                    return 'wood_density'

            # Coordinates
            elif -180 <= range_min and range_max <= 180:
                if -90 <= range_min and range_max <= 90:
                    return 'latitude'
                else:
                    return 'longitude'

        elif profile['dtype'] == 'text':
            samples = profile['sample_values']

            # Détection taxonomie par patterns
            if self._looks_like_species(samples):
                return 'species_name'
            elif self._looks_like_family(samples):
                return 'family_name'
            elif self._looks_like_location(samples):
                return 'location_name'

        return 'unknown'

    def _looks_like_species(self, samples: List[str]) -> bool:
        """
        Détecte si ça ressemble à des noms d'espèces
        PEU IMPORTE comment c'est nommé
        """

        # Pattern : 2 mots, premier avec majuscule, deuxième en minuscule
        binomial_pattern = 0
        for s in samples[:20]:
            if isinstance(s, str):
                parts = s.split()
                if len(parts) == 2:
                    if parts[0][0].isupper() and parts[1][0].islower():
                        binomial_pattern += 1

        # Pattern : mots latins typiques
        latin_endings = ['us', 'a', 'um', 'is', 'ensis', 'oides']
        latin_count = sum(
            1 for s in samples
            if isinstance(s, str) and any(s.endswith(e) for e in latin_endings)
        )

        return binomial_pattern > 5 or latin_count > 8

    def _looks_like_family(self, samples: List[str]) -> bool:
        """Détecte les familles botaniques"""

        # Les familles botaniques finissent souvent par -aceae, -idae
        family_endings = ['aceae', 'idae', 'ales', 'ineae']
        count = sum(
            1 for s in samples
            if isinstance(s, str) and any(s.lower().endswith(e) for e in family_endings)
        )

        return count > len(samples) * 0.3

    def _check_distribution(self, values: pd.Series) -> str:
        """Analyse la distribution statistique"""

        from scipy import stats

        # Test de normalité
        if len(values) > 30:
            _, p_value = stats.normaltest(values)
            if p_value > 0.05:
                return 'normal'

        # Check skewness
        skew = values.skew()
        if skew > 1:
            return 'right_skewed'  # Typique pour DBH
        elif skew < -1:
            return 'left_skewed'

        return 'uniform'
```

### Approche 2 : Embeddings Sémantiques (Plus Sophistiqué)

```python
class SemanticColumnDetector:
    """Utilise des embeddings pour comprendre le sens des colonnes"""

    def __init__(self):
        # Modèle d'embeddings léger
        from sentence_transformers import SentenceTransformer
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')  # 80MB

        # Embeddings de référence pour concepts écologiques
        self.reference_embeddings = self._create_reference_embeddings()

    def _create_reference_embeddings(self):
        """Crée des embeddings pour les concepts connus"""

        concepts = {
            'diameter': [
                'diameter at breast height', 'dbh', 'trunk diameter',
                'tree girth', 'circonference', 'stem diameter'
            ],
            'height': [
                'tree height', 'canopy height', 'plant height',
                'hauteur', 'vertical measurement'
            ],
            'species': [
                'species name', 'scientific name', 'latin name',
                'taxonomic name', 'binomial nomenclature'
            ],
            'leaf_area': [
                'leaf surface area', 'foliar area', 'leaf size',
                'blade area', 'lamina surface'
            ]
        }

        embeddings = {}
        for concept, descriptions in concepts.items():
            # Moyenne des embeddings pour robustesse
            emb = self.encoder.encode(descriptions)
            embeddings[concept] = emb.mean(axis=0)

        return embeddings

    def detect_semantic_type(self, column_name: str, sample_values: List) -> str:
        """
        Détecte le type par similarité sémantique
        """

        # Combine nom de colonne + échantillon de valeurs pour contexte
        context = f"Column: {column_name}\nSample values: {sample_values[:5]}"

        # Encode le contexte
        context_embedding = self.encoder.encode(context)

        # Compare avec références
        similarities = {}
        for concept, ref_embedding in self.reference_embeddings.items():
            similarity = cosine_similarity(context_embedding, ref_embedding)
            similarities[concept] = similarity

        # Retourne le plus similaire si > seuil
        best_match = max(similarities, key=similarities.get)
        if similarities[best_match] > 0.6:
            return best_match

        return 'unknown'
```

### Approche 3 : ML Léger sur Features (Le Plus Pragmatique)

```python
class MLColumnClassifier:
    """
    Petit modèle ML qui apprend des patterns
    Ne se base PAS sur les noms de colonnes
    """

    def __init__(self):
        from sklearn.ensemble import RandomForestClassifier
        self.model = RandomForestClassifier(n_estimators=100)
        self.is_trained = False

    def extract_features(self, series: pd.Series) -> np.array:
        """
        Extrait des features SANS utiliser le nom de colonne
        """

        features = []

        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()

            # Features statistiques
            features.extend([
                clean.mean(),
                clean.std(),
                clean.min(),
                clean.max(),
                clean.quantile(0.25),
                clean.quantile(0.75),
                clean.skew(),
                clean.kurtosis(),
                len(clean.unique()) / len(clean),  # Unique ratio
                (clean > 0).mean(),  # Proportion positive
                (clean % 1 != 0).mean(),  # Proportion decimals
            ])

            # Features de distribution
            hist, _ = np.histogram(clean, bins=10)
            hist_norm = hist / hist.sum()
            features.extend(hist_norm)  # 10 features

        else:
            # Features pour texte
            str_series = series.astype(str)
            features.extend([
                str_series.str.len().mean(),  # Longueur moyenne
                str_series.str.count(' ').mean(),  # Nombre de mots
                str_series.str.count('[A-Z]').mean(),  # Majuscules
                str_series.str.count('[a-z]').mean(),  # Minuscules
                series.nunique() / len(series),  # Unique ratio
                0, 0, 0, 0, 0,  # Padding pour même taille
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
            ])

        return np.array(features[:21])  # Taille fixe

    def train(self, training_data: List[Tuple[pd.Series, str]]):
        """
        Entraîne sur des exemples :
        [(series1, 'diameter'), (series2, 'species'), ...]
        """

        X = []
        y = []

        for series, label in training_data:
            features = self.extract_features(series)
            X.append(features)
            y.append(label)

        self.model.fit(X, y)
        self.is_trained = True

    def predict(self, series: pd.Series) -> Tuple[str, float]:
        """Prédit le type avec confiance"""

        if not self.is_trained:
            # Fallback sur règles si pas entraîné
            return self._rule_based_fallback(series)

        features = self.extract_features(series).reshape(1, -1)

        # Prédiction avec probabilité
        prediction = self.model.predict(features)[0]
        proba = self.model.predict_proba(features)[0].max()

        return prediction, proba

    def _rule_based_fallback(self, series: pd.Series) -> Tuple[str, float]:
        """Fallback sur analyse statistique simple"""

        if pd.api.types.is_numeric_dtype(series):
            clean = series.dropna()

            # Heuristiques simples basées sur les ranges
            if 5 < clean.mean() < 200 and clean.max() < 500:
                return 'diameter', 0.6
            elif 1 < clean.mean() < 50 and clean.max() < 100:
                return 'height', 0.5
            elif 0.1 < clean.mean() < 1.5 and clean.max() < 2:
                return 'wood_density', 0.7

        return 'unknown', 0.3
```

## Configuration Finale Générée

```python
class IntelligentConfigGenerator:
    """
    Génère la config basée sur l'analyse des VALEURS
    """

    def __init__(self):
        self.detector = MLColumnClassifier()
        self.semantic_detector = SemanticColumnDetector()

    def generate_config(self, df: pd.DataFrame) -> Dict:
        """
        Analyse chaque colonne et génère la config appropriée
        """

        config = {'transform': [], 'export': []}

        for col in df.columns:
            # Détection multi-stratégies
            ml_type, ml_conf = self.detector.predict(df[col])
            sem_type = self.semantic_detector.detect_semantic_type(col, df[col].head(10))

            # Consensus ou meilleure confiance
            detected_type = ml_type if ml_conf > 0.7 else sem_type

            # Génère la config selon le type détecté
            if detected_type == 'diameter':
                config['transform'].append({
                    'plugin': 'binned_distribution',
                    'params': {
                        'field': col,  # Peu importe le nom !
                        'bins': self._calculate_optimal_bins(df[col]),
                        'include_percentages': True
                    }
                })
                config['export'].append({
                    'plugin': 'bar_plot',
                    'source': f"{col}_distribution"
                })

            elif detected_type in ['species', 'genus', 'family']:
                if 'taxonomy_extraction' not in config:
                    config['transform'].append({
                        'plugin': 'taxonomy_extractor',
                        'params': {
                            'hierarchy': self._detect_hierarchy_columns(df)
                        }
                    })

        return config

    def _calculate_optimal_bins(self, series: pd.Series) -> List[float]:
        """Calcule des bins optimaux basés sur la distribution réelle"""

        # Utilise les quantiles pour bins adaptatifs
        quantiles = [0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 1.0]
        bins = series.quantile(quantiles).round().unique().tolist()

        return sorted(bins)
```

## Conclusion : C'est Faisable !

**Sans maintenir de listes de synonymes**, on peut :

1. **Analyser les valeurs** : Un diamètre a une signature statistique reconnaissable
2. **Utiliser le contexte** : Si on voit des valeurs 10-200 + autres colonnes biologiques = probablement DBH
3. **Apprendre des patterns** : Un petit ML apprend vite les signatures typiques

**Approche recommandée** :
- **Phase 1** : Détection par valeurs + heuristiques (2 semaines)
- **Phase 2** : Petit ML (Random Forest) qui apprend (1 mois)
- **Phase 3** : Embeddings sémantiques si besoin (optionnel)

Les utilisateurs peuvent nommer leurs colonnes `toto`, `truc`, `X1` - on s'en fiche ! On détecte par les **valeurs et patterns statistiques**.
