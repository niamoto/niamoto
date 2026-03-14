# Template — Rapport de Parité (`niamoto-nc` vs `niamoto-test`)

Date d'exécution : `____/____/______`
Auteur(s) : `______________________`
Version app/branche : `______________________`

## 1) Contexte

- Référence : `/Users/julienbarbe/Dev/clients/niamoto/test-instance/niamoto-nc`
- Test UI : `/Users/julienbarbe/Dev/clients/niamoto/test-instance/niamoto-test`
- Objectif : valider la parité fonctionnelle pilotée UI sur `taxons`, `plots`, `shapes`, `publication/export`
- Principe non négociable : **configuration over code** (aucun hardcode métier spécifique instance)

## 2) Résultat exécutif

- Statut global : `GO` / `GO with conditions` / `NO-GO`
- Résumé (5 lignes max) :
  - `...`
  - `...`

## 3) Matrice de parité par domaine

| Domaine | Statut | Couverture testée | Écarts détectés | Criticité max | Owner |
|---|---|---|---|---|---|
| Taxons | `OK/KO/PARTIEL` | `...` | `...` | `P1/P2/P3/None` | `...` |
| Plots | `OK/KO/PARTIEL` | `...` | `...` | `P1/P2/P3/None` | `...` |
| Shapes | `OK/KO/PARTIEL` | `...` | `...` | `P1/P2/P3/None` | `...` |
| Publication/Export | `OK/KO/PARTIEL` | `...` | `...` | `P1/P2/P3/None` | `...` |

## 4) Exécution détaillée (checklist)

### Import

- [ ] Sources importées avec succès
- [ ] Mapping entités/colonnes validé
- [ ] Aucune hypothèse hardcodée détectée

### Transform

- [ ] `taxons` exécuté et vérifié
- [ ] `plots` exécuté et vérifié
- [ ] `shapes` exécuté et vérifié
- [ ] Widgets conformes aux attentes métier

### Publication

- [ ] Build statique réussi
- [ ] Preview local valide
- [ ] Navigation et pages conformes

### Configuration over code

- [ ] Changement de nom d'entité testé sans patch code
- [ ] Changement de nom de colonne testé sans patch code
- [ ] Flux complet toujours opérationnel

## 5) Comparaison des sorties (référence vs test UI)

## 5.1 Méthode de comparaison

- Répertoires comparés : `______________________`
- Règles d'ignorance (timestamps, métadonnées non fonctionnelles) :
  - `...`

## 5.2 Résultats de comparaison

| Objet comparé | Référence | Test UI | Verdict | Commentaire |
|---|---|---|---|---|
| Taxons output | `...` | `...` | `OK/KO` | `...` |
| Plots output | `...` | `...` | `OK/KO` | `...` |
| Shapes output | `...` | `...` | `OK/KO` | `...` |
| Site généré | `...` | `...` | `OK/KO` | `...` |

## 6) Écarts et plan d'action

| ID | Domaine | Description | Sévérité | Type | Owner | ETA | Statut |
|---|---|---|---|---|---|---|---|
| GAP-001 | `...` | `...` | `P1/P2/P3` | `Bug/Config/UX/Perf` | `...` | `...` | `Open/In Progress/Done` |

## 7) Décision Go/No-Go

- Décision : `GO` / `GO with conditions` / `NO-GO`
- Conditions (si applicable) :
  - `...`
- Sign-off :
  - Product : `________________`
  - Tech (CTO/Lead) : `________________`
  - QA : `________________`
  - Date : `____/____/______`

## 8) Annexes

- Logs/commandes principales :
  - `...`
- Captures d'écran UI :
  - `...`
- Liens tickets associés :
  - `...`
