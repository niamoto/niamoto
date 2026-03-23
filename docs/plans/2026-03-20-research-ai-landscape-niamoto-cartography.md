---
title: "Cartographie IA 2025-2026 : technologies applicables au pipeline Niamoto"
type: research
date: 2026-03-20
reviewed: 2026-03-20
---

# Cartographie IA 2025-2026 : technologies applicables au pipeline Niamoto

Analyse exhaustive des technologies IA (HuggingFace, Ollama, ONNX, etc.) pertinentes pour une plateforme de donnees ecologiques. Chaque section couvre ce que la technologie fait, si elle tourne hors-ligne, sa taille, sa maturite, et comment elle pourrait concretement aider Niamoto.

**Contexte** : Niamoto utilise actuellement scikit-learn (TF-IDF + LogReg + HistGBT) pour la detection de colonnes, avec un macro-F1 de 0.97 en fusion sur 2231 colonnes labelisees. Le pipeline complet : Import CSV --> Profiling --> Detection ML --> Suggestion transformers/widgets --> Transform --> Export pages HTML.

**Contraintes Niamoto** :
- Offline-first (app desktop Tauri)
- Modeles < 100 MB idealement, < 500 MB acceptable
- Inference < 500ms par colonne
- Pas de GPU obligatoire
- Solo developer, stack Python/scikit-learn

---

## 1. Column/Schema Understanding

### 1.1 Ce que Niamoto fait deja

Le systeme actuel atteint 0.97 de macro-F1 sur 61 concepts avec un pipeline 3 branches :
- **Header** : TF-IDF char n-grams (2-5) + LogisticRegression L1 --> 0.77 macro-F1
- **Values** : 37 features statistiques + HistGradientBoosting --> 0.35 macro-F1
- **Fusion** : LogReg calibree sur les probas des 2 branches --> 0.97 macro-F1

La performance est excellente pour un systeme leger. La question est : que pourrait-on ameliorer, et a quel cout ?

### 1.2 ColBERT / ModernColBERT / Reason-ModernColBERT (LightOn AI)

**Ce que c'est** : ColBERT est un modele de recherche semantique qui utilise le "late interaction" -- au lieu de compresser tout un texte en un seul vecteur, il compare chaque token individuellement (operateur MaxSim). ModernColBERT est la version mise a jour (base ModernBERT d'Alibaba-NLP). Reason-ModernColBERT est fine-tune pour la recherche avec raisonnement.

| Critere | Valeur |
|---------|--------|
| Taille | ~560 MB (base), embeddings 128 dimensions |
| Offline | Oui (poids telechargeables) |
| GPU requis | Non, mais CPU lent |
| Maturite | Production pour la recherche documentaire |

**Pertinence pour Niamoto** : **Faible**. Ces modeles sont concus pour la recherche de documents (retrouver un paragraphe pertinent dans un corpus de millions). Pour du matching de noms de colonnes (1-3 mots), c'est un canon pour tuer une mouche. Le TF-IDF char n-grams + alias YAML couvre deja 95% des cas avec 100x moins de ressources.

**Verdict** : Pas pertinent. Le vocabulaire de colonnes ecologiques est ferme (~25 concepts). Le fuzzy matching + alias registry est plus adapte que la recherche semantique dense.

- HuggingFace : https://huggingface.co/lightonai/Reason-ModernColBERT
- HuggingFace : https://huggingface.co/lightonai/GTE-ModernColBERT-v1

### 1.3 Table Transformers (TAPAS, TaPEx, TableFormer, TURL)

**Ce que c'est** :
- **TAPAS** (Google, 2020) : BERT modifie pour repondre a des questions sur des tableaux. Encode la structure tabulaire (colonnes, lignes) avec des position embeddings speciaux.
- **TaPEx** (Microsoft, 2022) : Simule un executeur SQL neural, pre-entraine sur des paires (question, resultat SQL).
- **TableFormer** (IBM/Google, 2022) : Ajoute des "structural attention biases" pour encoder les relations ligne-colonne.
- **TURL** (2021) : Pre-entraine des representations sur des tables relationnelles du web, fine-tunable pour annotation de colonnes.

| Critere | TAPAS | TaPEx | TableFormer | TURL |
|---------|-------|-------|-------------|------|
| Taille | ~440 MB | ~890 MB | ~440 MB | ~440 MB |
| Tache principale | Question-answering | Table QA | Table encoding | Column annotation, entity linking |
| GPU requis | Recommande | Oui | Recommande | Recommande |
| Donnees pre-train | Wikipedia tables | SQL pairs | Tables + texte | Tables relationnelles du web |

**Pertinence pour Niamoto** :
- **TAPAS/TaPEx** : **Faible**. Ces modeles repondent a des questions sur le contenu d'une table ("Quel est le DBH moyen ?"). Niamoto n'a pas ce besoin pour la detection -- le text-to-SQL (section 4) couvre mieux ce cas.
- **TURL** : **Moyenne**. TURL peut annoter des colonnes avec des types semantiques. Mais il necessite PyTorch, ~440 MB, et son pre-entrainement est sur des tables web (Wikipedia), pas ecologiques. La performance sur un domaine de niche sans fine-tuning serait mediocre.
- **TableFormer** : **Faible**. Modele d'encoding, utile si on avait un pipeline downstream complexe.

**Verdict** : Aucun n'est pratique pour Niamoto aujourd'hui. Le pipeline scikit-learn existant les bat en termes de ratio performance/cout. A reconsiderer si le gold set depasse 10k colonnes et qu'on veut un modele unique au lieu de 3 branches.

- HuggingFace : https://huggingface.co/docs/transformers/model_doc/tapas
- Paper survey : https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00544

### 1.4 Sentence Transformers pour noms de colonnes

**Ce que c'est** : Des modeles qui convertissent du texte en vecteurs denses (embeddings) pour mesurer la similarite semantique. Contrairement au TF-IDF qui compare des caracteres, les embeddings capturent le sens ("hauteur" est proche de "height" meme si les caracteres sont differents).

**Modeles cles** :

| Modele | Params | Taille | Dimensions | Multilingual | Offline |
|--------|--------|--------|------------|-------------|---------|
| all-MiniLM-L6-v2 | 22M | ~80 MB | 384 | Non (EN) | Oui |
| E5-small-v2 | 33M | ~130 MB | 384 | Non (EN) | Oui |
| GTE-small | 33M | ~130 MB | 384 | Non (EN) | Oui |
| **EmbeddingGemma-300M** | 308M | ~200 MB (quantifie) | 768 (MRL: 128-768) | **Oui (100+ langues)** | **Oui (ONNX)** |
| **Qwen3-Embedding-0.6B** | 600M | ~1.2 GB (Q4) | flexible (32-4096) | **Oui (100+ langues)** | **Oui (Ollama)** |
| nomic-embed-text-v2 | ~137M | ~274 MB | 768 | Oui (~100 langues) | Oui (Ollama) |

**Pertinence pour Niamoto** :

Le **point faible actuel** du pipeline est le matching multilingue au-dela des racines latines. Le TF-IDF char n-grams capte bien `diametre`/`diametro`/`diameter` (racines partagees), mais echoue sur `hauteur` vs `height` ou `profondeur` vs `depth` (aucun n-gramme commun). L'alias registry YAML compense, mais c'est un effort de maintenance continu.

**EmbeddingGemma-300M** est le candidat le plus interessant :
- 308M parametres, < 200 MB RAM avec quantification
- 100+ langues, dont les langues de colonnes ecologiques (FR, ES, PT, DE, ID)
- ONNX Runtime natif -- pas besoin de PyTorch
- MTEB : meilleur modele open multilingue sous 500M
- Inference < 15ms pour 256 tokens sur EdgeTPU, rapide sur CPU aussi
- Matryoshka : peut reduire les embeddings a 128 dimensions pour la vitesse

**Comment l'integrer** : Pas en remplacement du TF-IDF, mais en complement pour le 5% de colonnes ou l'alias registry echoue. Embedder les 25 concepts + leurs alias = ~500 vecteurs de reference. Pour une colonne inconnue, calculer le cosinus avec les references. Si le score > seuil, ajouter un signal supplementaire a la fusion.

```python
# Pseudo-code : embedding comme feature supplementaire pour le header model
from fastembed import TextEmbedding

model = TextEmbedding("google/embeddinggemma-300m")
concept_embeddings = {concept: model.embed(aliases) for concept, aliases in registry.items()}

def embedding_feature(col_name: str) -> float:
    col_vec = model.embed([col_name])[0]
    best_score = max(cosine(col_vec, ref) for ref in concept_embeddings.values())
    return best_score  # feature supplementaire pour la fusion
```

**Verdict** : **Candidat Phase 4** (optionnel). Le ratio benefice/complexite est bon pour EmbeddingGemma via FastEmbed (ONNX, pas de PyTorch). A tester quand l'alias registry atteint ses limites sur des datasets en langues non-latines.

- HuggingFace : https://huggingface.co/google/embeddinggemma-300m
- ONNX : https://huggingface.co/onnx-community/embeddinggemma-300m-ONNX
- Blog : https://developers.googleblog.com/introducing-embeddinggemma/
- FastEmbed : https://github.com/qdrant/fastembed

### 1.5 Small Language Models pour classification zero-shot

**Ce que c'est** : Des modeles de langage complets (capables de generer du texte) mais suffisamment petits pour tourner localement. L'idee est de leur demander "Cette colonne avec les valeurs [12.5, 34.2, 8.1] et le nom 'dbh' est de quel type ?" sans entrainement prealable.

| Modele | Params | Taille Q4 | Ollama | Classification | Multilingual |
|--------|--------|-----------|--------|---------------|-------------|
| Gemma-3-270M | 270M | 529 MB | Oui | Basique | Limitee |
| SmolLM2-135M | 135M | ~270 MB | Oui | Faible | Non |
| SmolLM2-360M | 360M | ~720 MB | Oui | Correct | Non |
| **Qwen3-0.6B** | 600M | **~1.2 GB** | **Oui** | **Correct** | **Oui (100+ langues)** |
| Phi-3-mini | 3.8B | ~2.3 GB | Oui | Bon | Limitee |
| Gemma-3-1B | 1B | ~2 GB | Oui | Bon | Oui |
| Qwen3-4B | 4B | ~2.8 GB | Oui | Tres bon | Oui |

**Resultats de benchmarks** (distillabs.ai, 2026) :
- Sur 4 taches de classification (TREC, Banking77, Ecommerce, Mental Health), Qwen3-4B fine-tune atteint : TREC 0.93, Banking77 0.89, Ecommerce 0.90, Mental Health 0.82
- Les modeles sous 1B (SmolLM2, Gemma-270M, Qwen3-0.6B) performent nettement moins bien out-of-the-box mais montrent les "plus grands gains au fine-tuning"
- Qwen3-4B domine le classement sub-10B

**Pertinence pour Niamoto** :

Le zero-shot avec un SLM < 1B pour la detection de colonnes a 3 problemes :
1. **Latence** : meme Qwen3-0.6B prend ~500ms-2s par colonne sur CPU, vs ~2ms pour le pipeline scikit-learn. Pour 50 colonnes, c'est 25-100s vs 0.1s.
2. **Precision** : sans fine-tuning sur le domaine ecologique, la precision sera inferieure au pipeline entraine sur 2231 exemples labelises.
3. **Determinisme** : un LLM peut donner des reponses differentes a chaque appel.

**Ou ils sont utiles** : pour les suggestions cross-colonnes (Tier M2 du roadmap), le LLM apporte une valeur que les regles ne peuvent pas capturer ("les colonnes flower_month et fruit_month forment un calendrier phenologique").

**Verdict** : **Qwen3-0.6B via Ollama pour le Tier M2 uniquement** (suggestions cross-colonnes, ~5% de l'impact). Pas pour la detection de base ou scikit-learn domine en vitesse et precision.

- HuggingFace : https://huggingface.co/Qwen/Qwen3-0.6B
- Benchmark : https://www.distillabs.ai/blog/we-benchmarked-12-small-language-models-across-8-tasks-to-find-the-best-base-model-for-fine-tuning
- Guide 2026 : https://localaimaster.com/blog/small-language-models-guide-2026

### 1.6 Magneto : le pattern SLM + LLM pour le schema matching

**Ce que c'est** : Un framework (VLDB 2025, NYU/VIDA) qui combine un petit modele (SLM) pour le filtrage rapide avec un grand modele (LLM) pour le reranking precis. L'architecture est en 2 phases :
1. **Retrieval** : un SLM fine-tune genere des candidats rapidement (offline, pas cher)
2. **Reranking** : un LLM (GPT-4, Claude) reordonne les top-N candidats (en ligne, cher mais peu d'appels)

L'innovation cle : ils utilisent le LLM pour generer les donnees d'entrainement du SLM, evitant l'annotation manuelle.

| Critere | Valeur |
|---------|--------|
| Taille SLM | Variable (n'importe quel embedding model) |
| LLM requis | Oui, pour le reranking (et optionnel: generation training data) |
| Maturite | Paper VLDB 2025, code open source |
| Benchmark | Inclut des datasets biomedicaux |

**Pertinence pour Niamoto** : **Interessante mais prematuree**. Le pattern est exactement ce que le roadmap Niamoto prevoit deja (Tier S1 local + Tier M2 LLM optionnel). La difference : Niamoto utilise TF-IDF + HistGBT au lieu d'un SLM fine-tune pour le retrieval. Si les embeddings (section 1.4) s'averent necessaires, Magneto fournit un blueprint valide.

**A surveiller** : la methode de generation de training data par LLM pourrait aider a enrichir le gold set Niamoto sans annotation manuelle.

- Paper : https://arxiv.org/abs/2412.08194
- Code : https://github.com/VIDA-NYU/magneto-matcher
- VLDB 2025 : https://www.vldb.org/pvldb/vol18/p2681-freire.pdf

### 1.7 RACOON : RAG + Knowledge Graph pour l'annotation de colonnes

**Ce que c'est** : Un framework (NeurIPS 2024) qui ameliore l'annotation de colonnes par LLM en injectant du contexte provenant d'un Knowledge Graph. Pour chaque colonne, RACOON cherche les entites mentionnees dans les cellules dans un KG (Wikidata, DBpedia), puis compresse ce contexte pour le prompt LLM.

| Critere | Valeur |
|---------|--------|
| Taille | Depend du LLM utilise |
| Offline | Non (necessite KG + LLM) |
| Gain | +0.21 micro-F1 vs LLM vanilla |
| Maturite | Paper NeurIPS 2024 |

**Pertinence pour Niamoto** : **Faible a court terme**. L'approche est elegante mais necessite un KG external et un LLM. Pour Niamoto offline-first, c'est trop lourd. Le concept sous-jacent (enrichir le contexte avec des connaissances externes) est deja couvert par l'alias registry YAML + les features biologiques (binomial_score, family_suffix).

- arXiv : https://arxiv.org/abs/2409.14556

### 1.8 FastEmbed (Qdrant) : embeddings legers sans PyTorch

**Ce que c'est** : Une librairie Python de Qdrant qui fait tourner des modeles d'embedding via ONNX Runtime au lieu de PyTorch. L'avantage : pas de dependance lourde (~50 MB au lieu de 2 GB pour torch), rapide sur CPU, modeles quantifies.

| Critere | Valeur |
|---------|--------|
| Installation | `pip install fastembed` |
| Taille | ~50-200 MB selon le modele |
| GPU requis | Non, optimise CPU |
| Latence | < 1ms par embedding (court texte) |
| Modeles supportes | all-MiniLM, BGE, E5, Flag Embedding, etc. |

**Pertinence pour Niamoto** : **Forte si on adopte les embeddings** (section 1.4). FastEmbed est la bonne interface pour integrer EmbeddingGemma-300M sans importer PyTorch. L'empreinte est compatible avec les contraintes desktop de Niamoto.

```
pip install fastembed  # ~50 MB, pas de torch
```

- GitHub : https://github.com/qdrant/fastembed
- Docs : https://qdrant.github.io/fastembed/

---

## 2. Auto-Visualization / Chart Suggestion

### 2.1 LIDA (Microsoft Research)

**Ce que c'est** : Un outil open source qui genere automatiquement des visualisations a partir d'un dataset. Architecture en 4 modules :
1. **Summarizer** : resume le dataset en langage naturel compact
2. **Goal Explorer** : enumere des objectifs de visualisation ("montrer la distribution des DBH", "correler height et DBH")
3. **VisGenerator** : genere, raffine et execute du code de visualisation
4. **Infographer** : stylise les graphiques

| Critere | Valeur |
|---------|--------|
| Taille | Librairie Python, depend du LLM |
| LLM requis | **Oui, obligatoire** pour chaque generation |
| Offline | Non sans modele local (possible via HuggingFace/vLLM) |
| Librairies de viz | Matplotlib, Seaborn, Altair, D3 (grammar-agnostic) |
| Maturite | ACL 2023, open source, maintenu |

**Pertinence pour Niamoto** :

Le **Goal Explorer** de LIDA fait exactement ce que le Tier M2 du roadmap Niamoto veut faire : suggerer des visualisations semantiquement pertinentes a partir d'un schema. Mais la dependance au LLM pour chaque generation est un deal-breaker pour le mode offline.

**Ce qu'on peut emprunter** : la logique du Summarizer (resumer le schema d'un dataset en ~200 tokens) est utile comme prompt pour le LLM optionnel (Tier M2). Le pattern "schema --> goals --> code" est validee academiquement.

**Ce qu'on ne peut pas utiliser directement** : LIDA genere du matplotlib/seaborn, pas du Plotly. Niamoto a besoin de specs JSON pour ses widgets, pas de code Python.

**Verdict** : **Pattern a imiter, pas librairie a integrer**. Le Tier M2 (LLM optionnel) de Niamoto fait la meme chose mais genere des paires (transformer, widget) au lieu de code matplotlib.

- GitHub : https://github.com/microsoft/lida
- Paper : https://aclanthology.org/2023.acl-demo.11/
- Site : https://microsoft.github.io/lida/

### 2.2 Data Formulator (Microsoft Research)

**Ce que c'est** : Un outil interactif qui combine UI drag-and-drop + langage naturel pour creer des visualisations. 4 niveaux :
1. Drag-and-drop pur
2. Description en langage naturel
3. Recommandations par agent IA
4. Exploration automatique par agent

| Critere | Valeur |
|---------|--------|
| Backend | DuckDB (depuis v0.2, avril 2025) |
| LLM | OpenAI, Azure, **Ollama**, Anthropic (via LiteLLM) |
| Offline | **Possible avec Ollama** |
| Open source | Oui (MIT) |
| Format de sortie | Vega-Lite |

**Pertinence pour Niamoto** : **Interessante comme inspiration UX**. Data Formulator montre comment combiner selection manuelle + suggestion IA pour la creation de visualisations. Son integration DuckDB + Ollama est exactement le stack que Niamoto pourrait utiliser.

**Mais** : c'est une application standalone, pas une librairie embedable. L'integrer dans le GUI Niamoto demanderait une reecriture complete.

**Verdict** : **Reference UX et architecturale**, pas integration directe. Le pattern DuckDB + Ollama + Vega-Lite valide les choix du roadmap.

- GitHub : https://github.com/microsoft/data-formulator

### 2.3 Data2Vis et VizML

**Ce que c'est** :
- **Data2Vis** (2019) : modele sequence-a-sequence (LSTM) qui convertit des specs JSON de donnees en specs Vega-Lite.
- **VizML** (CHI 2019) : reseau neuronal entraine sur 2.3M de visualisations Plotly pour predire les types de charts.

| Critere | Data2Vis | VizML |
|---------|----------|-------|
| Annee | 2019 | 2019 |
| Modele | LSTM seq2seq | DNN |
| Sortie | Vega-Lite specs | Design choices (chart type, axes) |
| Maturite | Recherche, code dispo | Recherche, dataset dispo |

**Pertinence pour Niamoto** : **Depasses**. Les approches basees sur LLM (LIDA, Data Formulator) les remplacent en 2025-2026. Le concept sous-jacent (predire le type de chart a partir du schema) est cependant valide et se retrouve dans le Dataset Pattern Detector de Niamoto (approche par regles).

**Verdict** : Historiquement interessant, mais remplace par les approches LLM modernes.

- Data2Vis : https://github.com/victordibia/data2vis
- VizML : https://dl.acm.org/doi/fullHtml/10.1145/3290605.3300358

### 2.4 VegaFusion

**Ce que c'est** : Acceleration serveur pour les visualisations Vega/Vega-Lite. Fait le gros du calcul cote serveur (en Rust/DuckDB) au lieu du navigateur, puis envoie seulement les donnees necessaires au frontend.

| Critere | Valeur |
|---------|--------|
| Backend | Rust + DuckDB (natif) |
| Frontend | Vega-Lite (via Altair en Python) |
| Maturite | v2.0 (nov 2024), production |
| GPU requis | Non |
| Taille | Librairie Rust/Python |

**Pertinence pour Niamoto** : **Faible**. Niamoto utilise Plotly, pas Vega-Lite. VegaFusion serait pertinent si Niamoto migrerait vers Vega-Lite pour les visualisations. Le concept d'acceleration serveur est neanmoins utile -- Niamoto le fait deja via DuckDB cote backend.

- GitHub : https://github.com/vega/vegafusion
- v2.0 : https://vegafusion.io/posts/2024/2024-11-13_Release_2.0.0.html

### 2.5 Approche recommandee pour Niamoto

Le systeme de suggestion de Niamoto est deja bien pense (Tier S1 affordance matching + Tier M1 dataset patterns). Les technologies de type LIDA/Data Formulator ajouteraient de la valeur uniquement via le **Tier M2 (LLM optionnel)** pour les suggestions cross-colonnes.

**Recapitulatif** :

| Tier | Methode | Technologie | Couverture |
|------|---------|------------|-----------|
| S1 | Affordance matching | Regles Python pures | ~60% des suggestions |
| M1 | Dataset Pattern Detector | Regles + taxonomie concepts | ~10% des suggestions |
| **M2** | **LLM optionnel** | **Qwen3-0.6B via Ollama** | **~5% des suggestions** |
| S2 | Recipe ranker | scikit-learn (apres feedback) | Reranking des 3 tiers |

La litterature 2026 (survey de Rollwagen & Manssour) confirme que les approches hybrides regles + LLM surpassent les approches purement ML ou purement LLM.

- Survey 2026 : https://journals.sagepub.com/doi/10.1177/14738716251409351

---

## 3. Data Profiling & Anomaly Detection

### 3.1 Outils automatises de data quality

| Outil | Ce qu'il fait | Taille | Offline | Pertinence Niamoto |
|-------|--------------|--------|---------|-------------------|
| **ydata-profiling** | Genere un rapport HTML interactif sur un DataFrame (distribution, correlations, alertes) | ~20 MB | Oui | **Forte** pour la phase profiling |
| **Great Expectations** (GX) | Framework de tests de qualite des donnees : definir des attentes ("cette colonne a des valeurs entre 0 et 500") et les valider automatiquement | ~50 MB | Oui | **Moyenne** -- le systeme d'anomaly rules Niamoto fait deja ca mais en plus leger |
| **Deepchecks** | Suite de validation ML + donnees avec drift detection, outlier detection (Isolation Forest), visualisations | ~100 MB | Oui | **Faible** -- trop oriente ML ops, overkill pour Niamoto |
| **Soda Core** | Tests de qualite via SQL-like assertions | ~30 MB | Oui | **Moyenne** -- integrable avec DuckDB |

### 3.2 Anomaly detection ML sur donnees ecologiques

**Le choix actuel de Niamoto est le bon** : des regles metier explicites (DBH < 500 cm, latitude dans [-90, 90], pH dans [0, 14]) avec un fallback IQR x 3 pour les colonnes sans regle connue.

**Pourquoi pas d'Isolation Forest** :
- Les outliers ecologiques sont souvent des erreurs de saisie (500 au lieu de 50) ou des valeurs legitimes extremes (un arbre de 40m de haut en foret tropicale est normal)
- Un ecologue comprend "DBH > 500 cm est suspect" mais pas "score d'anomalie 0.87 selon Isolation Forest"
- Les regles metier sont plus fiables, plus explicables, et ne necessitent pas d'entrainement

**Ou le ML ajouterait de la valeur** : detection d'anomalies **multivariees** ("un arbre de 5 cm de DBH avec une hauteur de 40 m est suspect" -- les deux valeurs sont valides individuellement mais la combinaison est invraisemblable). Cela necessiterait un modele entraine sur des relations allometriques connues.

**Approche realiste** : un `IsolationForest` ou `LocalOutlierFactor` de scikit-learn sur les paires de mesures (DBH, height) par grande famille taxonomique. Pas besoin de modeles externes.

```python
# Anomalie multivariee simple -- 100% scikit-learn, pas de dependance
from sklearn.ensemble import IsolationForest

def detect_multivariate_anomalies(df, measurement_cols):
    X = df[measurement_cols].dropna()
    if len(X) < 50:
        return pd.Series(False, index=df.index)
    clf = IsolationForest(contamination=0.05, random_state=42)
    preds = clf.fit_predict(X)
    return pd.Series(preds == -1, index=X.index).reindex(df.index, fill_value=False)
```

### 3.3 "Un DBH de 500 cm est suspect pour cette espece" -- peut-on apprendre ca ?

Oui, mais pas avec un modele generique. Il faudrait :
1. Un dataset de reference (DBH max par espece/genre/famille) -- extractible des donnees existantes
2. Une table de lookup : si `DBH > max_known_for_species * 1.5` --> suspect
3. Pas besoin de ML -- une simple table de reference suffit

**L'enrichissement par GBIF** : les donnees GBIF contiennent des millions de mesures par espece. Un script pourrait extraire les percentiles 99 par espece et creer un fichier de reference.

**Verdict** : Les anomaly rules actuelles + un enrichissement par table de reference sont suffisants. Pas besoin de modeles externes.

- Great Expectations : https://github.com/great-expectations/great_expectations
- ydata-profiling : https://github.com/ydataai/ydata-profiling
- Deepchecks : https://www.productowl.io/mlops/deepchecks
- Landscape 2026 : https://datakitchen.io/the-2026-open-source-data-quality-and-data-observability-landscape/

---

## 4. Natural Language to SQL/DuckDB

### 4.1 DuckDB-NSQL

**Ce que c'est** : Un modele 7B specialement fine-tune pour generer du SQL DuckDB a partir de langage naturel. Base sur Llama-2 7B, entraine sur 200k paires text-to-SQL generees synthetiquement a partir de la doc DuckDB v0.9.2.

| Critere | Valeur |
|---------|--------|
| Taille | 7B params, ~4 GB quantifie |
| Offline | Oui (via llama.cpp ou Ollama) |
| GPU requis | Non mais recommande (lent sur CPU) |
| Specificites | Gere les struct columns DuckDB, ALTER TABLE, etc. |
| Maturite | Production (MotherDuck) |

**Pertinence pour Niamoto** : **Forte pour Phase 5+**. Un botaniste pourrait demander "montre-moi le DBH moyen par famille" et obtenir la requete DuckDB :

```sql
SELECT family, AVG(dbh) as avg_dbh
FROM occurrences
GROUP BY family
ORDER BY avg_dbh DESC
```

**Problemes pratiques** :
- 4 GB pour un modele est au-dela de la contrainte < 500 MB pour la distribution
- Sur CPU (pas de GPU), latence de 5-30s par requete
- Les requetes complexes (ratios, z-scores) echouent souvent avec les petits modeles
- Le risque principal : **les requetes qui s'executent mais renvoient des resultats faux** (silent failures)

**Alternative plus legere** : utiliser un LLM generique (Qwen3-4B) avec un prompt contenant le schema DuckDB, au lieu d'un modele specialise. La qualite est comparable pour des requetes simples.

- HuggingFace : https://huggingface.co/motherduckdb/DuckDB-NSQL-7B-v0.1
- Ollama : https://ollama.com/library/duckdb-nsql
- GitHub : https://github.com/NumbersStationAI/DuckDB-NSQL

### 4.2 SQLCoder (Defog)

**Ce que c'est** : Famille de modeles fine-tunes pour le text-to-SQL generique.

| Variante | Params | Precision (benchmark) | GPU requis |
|----------|--------|----------------------|-----------|
| SQLCoder-7b | 7B | ~85% | Non (lent CPU) |
| SQLCoder-34b | 34B | ~92% | 20 GB+ VRAM |
| SQLCoder-70b | 70B | ~96% | 4x A10 |

**Pertinence pour Niamoto** : Le 7B est comparable a DuckDB-NSQL mais generique (pas specifique DuckDB). Pour Niamoto, DuckDB-NSQL est preferable car il gere les specificites DuckDB.

- HuggingFace : https://huggingface.co/defog/sqlcoder

### 4.3 Benchmark small models text-to-SQL (2025)

Un benchmark non-scientifique (datamonkeysite.com, mai 2025) a teste Qwen3 4B/8B/14B sur du text-to-SQL :
- **Qwen3-4B** : reussit les requetes simples (total, moyennes) en < 1 min, echoue sur les complexes
- **Qwen3-8B** : le plus fiable, genere du SQL propre avec CTE, reussit les requetes statistiques
- **Qwen3-14B** : paradoxalement moins bon que le 8B sur certaines taches (sur-ingenierie)
- **Meilleure surprise** : les modeles convertissent intelligemment les valeurs ("USA" --> "UNITED STATES")
- **Pire risque** : les requetes qui s'executent correctement mais renvoient des resultats faux

### 4.4 Approche recommandee pour Niamoto

| Timing | Approche | Technologie | Experience utilisateur |
|--------|---------|------------|---------------------|
| **Court terme** | Templates SQL parametres | Python pur | Menu dropdown : "DBH moyen par famille", "Distribution par espece" |
| **Moyen terme** | LLM local + schema | Qwen3-4B via Ollama | Champ texte libre, generation SQL, preview avant execution |
| **Optionnel** | DuckDB-NSQL | duckdb-nsql-7b via Ollama | Specialiste DuckDB, meilleur pour requetes complexes |

**Le court terme est suffisant** pour la v1. La plupart des questions ecologiques se reduisent a une dizaine de templates SQL parametres. Le text-to-SQL LLM est un "nice to have" pour les utilisateurs avances.

- Benchmark : https://datamonkeysite.com/2025/05/05/a-non-scientific-benchmark-of-text-to-sql-using-small-models/
- Guide complet : https://builder.ai2sql.io/blog/text-to-sql-complete-guide
- text2sql small : https://github.com/Anindyadeep/text2sql

---

## 5. Ecological / Biodiversity AI

### 5.1 BioCLIP : Vision Foundation Model for the Tree of Life

**Ce que c'est** : Un modele CLIP (ViT-B/16) entraine sur **TreeOfLife-10M** -- 10 millions d'images de 450k+ especes provenant d'iNaturalist, BIOSCAN-1M et Encyclopedia of Life. Meilleur Paper etudiant CVPR 2024.

| Critere | Valeur |
|---------|--------|
| Taille | ~350 MB (ViT-B/16) |
| Offline | Oui |
| GPU requis | Recommande pour l'inference d'images |
| Specialite | Classification zero-shot d'especes par image |
| Taxonomie | Representations hierarchiques (kingdom --> species) |

**Pertinence pour Niamoto** : **Nulle directement** (Niamoto travaille sur des CSV, pas des images). Mais le concept de representation hierarchique de la taxonomie est interessant : BioCLIP apprend des embeddings ou les especes proches dans l'arbre taxonomique sont proches en espace vectoriel.

**Application indirecte** : si Niamoto acceptait un jour des donnees photographiques d'inventaires (photos de specimens), BioCLIP pourrait identifier les especes automatiquement.

- Paper : https://arxiv.org/abs/2311.18803
- GitHub : https://github.com/Imageomics/bioclip
- Site : https://imageomics.github.io/bioclip/

### 5.2 PlantNet et iNaturalist

**PlantNet** : application d'identification de plantes par photo, avec 6M d'observations publiees sur GBIF. Le modele de vision n'est pas directement accessible comme librairie Python.

**iNaturalist** : 110M d'observations research-grade sur GBIF (3eme plus gros contributeur). Le modele de vision v2.1 (fev 2023) est disponible via l'API iNaturalist mais pas en local.

**Pertinence pour Niamoto** : **Aucune pour le pipeline actuel** (CSV, pas images). Pertinent si Niamoto etendait ses capacites a l'enrichissement de donnees par identification photographique.

### 5.3 Taxonomic Name Resolution via embeddings

**Etat de l'art** : GBIF utilise actuellement du fuzzy matching canonique pour la resolution de noms taxonomiques (excluant les autorites, puis scoring par taxonomie/rang/statut). Pas d'approche par embeddings connue en production.

**Approche possible** : embedder les noms taxonomiques (binomiaux latins) et chercher les plus proches voisins pour la resolution d'homonymes et de synonymes. Le vocabulaire taxonomique est fortement structure (genre + epithete), donc le TF-IDF char n-grams fonctionne deja bien.

**Pertinence pour Niamoto** : **Faible**. Le fuzzy matching de GBIF (via l'API `/species/match`) est suffisant. Reimplementer localement via embeddings n'apporterait pas de gain significatif.

- GBIF species matching : https://www.gbif.org/tools/species-lookup
- GBIF backbone : https://www.gbif.org/dataset/d7dddbf4-2cf0-4f39-9b2a-bb099caae36c

### 5.4 Biodiversity informatics AI

Pas de modeles specifiquement entraines sur les schemas d'inventaires ecologiques ou Darwin Core en mars 2026. Le plus proche est Magneto (section 1.6) qui inclut des benchmarks biomedicaux.

**Ce qui existe** :
- Des datasets d'entrainement (GBIF, iNaturalist)
- Des standards (Darwin Core, ABCD)
- Des outils de fuzzy matching (pygbif, GBIF API)
- BioCLIP pour les images

**Ce qui manque** : un modele "Sherlock for ecology" entraine sur des milliers de datasets ecologiques labelises. C'est exactement ce que Niamoto est en train de construire avec son gold set de 2231 colonnes.

**Verdict** : Niamoto est a la pointe pour son domaine. Il n'existe pas de modele pre-entraine specialise en biodiversity informatics pour l'annotation de schemas. Le gold set de Niamoto pourrait devenir une contribution a la communaute.

---

## 6. Small/Local Models vs API Models

### 6.1 Realisme des modeles sub-1B

| Tache | Sub-1B (local) | 1-4B (local) | 7B+ (local) | API (Claude/GPT-4) |
|-------|----------------|--------------|-------------|-------------------|
| Classification de colonnes | **Inferieur au pipeline scikit-learn actuel** | Comparable | Superieur mais trop lent | Bien meilleur mais en ligne |
| Text-to-SQL simple | Faible | Correct | Bon | Excellent |
| Suggestions cross-colonnes | Faible | **Correct** (Qwen3-0.6B suffisant) | Bon | Excellent |
| Resume de donnees | Faible | Correct | Bon | Excellent |
| Anomaly detection | Non pertinent (regles mieux) | Non pertinent | Non pertinent | Non pertinent |

**Conclusion** : pour les taches de classification structuree (colonnes, anomalies), scikit-learn bat tous les LLM locaux en vitesse et precision. Les LLM locaux brillent pour les taches de generation (texte, SQL, suggestions semantiques).

### 6.2 Ollama : ecosysteme pratique

Ollama est le standard de facto pour les LLM locaux en 2026. Installation en une commande, modeles telechargeable via `ollama pull`.

**Modeles recommandes pour Niamoto** :

| Modele | Taille | RAM | Usage Niamoto |
|--------|--------|-----|---------------|
| qwen3:0.6b | ~1.2 GB | 4 GB | Suggestions cross-colonnes |
| qwen3-embedding:0.6b | ~1.2 GB | 4 GB | Embeddings multilingues |
| qwen3:4b | ~2.8 GB | 8 GB | Text-to-SQL, resumes |
| all-minilm:l6-v2 | ~45 MB | 1 GB | Embeddings legers |
| nomic-embed-text | ~274 MB | 2 GB | Embeddings multilingues |

**Integration Niamoto** : Ollama est un process externe. L'app desktop pourrait :
1. Detecter si Ollama est installe
2. Si oui, activer les fonctions "enrichies" (suggestions LLM, text-to-SQL)
3. Si non, tout fonctionne normalement sans LLM (offline-first)

```python
import httpx

def call_ollama_or_skip(prompt: str, model: str = "qwen3:0.6b") -> str | None:
    try:
        r = httpx.post("http://localhost:11434/api/generate",
                       json={"model": model, "prompt": prompt, "stream": False},
                       timeout=30)
        return r.json()["response"]
    except (httpx.ConnectError, httpx.TimeoutException):
        return None  # Ollama pas disponible -- on continue sans
```

- Ollama : https://ollama.com/library
- Modeles : https://ollama.com/library/qwen3-embedding:0.6b

### 6.3 ONNX Runtime : modeles embarques dans l'app

**Ce que c'est** : Un runtime d'inference multi-plateforme (Microsoft) qui execute des modeles au format ONNX. Beaucoup plus leger que PyTorch (~50 MB vs ~2 GB).

| Critere | Valeur |
|---------|--------|
| Installation | `pip install onnxruntime` (~50 MB) |
| GPU | Optionnel (paquet `onnxruntime-gpu` separe) |
| Latence | Sub-milliseconde pour les petits modeles |
| Modeles | Tout modele HuggingFace exportable en ONNX |

**Pertinence pour Niamoto** : **Forte pour les embeddings**. Via FastEmbed, on peut embarquer EmbeddingGemma-300M (~200 MB quantifie) directement dans l'app sans Ollama ni PyTorch.

**Pas pertinent pour les LLM** : les modeles generatifs (Qwen3-0.6B etc.) sont trop lourds pour ONNX Runtime sur CPU. Ollama (qui utilise llama.cpp) est plus optimise pour ca.

**Stack recommande** :

| Besoin | Technologie | Dependance |
|--------|------------|-----------|
| Embeddings | FastEmbed + ONNX Runtime | ~250 MB total |
| LLM generatif | Ollama (externe, optionnel) | ~1-4 GB |
| Classification | scikit-learn (existant) | ~50 MB |

- ONNX Runtime : https://onnxruntime.ai/
- FastEmbed ONNX : https://johal.in/fastembed-onnx-lightweight-embedding-inference-2025/
- Client-side inference : https://tty4.dev/development/2026-02-26-onnxruntime-ml-on-edge/

### 6.4 Quand une API est-elle justifiee ?

| Scenario | Local | API | Recommandation |
|----------|-------|-----|---------------|
| Detection de colonnes (production) | scikit-learn | Non necessaire | **Local** |
| Enrichissement gold set (dev) | Non | Claude/GPT-4 pour labeliser | **API** (one-shot, pas en production) |
| Suggestions cross-colonnes (production) | Qwen3-0.6B via Ollama | Claude Haiku en fallback | **Local d'abord, API en fallback** |
| Text-to-SQL (futur) | Qwen3-4B via Ollama | Claude Sonnet | **Local si Ollama installe, sinon API** |
| Report generation (futur) | Qwen3-4B | Claude Sonnet | **API** (qualite du texte critique) |

**Regle d'or** : local pour tout ce qui tourne en boucle (detection, suggestions), API pour tout ce qui est ponctuel et ou la qualite du texte compte (rapports, enrichissement).

---

## 7. Embedding-based Approaches

### 7.1 Embedder les profils de colonnes

**Idee** : au lieu de classifier une colonne par ses features statistiques seules, encoder le profil complet (nom + stats + echantillon de valeurs) en un vecteur dense, et le comparer a une librairie de profils de reference.

**Comment** :
```python
profile_text = f"column: {col_name}, dtype: {dtype}, "
profile_text += f"mean: {mean:.1f}, std: {std:.1f}, "
profile_text += f"sample: {', '.join(sample[:5])}"
# ex: "column: dbh, dtype: float64, mean: 23.5, std: 12.1, sample: 12.3, 45.6, 8.9"

embedding = model.embed([profile_text])
# Comparer avec les embeddings de profils de reference
```

**Probleme** : ca melange du texte structure (nombres) avec du texte libre (nom). Les embeddings sont optimises pour le texte naturel, pas pour les distributions statistiques. Le pipeline actuel (TF-IDF pour le nom, features numeriques pour les stats) traite chaque signal dans son espace optimal.

**Verdict** : **Pas recommande**. La separation header/values/context est une meilleure architecture que l'embedding monolithique du profil.

### 7.2 RAG pour la documentation de donnees

**Idee** : indexer la documentation des datasets (data dictionaries, metadata GBIF, guides de terrain) et utiliser le RAG pour enrichir la detection.

**Comment** :
1. Embedder les data dictionaries (ex: "dbh = diameter at breast height, measured in cm at 1.3m") avec EmbeddingGemma
2. Pour une colonne inconnue, chercher les descriptions les plus proches
3. Utiliser le resultat comme contexte supplementaire pour la classification

**Pertinence pour Niamoto** : **Moyenne**. Utile si les datasets arrivent avec une documentation. Pour les CSV bruts sans metadonnees, le RAG n'a rien a chercher. Plus pertinent pour le futur enrichissement GBIF (les datasets GBIF ont souvent des metadata EML).

**Stack** : FastEmbed + un petit index vectoriel (numpy cosine suffit pour < 10k documents).

### 7.3 Semantic search sur la concept taxonomy

**Idee** : au lieu de mapper un nom de colonne vers les 61 concepts via TF-IDF, utiliser des embeddings pour capturer la proximite semantique entre concepts. "crown_diameter" est semantiquement proche de "canopy_cover" meme s'ils sont dans des categories differentes.

**Pertinence pour Niamoto** : **Faible**. La taxonomie de concepts est explicite et maintenue manuellement (61 concepts coarsened). La recherche semantique n'apporte pas de valeur quand le vocabulaire est ferme et petit.

### 7.4 Qwen3-Embedding : le meilleur embedding multilingue en mars 2026

| Variante | Params | MTEB multilingue | Dimensions | Ollama |
|----------|--------|-----------------|-----------|--------|
| Qwen3-Embedding-0.6B | 600M | Bon | Flexible (32-4096) | Oui |
| Qwen3-Embedding-4B | 4B | Tres bon | Flexible | Oui |
| Qwen3-Embedding-8B | 8B | **#1 MTEB** (70.58, juin 2025) | Flexible | Oui |

Le 0.6B est disponible via Ollama et en GGUF quantifie. C'est une alternative a EmbeddingGemma-300M avec plus de flexibilite dimensionnelle.

- HuggingFace : https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- Ollama : https://ollama.com/library/qwen3-embedding:0.6b
- Paper : https://arxiv.org/html/2506.05176v1

---

## 8. Auto-Report / Page Generation

### 8.1 Etat de l'art

La generation de texte a partir de donnees structurees est un domaine mature grace aux LLM. Les approches :

| Approche | Technologie | Offline | Qualite |
|----------|------------|---------|---------|
| Templates parametres | Python f-strings | Oui | Previsible mais rigide |
| LLM local (0.6-4B) | Qwen3 via Ollama | Oui | Correct pour des resumes courts |
| LLM API (Claude Sonnet) | API Anthropic | Non | Excellent |
| Modeles specialises NLG | T5/BART fine-tune | Oui | Bon mais necessite fine-tuning |

### 8.2 Application concrete pour Niamoto

Niamoto genere des pages HTML d'export avec des widgets (graphiques, cartes, tableaux). Actuellement, les titres et descriptions sont configures manuellement dans transform.yml. L'IA pourrait :

1. **Generer des descriptions de widgets** : "Ce graphique montre la distribution des diametres (DBH) pour 1250 arbres. Le diametre moyen est de 23.5 cm avec un ecart-type de 12.1 cm."

2. **Generer des narratifs de page** : "La foret de Riviere Bleue presente une diversite de 45 familles botaniques. Les Myrtaceae dominent avec 23% des individus."

3. **Detecter les patterns narratifs** : "Les donnees montrent une correlation positive entre le DBH et la hauteur (r=0.78), typique d'une relation allometrique."

### 8.3 Approche recommandee

| Phase | Methode | Technologie |
|-------|---------|------------|
| **V1 (maintenant)** | Templates parametres | Python pur |
| **V2 (moyen terme)** | LLM optionnel pour les descriptions | Qwen3-0.6B via Ollama |
| **V3 (long terme)** | LLM pour les narratifs de page | Qwen3-4B ou API Claude |

**Template parametres (V1)** :
```python
TEMPLATES = {
    "histogram": "Distribution de {column} ({n} observations). "
                 "Moyenne : {mean:.1f} {unit}, ecart-type : {std:.1f} {unit}.",
    "bar_chart": "Repartition par {category} ({n_categories} categories). "
                 "{top_category} domine avec {top_pct:.0f}%.",
    "scatter": "Relation entre {x_col} et {y_col} (n={n}). "
               "Correlation : r={corr:.2f}.",
}
```

C'est simple, deterministe, et suffisant pour la v1. L'enrichissement par LLM viendra quand les templates deviennent trop rigides.

---

## 9. Synthese : matrice de decision

### Technologies recommandees par horizon

| Horizon | Technologie | Usage Niamoto | Investissement |
|---------|------------|---------------|---------------|
| **Maintenant** | scikit-learn (existant) | Detection, anomalies, suggestions | Deja fait |
| **Phase 4** | FastEmbed + EmbeddingGemma-300M (ONNX) | Embeddings multilingues complementaires | ~2 jours integration |
| **Phase 4** | Ollama + Qwen3-0.6B | Suggestions cross-colonnes (Tier M2) | ~3 jours integration |
| **Phase 5** | Ollama + Qwen3-4B | Text-to-SQL, descriptions auto | ~1 semaine |
| **Phase 5** | Templates parametres | Auto-description des widgets | ~2 jours |
| **Long terme** | API Claude (optionnel) | Narratifs de page, enrichissement gold set | Pay-per-use |

### Technologies rejetees (avec justification)

| Technologie | Pourquoi rejetee |
|-------------|-----------------|
| ColBERT/ModernColBERT | Overkill pour 25 concepts, 560 MB |
| TAPAS/TaPEx/TableFormer | Trop lourds, GPU recommande, mauvais ratio pour le domaine |
| TURL | Interessant mais 440 MB + PyTorch |
| Sherlock/Sato/DoDuo (complets) | Necessitent 100k+ colonnes, GPU, PyTorch |
| LIDA (direct) | LLM obligatoire par generation, genere matplotlib pas Plotly |
| VegaFusion | Niamoto utilise Plotly, pas Vega-Lite |
| Deepchecks | Overkill, oriente ML ops |
| DuckDB-NSQL 7B (immediat) | 4 GB, lent sur CPU, premature |
| BioCLIP | Images, pas CSV |
| RACOON | Necessite KG + LLM en ligne |

### Technologies a surveiller

| Technologie | Pourquoi la surveiller | Condition d'adoption |
|-------------|----------------------|---------------------|
| Magneto (VLDB 2025) | Pattern SLM+LLM pour schema matching | Si le gold set depasse 5k+ colonnes |
| Qwen3-Embedding-0.6B (GGUF) | Alternative a EmbeddingGemma | Si les benchmarks montrent un avantage sur les noms courts |
| Data Formulator v0.3+ | Inspiration UX pour les suggestions | Si migration vers Vega-Lite envisagee |
| GBIF AI initiatives (2026) | Modeles entraines sur Darwin Core | S'ils publient un modele pre-entraine |
| StatGPT (IMF) | Pattern "LLM + API stats officielle" | Pour la narration de donnees ecologiques |

---

## 10. Recommandation finale

Le pipeline scikit-learn actuel de Niamoto (macro-F1 0.97) est **deja a l'etat de l'art pour son domaine** avec des contraintes offline-first. Les technologies IA modernes n'apporteraient des gains que dans deux axes :

1. **Enrichissement semantique** (Phase 4) : EmbeddingGemma-300M via FastEmbed pour le matching multilingue residuel, Qwen3-0.6B via Ollama pour les suggestions cross-colonnes. Investissement : ~5 jours, gain marginal.

2. **Experience utilisateur avancee** (Phase 5+) : text-to-SQL, descriptions auto-generees, narratifs de page. Investissement : ~2 semaines, gain en UX.

**La priorite reste l'enrichissement du gold set** (plus de datasets ecologiques labelises), pas le changement de technologies. Avec 5000+ colonnes gold, le pipeline actuel progressera mecaniquement. Avec les memes 2231 colonnes et un modele plus sophistique, le gain serait marginal.

> "Plus de donnees bat un meilleur algorithme." -- Niamoto gold set strategy

---

## Sources

### Column/Schema Understanding
- [Reason-ModernColBERT (LightOn AI)](https://huggingface.co/lightonai/Reason-ModernColBERT)
- [GTE-ModernColBERT-v1 (LightOn AI)](https://huggingface.co/lightonai/GTE-ModernColBERT-v1)
- [TAPAS - HuggingFace docs](https://huggingface.co/docs/transformers/model_doc/tapas)
- [Transformers for Tabular Data (TACL survey)](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00544)
- [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [EmbeddingGemma-300M (Google)](https://developers.googleblog.com/introducing-embeddinggemma/)
- [EmbeddingGemma ONNX](https://huggingface.co/onnx-community/embeddinggemma-300m-ONNX)
- [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- [Small LM Benchmark (Distillabs)](https://www.distillabs.ai/blog/we-benchmarked-12-small-language-models-across-8-tasks-to-find-the-best-base-model-for-fine-tuning)
- [Small Language Models Guide 2026](https://localaimaster.com/blog/small-language-models-guide-2026)
- [Magneto: SLM + LLM Schema Matching (VLDB 2025)](https://arxiv.org/abs/2412.08194)
- [Magneto code](https://github.com/VIDA-NYU/magneto-matcher)
- [RACOON: RAG + KG Column Annotation (NeurIPS 2024)](https://arxiv.org/abs/2409.14556)
- [FastEmbed (Qdrant)](https://github.com/qdrant/fastembed)

### Auto-Visualization
- [LIDA (Microsoft Research)](https://github.com/microsoft/lida)
- [LIDA paper (ACL 2023)](https://aclanthology.org/2023.acl-demo.11/)
- [Data Formulator (Microsoft)](https://github.com/microsoft/data-formulator)
- [Data2Vis](https://github.com/victordibia/data2vis)
- [VizML (CHI 2019)](https://dl.acm.org/doi/fullHtml/10.1145/3290605.3300358)
- [VegaFusion](https://github.com/vega/vegafusion)
- [Data Visualization Recommendation Survey 2026](https://journals.sagepub.com/doi/10.1177/14738716251409351)

### Data Quality
- [Great Expectations](https://github.com/great-expectations/great_expectations)
- [Open-Source Data Quality Landscape 2026](https://datakitchen.io/the-2026-open-source-data-quality-and-data-observability-landscape/)

### Text-to-SQL
- [DuckDB-NSQL 7B](https://github.com/NumbersStationAI/DuckDB-NSQL)
- [DuckDB-NSQL on Ollama](https://ollama.com/library/duckdb-nsql)
- [SQLCoder (Defog)](https://huggingface.co/defog/sqlcoder)
- [Small Models Text-to-SQL Benchmark](https://datamonkeysite.com/2025/05/05/a-non-scientific-benchmark-of-text-to-sql-using-small-models/)
- [Text-to-SQL Complete Guide 2026](https://builder.ai2sql.io/blog/text-to-sql-complete-guide)

### Biodiversity AI
- [BioCLIP (CVPR 2024)](https://arxiv.org/abs/2311.18803)
- [BioCLIP code](https://github.com/Imageomics/bioclip)
- [GBIF species matching](https://www.gbif.org/tools/species-lookup)
- [GBIF backbone taxonomy](https://www.gbif.org/dataset/d7dddbf4-2cf0-4f39-9b2a-bb099caae36c)

### Local Models & Infrastructure
- [Ollama library](https://ollama.com/library)
- [ONNX Runtime](https://onnxruntime.ai/)
- [FastEmbed ONNX guide](https://johal.in/fastembed-onnx-lightweight-embedding-inference-2025/)
- [Best Open-Source Embedding Models 2026](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)

### Schema Understanding (Academic)
- [Sherlock (KDD 2019)](https://arxiv.org/abs/1905.10688)
- [Sato (VLDB 2020)](https://www.vldb.org/pvldb/vol13/p1835-zhang.pdf)
- [LLM for Column Typing (Korini & Bizer, 2023)](https://arxiv.org/abs/2306.00745)
- [Grinsztajn et al. - Tree-based vs Deep Learning on Tabular Data (NeurIPS 2022)](https://arxiv.org/abs/2207.08815)
