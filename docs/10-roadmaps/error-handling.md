# Niamoto Error Handling Improvement Roadmap

## 🎯 Objectif

Améliorer progressivement la gestion d'erreurs dans tout le système Niamoto pour fournir des messages d'erreur clairs, contextuels et actionables, en réduisant la verbosité des stack traces inutiles.

## 📊 État Actuel

### ✅ Points forts existants
- Architecture d'exceptions bien structurée (`NiamotoError` → spécialisées)
- Système `@error_handler` décorateur fonctionnel
- Méthode `get_user_message()` pour messages personnalisés
- Integration avec Rich console pour l'affichage

### ❌ Problèmes identifiés
- **Verbosité excessive**: Stack traces complètes pour erreurs de configuration
- **Manque de contexte**: Erreurs génériques sans pointer l'élément problématique
- **Inconsistance**: Gestion différente selon les commandes (import/transform/export)
- **Pas de suggestions**: Aucune aide pour corriger les erreurs

### 🔍 Types d'erreurs rencontrés
1. **Configuration**: YAML malformé, champs manquants, valeurs invalides
2. **Fichiers**: Fichiers introuvables, formats invalides, permissions
3. **Données**: Validation échouée, types incorrects, références cassées
4. **Processing**: Calculs échoués, plugins défaillants, ressources insuffisantes
5. **Sortie**: Échec d'écriture, templates corrompus, espaces disques

## 🏗️ Fondation Commune

### Phase 0: Infrastructure de base ⏳
> **Priorité**: CRITIQUE - Prérequis pour toutes les autres phases

#### 0.1 Améliorer ConfigurationError
- [ ] Support pour indexation dans les listes (`shapes[0]`, `transforms[2]`)
- [ ] Affichage YAML de la configuration problématique
- [ ] Suggestions intelligentes basées sur erreurs fréquentes
- [ ] Intégration avec fuzzy matching pour champs similaires

#### 0.2 Étendre error_handler
- [ ] Mode "minimal" sans stack trace pour erreurs attendues
- [ ] Support pour agrégation d'erreurs multiples
- [ ] Codes de sortie standardisés par type d'erreur
- [ ] Logging structuré avec contexte

#### 0.3 Créer ErrorFormatter
- [ ] Classe utilitaire pour formater les erreurs de façon consistante
- [ ] Templates d'affichage par type d'erreur
- [ ] Support pour différents niveaux de verbosité
- [ ] Integration avec Rich pour colorisation intelligente

#### 0.4 Validation Framework
- [ ] Classes de validation réutilisables (`ConfigValidator`, `FileValidator`)
- [ ] Validation en pipeline avec accumulation d'erreurs
- [ ] Messages d'erreur standardisés avec suggestions
- [ ] Support pour validation conditionnelle

**Critères de validation Phase 0**:
- ✅ Aucun stack trace pour erreurs de configuration
- ✅ Messages pointent précisément l'élément problématique
- ✅ Suggestions disponibles pour 80% des erreurs courantes
- ✅ Temps de développement d'une nouvelle validation < 15 min

## 📈 Roadmap Progressive

### Phase 1: Import Commands 🚀
> **Priorité**: HAUTE - Impact utilisateur immédiat

#### 1.1 Shapes Import
- [ ] Messages spécifiques par index (`shapes[0]: Missing field 'name_field'`)
- [ ] Validation de chemins avec suggestions alternatives
- [ ] Erreurs de géométrie avec contexte spatial
- [ ] Preview de la configuration problématique

#### 1.2 Taxonomy Import
- [ ] Validation des rangs taxonomiques
- [ ] Erreurs de hiérarchie avec visualisation
- [ ] API enrichment errors avec fallback options
- [ ] CSV validation avec numéro de ligne

#### 1.3 Occurrences Import
- [ ] Erreurs de liaison taxon/plot avec suggestions
- [ ] Validation géospatiale avec tolérances
- [ ] Gestion des doublons avec options de résolution
- [ ] Statistiques d'import enrichies

#### 1.4 Plots Import
- [ ] Validation hiérarchique avec représentation arbre
- [ ] Erreurs de géoréférencement contextuelles
- [ ] Conflits d'identifiants avec résolution suggérée

**Exemples de messages améliorés**:
```
❌ Configuration error in shapes[0]
   Missing required field: 'name_field'

   Configuration:
   - name: "country"
     type: shapefile
     path: "imports/shapes/countries.shp"
     id_field: "id"
     # Missing: name_field

   💡 Suggestion: Add 'name_field: "NAME"' to specify the feature name column
```

### Phase 2: Transform Commands 🔄
> **Priorité**: MOYENNE - Après stabilisation des imports

#### 2.1 Plugin System
- [ ] Erreurs de plugin avec détails de configuration
- [ ] Validation des paramètres avec types attendus
- [ ] Échecs de calcul avec données d'entrée contextuelles
- [ ] Suggestions de plugins alternatifs

#### 2.2 Data Pipeline
- [ ] Erreurs de transformation avec étape précise
- [ ] Validation des données intermédiaires
- [ ] Gestion des ressources (mémoire, temps)
- [ ] Recovery options pour calculs partiels

#### 2.3 Group Configuration
- [ ] Validation des groupes avec plugins disponibles
- [ ] Erreurs de dépendances avec graphe
- [ ] Configuration conditionnelle

### Phase 3: Export Commands 📤
> **Priorité**: MOYENNE - Stabilisation après phases 1-2

#### 3.1 Template System
- [ ] Erreurs de template avec ligne/colonne
- [ ] Variables manquantes avec contexte de données
- [ ] Erreurs de rendu avec preview partiel

#### 3.2 Static Site Generation
- [ ] Erreurs de fichiers avec arborescence
- [ ] Assets manquants avec alternatives
- [ ] Validation HTML/CSS/JS

#### 3.3 Widget System
- [ ] Erreurs de widget avec données d'entrée
- [ ] Configuration de visualisation
- [ ] Performance warnings

### Phase 4: CLI Consistency 🎨
> **Priorité**: FAIBLE - Polish final

#### 4.1 Message Formatting
- [ ] Style guide pour tous les messages
- [ ] Codes couleur cohérents
- [ ] Icons et symboles standardisés

#### 4.2 Help System
- [ ] Intégration help contextuelle dans les erreurs
- [ ] Documentation auto-générée des erreurs
- [ ] Exemples de configuration valides

#### 4.3 Exit Codes
- [ ] Codes de sortie standardisés
- [ ] Intégration CI/CD
- [ ] Scripts de diagnostic

## 🛠️ Standards & Patterns

### Convention de Naming
- `ConfigurationError`: Erreurs de fichiers YAML/JSON
- `ValidationError`: Erreurs de validation de données
- `ProcessingError`: Erreurs de traitement/calcul
- `ResourceError`: Erreurs de fichiers/réseau/ressources

### Structure de Message Type
```
❌ [ERROR_TYPE] in [CONTEXT]
   [DESCRIPTION]

   [PROBLEMATIC_CONFIG/DATA]

   💡 [SUGGESTION]
   📚 [DOCUMENTATION_LINK]
```

### Niveaux de Verbosité
- **Minimal**: Message + suggestion uniquement
- **Normal**: + contexte de configuration
- **Verbose**: + stack trace pour debugging
- **Debug**: + état interne complet

## 📋 Checklist de Progression

### Phase 0 - Fondation
- [ ] ConfigurationError amélioré
- [ ] ErrorFormatter créé
- [ ] Validation framework
- [ ] Tests de non-régression

### Phase 1 - Imports
- [ ] Shapes: messages contextuels ✅ (en cours)
- [ ] Taxonomy: validation rangs
- [ ] Occurrences: liaison errors
- [ ] Plots: hiérarchie errors

### Phase 2 - Transforms
- [ ] Plugin validation
- [ ] Pipeline errors
- [ ] Group configuration

### Phase 3 - Exports
- [ ] Template errors
- [ ] Static generation
- [ ] Widget system

### Phase 4 - Polish
- [ ] CLI consistency
- [ ] Documentation
- [ ] Exit codes

## 🧪 Tests de Validation

### Critères de Réussite
1. **Temps de résolution**: Utilisateur peut identifier et corriger l'erreur en < 2 min
2. **Précision**: Message pointe exactement l'élément problématique
3. **Actionabilité**: 90% des erreurs incluent une suggestion de correction
4. **Consistance**: Format identique à travers toutes les commandes
5. **Performance**: Pas de dégradation des temps d'exécution

### Test Cases Standards
- Configuration vide/malformée
- Champs requis manquants
- Types de données incorrects
- Fichiers introuvables
- Permissions insuffisantes
- Données corrompues
- Ressources insuffisantes

## 📅 Timeline Estimé

- **Phase 0**: 1-2 semaines (fondation critique)
- **Phase 1**: 2-3 semaines (imports, haute priorité)
- **Phase 2**: 2-3 semaines (transforms)
- **Phase 3**: 1-2 semaines (exports)
- **Phase 4**: 1 semaine (polish)

**Total estimé**: 7-11 semaines en développement parallèle aux autres features.

---

## 📝 Notes d'Implementation

### Commencer par:
1. Améliorer `ConfigurationError.get_user_message()` avec indexation
2. Implémenter validation shapes avec messages contextuels
3. Créer quelques exemples de "bonnes erreurs" comme référence
4. Itérer basé sur feedback utilisateur

### Maintenir Compatibilité:
- Tous les changements doivent être rétro-compatibles
- Tests existants ne doivent pas être cassés
- API publique des exceptions conservée

---

*Ce document est un guide vivant - à mettre à jour au fur et à mesure des implémentations et découvertes.*
