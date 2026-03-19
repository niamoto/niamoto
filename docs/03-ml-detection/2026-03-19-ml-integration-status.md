# Point complet — ML Detection × Application Niamoto

## Contexte

La branche `feat/ml-detection-improvement` a construit un pipeline ML complet
(alias → header → values → fusion → semantic_profile → affordances). Ce document
fait le point sur ce qui marche, ce qui est intégré à l'app, et ce qui reste à
connecter.

---

## 1. État des modèles ML

### Modèles entraînés et livrés

| Modèle | Fichier | Taille | Technique |
|--------|---------|--------|-----------|
| Header | `models/header_model.joblib` | 2.6 MB | TF-IDF char n-grams + LogReg |
| Values | `models/value_model.joblib` | 38 MB | HistGradientBoosting (38 features) |
| Fusion | `models/fusion_model.joblib` | 50 KB | LogReg sur probas alignées + méta-features |

Les 3 modèles sont **bundlés dans le package** via `pyproject.toml` et chargés
lazily au runtime par `ColumnClassifier`.

### Gold set

- **2492 colonnes** (1896 gold + 596 synthetic)
- **61 concepts**, **10 rôles**, **7 langues**
- Sources : Guyane (Paracou), GBIF ciblé (NC/GF/GA/CM), GBIF institutionnel
  (GA/CM), inventaires forestiers, données synthétiques

### Scores actuels

| Métrique | Score |
|----------|-------|
| **NiamotoOfflineScore** | 78.6 |
| **ProductScore** | 79.2 |
| GBIF core standard | 96.3 |
| Anonymous | 100.0 |
| English standard | 95.7 |
| tropical_field | 64.0 |
| en_field | 75.9 |
| forest_inventory | 41.8 |

**Verdict modèles** : bons sur GBIF standard et colonnes anonymes, moyens sur
le terrain tropical et les headers codés métier.

---

## 2. Intégration dans l'application — ce qui MARCHE

### Pipeline d'import (end-to-end fonctionnel)

```
Upload CSV → POST /api/smart-config/auto-configure
  → ColumnDetector (règles + heuristiques)
  → Détection hiérarchie / relations FK
  → Génération import.yml
  → Review/édition par l'utilisateur
  → POST /api/imports/execute/all
  → DataProfiler → ColumnClassifier (ML 3 branches)
  → Semantic profiles stockés dans EntityRegistry
  → Suggestions de transformers disponibles
```

### Composants GUI fonctionnels

- **ImportWizard** : wizard 6 phases (upload → config → review → import → done)
- **FileUploadZone** : drag-drop CSV/GPKG/TIF/ZIP
- **AutoConfigDisplay** : affiche datasets/références/liens détectés
- **YamlPreview** : revue YAML avant import
- **ImportProgress** : suivi asynchrone avec polling

### API endpoints actifs

| Endpoint | Rôle | ML ? |
|----------|------|------|
| `POST /api/smart-config/auto-configure` | Auto-config complète | Heuristiques |
| `POST /api/smart-config/analyze-file` | Analyse colonnes | Heuristiques |
| `POST /api/smart-config/detect-hierarchy` | Hiérarchie taxo | Heuristiques |
| `POST /api/imports/execute/all` | Import complet | **ML (profiler)** |
| `GET /api/transformer-suggestions/{entity}` | Suggestions widgets | Via profils sémantiques |

### Semantic profiles & affordances

- `semantic_profile.py` : role + concept + affordances par colonne
- `affordance_matcher.py` : matching transformer→widget
- Profils stockés dans `EntityRegistry` après import
- Suggestions de transformers récupérables via API

---

## 3. Le GAP — ce qui N'EST PAS connecté

### Le ML ne tourne PAS pendant l'auto-config

C'est le point central :

- **Pendant l'upload/auto-config** : `ColumnDetector` utilise des **règles
  heuristiques** (patterns regex, FK par nom), PAS le classifier ML
- **Pendant l'import** : `DataProfiler` utilise le **classifier ML complet**
  (alias → header → values → fusion)
- L'utilisateur voit le résultat des heuristiques, pas du ML

Conséquence : la qualité de l'auto-config dépend des heuristiques, pas des
modèles ML entraînés.

### Scores de confiance ML invisibles

- Le classifier produit un score de confiance (0-1) par colonne
- Ce score n'est **jamais montré à l'utilisateur** dans le GUI
- L'utilisateur ne sait pas si la détection est sûre ou incertaine

### Semantic profiles invisibles pendant l'import

- Les profils sont générés et stockés mais **pas affichés**
- Pas d'endpoint pour récupérer les profils intermédiaires
- L'utilisateur ne voit pas les affordances détectées

### Suggestions de widgets pas connectées au GUI

- `class_object_suggester.py` existe mais **pas câblé à l'UI**
- L'endpoint `transformer-suggestions` fonctionne mais n'est **pas appelé**
  automatiquement après l'import

---

## 4. Deux systèmes de détection parallèles

| Composant | Quand | Technique | Fichier |
|-----------|-------|-----------|---------|
| `ColumnDetector` | Auto-config (avant import) | Règles/heuristiques | `column_detector.py` |
| `ColumnClassifier` | Import (profiling) | ML 3 branches | `classifier.py` |

C'est la source de confusion : le travail ML de la branche améliore
`ColumnClassifier`, mais l'utilisateur voit d'abord `ColumnDetector`.

---

## 5. Options pour combler le gap

### Option A — Brancher le ML dans l'auto-config

- Remplacer ou compléter `ColumnDetector` par `ColumnClassifier` dans
  `smart_config.py`
- L'utilisateur verrait le ML dès l'upload
- Risque : le ML est plus lent que les heuristiques (chargement modèles)

### Option B — Montrer les résultats ML après import

- Ajouter un endpoint `/api/semantic-profiles/{entity}`
- Afficher les profils sémantiques + confiance dans l'UI post-import
- Moins disruptif, permet de valider visuellement la qualité ML

### Option C — Fusionner les deux détecteurs

- `ColumnDetector` devient un wrapper qui appelle d'abord `AliasRegistry`,
  puis `ColumnClassifier`, puis les règles de fallback
- Un seul chemin de détection pour toute l'app
- Plus cohérent mais plus gros chantier

### Option D — Figer et merger la branche telle quelle

- Le ML tourne pendant l'import, c'est déjà utile
- Les heuristiques de l'auto-config marchent pour les cas simples
- On connecte le ML au GUI dans une prochaine itération

---

## 6. Recommandation retenue

### Phase 1 — Merger la branche telle quelle

Le ML tourne pendant l'import, les modèles sont livrés, les tests passent.
Merger maintenant pour arrêter d'accumuler de la dette d'intégration.

Prérequis avant merge :
- [ ] Vérifier que les tests passent sur main
- [ ] Nettoyer les fichiers obsolètes (`current-state.md` de décembre 2024)
- [ ] S'assurer que les modèles .joblib sont dans le bon état
- [ ] Rebase propre ou squash merge

### Phase 2 — Câbler le ML dans ColumnDetector

Faire de `ColumnClassifier` le moteur de détection sémantique unique :

- `ColumnDetector` garde : analyse FK, détection hiérarchie, inference
  dataset vs reference
- `ColumnDetector` délègue à `ColumnClassifier` : classification sémantique
  de colonne (type, concept, confiance)
- `smart_config.py` expose les scores ML dans la réponse auto-configure
- Le GUI affiche la confiance par colonne dans `AutoConfigDisplay`

Fichiers à modifier :
- `src/niamoto/core/utils/column_detector.py` — appeler ColumnClassifier
- `src/niamoto/gui/api/routers/smart_config.py` — retourner les scores ML
- `gui/ui/src/components/sources/AutoConfigDisplay.tsx` — afficher confiance

### Phase 3 — Exposer les semantic profiles dans l'UI

- Endpoint `GET /api/semantic-profiles/{entity_name}`
- Afficher affordances et suggestions post-import
- Câbler `class_object_suggester` au GUI

---

## 7. Résumé

Le pipeline ML est **construit, entraîné et intégré au profiling d'import**,
mais l'utilisateur ne le voit pas encore pendant l'auto-config — il voit les
heuristiques de `ColumnDetector`, pas les modèles ML.

La solution propre : merger d'abord, puis unifier les détecteurs pour que tout
le travail autoresearch bénéficie directement à l'UX.
