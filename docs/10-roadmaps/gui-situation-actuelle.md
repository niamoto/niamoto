# Situation Actuelle GUI - État des Lieux

**Date**: 22 Octobre 2025
**Commit**: 8b22b98 (avant tentatives migration EntityRegistry GUI)
**Status**: Backend EntityRegistry ✅ fonctionnel | GUI ❌ non adapté

---

## 🎯 Résumé Exécutif

Le backend Niamoto a été migré avec succès vers EntityRegistry (74% plugins critiques migrés).
Le GUI reste figé sur 4 imports hardcodés (`taxonomy`, `occurrences`, `plots`, `shapes`).

**Problème central**: Le GUI ne peut pas gérer les custom entities définies via EntityRegistry.

---

## 📊 État Actuel

### Backend ✅
- EntityRegistry fonctionnel
- API générique `/api/imports/execute` prête
- **TOUS les plugins supportent EntityRegistry** via classe de base `Plugin`
  - Méthode `resolve_entity_table()` disponible pour tous
  - 20 plugins utilisent explicitement EntityRegistry (imports + accès DB)
  - Autres plugins fonctionnent avec données passées (pas d'accès DB direct)
- Support entities custom dans `import.yml`
- Pipeline complet fonctionne avec entities custom ✅

### Frontend ❌
- Types figés: `'taxonomy' | 'occurrences' | 'plots' | 'shapes'`
- `ImportButton.tsx` envoie `import_type` (format legacy)
- API attend `entity_name` + `entity_type` (format EntityRegistry)
- **Résultat**: Impossible d'importer custom entities via GUI

---

## 🔴 5 Problèmes Critiques Identifiés

### 1. Flux d'import câblé sur types legacy
**Fichier**: `src/niamoto/gui/ui/src/pages/import/ImportButton.tsx`

**Problème**: Envoie `import_type: 'taxonomy'` au lieu de `entity_name: 'taxons'` + `entity_type: 'reference'`

**Impact**: Incompatibilité totale avec nouveau endpoint générique

### 2. Types UI figés
**Fichier**: `src/niamoto/gui/ui/src/components/import-wizard/types.ts`

```typescript
export type ImportType = 'taxonomy' | 'plots' | 'occurrences' | 'shapes'
```

**Problème**: Impossible d'ajouter une 5ème entité sans modifier le code

**Impact**: Pas de support entities dynamiques

### 3. Hooks non alignés EntityRegistry
**Fichier**: `src/niamoto/gui/ui/src/hooks/useImportStatus.ts`

**Problème**: Suppose 2 listes fixes (`references`/`datasets`)

**Impact**: UI n'affiche pas correctement les statuts entities custom

### 4. Analyse fichiers basée sur import_type
**Fichier**: `src/niamoto/gui/ui/src/lib/api/import.ts`

**Problème**: `analyzeFile(file, importType)` au lieu de `analyzeFile(file, entityName, entityType)`

**Impact**: Détection colonnes limitée aux 4 types hardcodés

### 5. Code mort (694 lignes)
**Fichiers**:
- `components/import-wizard/FileSelection.tsx` (210 lignes)
- `components/import-wizard/PlotHierarchyConfig.tsx` (211 lignes)
- `components/import-wizard/PropertySelector.tsx` (113 lignes)
- `components/import-wizard/TaxonomyRankEditor.tsx` (160 lignes)

**Problème**: Composants orphelins jamais utilisés

**Impact**: Complexité inutile, maintenance difficile

---

## ✅ Ce qui a été tenté (branche backup)

Entre `601bb0e` et `1458bd5`, 6 commits ont tenté d'adapter le GUI :
- Création `EntitySelector` component + `useEntities` hook
- Wrappers legacy (`executeImportLegacy`, etc.)
- Types dynamiques avec backward compatibility
- Nouveaux endpoints `/api/imports/entities`

**Résultat**: Architecture complexe avec wrappers, code difficile à maintenir → **Reset effectué**

---

## 🎯 Options Stratégiques

### Option A - Minimaliste ⭐ **RECOMMANDÉE**
**Approche**: Créer Entity Manager séparé, garder Import Wizard actuel intact

**Avantages**:
- Pas de risque de casser l'existant
- GUI existant continue de fonctionner pour les 4 types historiques
- Nouveau Entity Manager pour custom entities uniquement
- Séparation claire des responsabilités

**Inconvénients**:
- Deux interfaces distinctes
- Duplication partielle du code

**Livrable**:
- `/entity-manager` page (nouvelle route)
- Formulaire dynamique basé sur EntityRegistry
- YAML preview + download
- Aucun changement à Import Wizard existant

---

### Option B - Migration Progressive
**Approche**: Adapter Import Wizard progressivement avec feature flag

**Avantages**:
- Une seule interface à terme
- Pas de duplication

**Inconvénients**:
- Risque élevé de régression
- Beaucoup de refactoring
- Complexité temporaire avec feature flags

**Livrable**:
- Import Wizard adapté pour supporter entities dynamiques
- Backward compatibility pour 4 types historiques
- Tests E2E complets requis

---

### Option C - Status Quo
**Approche**: Garder GUI hardcodé, documenter comment ajouter entities manuellement

**Avantages**:
- Zéro effort GUI
- Aucun risque

**Inconvénients**:
- Utilisateurs devront éditer `import.yml` à la main
- Pas d'interface pour custom entities
- Faible adoption EntityRegistry

**Livrable**:
- Documentation détaillée
- Exemples import.yml

---

## 💡 Recommandation

**Choisir Option A - Entity Manager séparé**

### Pourquoi ?
1. **Risque minimal** - GUI existant non touché
2. **Livrable rapide** - 1-2 semaines max
3. **Clarté** - Séparation nette ancien/nouveau système
4. **Evolutif** - Pourra remplacer Import Wizard plus tard si besoin

### Scope minimal Option A
**Phase 1 - Entity Manager (1 semaine)**:
- [ ] Page `/entity-manager` avec liste entities
- [ ] Dialog création entity (form dynamique)
- [ ] Dialog édition entity existante
- [ ] YAML preview + download
- [ ] Tests unitaires

**Phase 2 - Cleanup (2 jours)**:
- [ ] Supprimer 4 composants morts (694 lignes)
- [ ] Documenter architecture dual-system
- [ ] Guide utilisateur Entity Manager

**Phase 3 - Integration optionnelle (future)**:
- [ ] Migrer Import Wizard vers Entity Manager
- [ ] Unifier interfaces

---

## 📋 Actions Immédiates

### Avant de démarrer quoi que ce soit :

1. **Décider de l'option** (A, B ou C)
2. **Valider le scope** avec l'équipe
3. **Définir les critères de succès**

### Si Option A choisie :

1. **Nettoyer code mort** (1h)
   ```bash
   rm src/niamoto/gui/ui/src/components/import-wizard/FileSelection.tsx
   rm src/niamoto/gui/ui/src/components/import-wizard/PlotHierarchyConfig.tsx
   rm src/niamoto/gui/ui/src/components/import-wizard/PropertySelector.tsx
   rm src/niamoto/gui/ui/src/components/import-wizard/TaxonomyRankEditor.tsx
   ```

2. **Créer structure Entity Manager** (2h)
   ```
   src/niamoto/gui/ui/src/pages/entity-manager/
   ├── index.tsx              # Page principale
   ├── EntityList.tsx         # Liste entities
   ├── EntityFormDialog.tsx   # Création/édition
   └── YamlPreview.tsx        # Preview YAML
   ```

3. **API endpoints nécessaires** (déjà existants)
   - ✅ `GET /api/entities` - Liste entities
   - ✅ `POST /api/entities` - Créer entity
   - ✅ `PUT /api/entities/{name}` - Modifier entity
   - ⚠️ À vérifier/créer si manquant

---

## 📊 Métriques de Succès

### Pour Option A (Entity Manager)
- [ ] Créer une custom entity "habitats" via GUI
- [ ] Générer `import.yml` avec nouvelle entity
- [ ] Importer fichier CSV via CLI avec nouvelle entity
- [ ] Vérifier données en DB
- [ ] Documentation utilisateur complète

### Critères non-régression
- [ ] Import Wizard existant fonctionne toujours
- [ ] 4 types historiques (taxonomy/plots/occurrences/shapes) OK
- [ ] Aucun test cassé

---

## 🔗 Ressources

- **Audit complet**: `docs/10-roadmaps/gui-audit-report.md` (930 lignes)
- **Branche backup**: `backup/entity-registry-gui-migration-attempt`
- **Plan action**: `docs/10-roadmaps/refactor-action-plan.md`
- **EntityRegistry**: `src/niamoto/core/imports/registry.py`

---

## 🤔 Questions à Résoudre

1. **Quelle option choisir** (A, B ou C) ?
2. **Entity Manager doit-il gérer** :
   - [ ] Uniquement création entities ?
   - [ ] Aussi configuration loaders/extractors ?
   - [ ] Aussi hiérarchies (nested_set) ?
3. **Format de sortie** :
   - [ ] Seulement YAML à copier/coller ?
   - [ ] Aussi écriture directe dans `config/import.yml` ?
   - [ ] Aussi génération fichiers séparés (`entities/*.yml`) ?

---

**Prochaine étape**: Décider de l'option et affiner le scope avant tout développement.
