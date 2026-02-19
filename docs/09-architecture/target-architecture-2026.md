# Architecture Cible Niamoto (2026-2027)

**Date**: 2026-02-11  
**Portee**: GUI, API, Core pipeline, extensibilite plugins  
**Horizon**: 6 a 12 mois

---

## 1. Resume Executif

Niamoto repose aujourd'hui sur un **monolithe modulaire solide**: le coeur metier (pipeline + plugins), une API FastAPI d'orchestration, et un frontend React/Tauri.  
Cette base est pertinente et ne justifie pas une re-ecriture.

La trajectoire recommandee est:

1. **Conserver le monolithe** pour garder la vitesse de delivery.
2. **Clarifier les frontieres internes** (Domain / Application / Adapters).
3. **Durcir les capacites transverses** (jobs persistants, securite FS/reseau, observabilite).
4. **Rendre l'architecture "headless-ready"** (GUI, CLI, automation, et API externe utilisent le meme moteur).

Objectif final: une architecture plus robuste, plus lisible, et plus evolutive, sans sacrifier le rythme produit.

---

## 2. Point de Depart: Architecture Actuelle

### 2.1 Ce qui fonctionne bien

- Un pipeline metier clair: **Import -> Transform -> Export -> Publish**.
- Un moteur plugin extensible pour transformers, widgets, exporters.
- Un contrat de configuration fort via Pydantic/YAML.
- Une API unique qui sert a la fois web et desktop (Tauri), sans duplication majeure.
- Une dynamique produit rapide grace au monolithe.

### 2.2 Limites structurelles observees

- Couplage croissant entre **metier core** et besoins **UI** (hints, comportements, adaptation schema).
- Logique applicative parfois repartie dans les routers API.
- Jobs long-running encore trop dependants de l'etat memoire.
- Politiques transverses (filesystem, connectivite, erreurs, permissions) heterogenes.
- Contrats API utiles mais pas encore gouvernes comme des interfaces versionnees.

---

## 3. Objectifs d'Architecture (12 mois)

1. **Robustesse operationnelle**
- Jobs resilients aux redemarrages.
- Comportement previsible hors-ligne / en erreur.
- Meilleure tracabilite de bout en bout.

2. **Separations de responsabilites**
- Domain pur (regles metier).
- Application (use-cases, orchestration).
- Adapters (API, DB, filesystem, services externes, UI contracts).

3. **Extensibilite produit**
- Ajouter des plugins, des templates, des flux sans dette structurelle.
- Reutiliser le moteur dans plusieurs interfaces (GUI, CLI, API automation).

4. **Gouvernance technique**
- Decisions d'architecture explicites (ADR).
- Contrats stables et versionnes.
- Plan de migration incremental et mesurable.

---

## 4. Principes Directeurs

### 4.1 Evolution, pas revolution

Pas de big-bang. Chaque etape doit etre deployable, testable, et reversible.

### 4.2 Monolithe modulaire d'abord

Le passage en microservices n'est pas un objectif court terme. Le gain principal vient de la clarte interne et de la fiabilite.

### 4.3 Core metier independant des interfaces

Le domaine ne doit pas dependre des routers/API ni de la forme des ecrans.

### 4.4 Contracts as product

Les schemas, endpoints, events et formats de config sont des produits en soi: ils doivent etre stables, documentes, versionnes.

### 4.5 Secure by default

Les frontieres filesystem/reseau/exec doivent etre explicites, centralisees et testees.

### 4.6 Observability by design

Logs structures, correlation ids, metriques et traces minimales sur tous les workflows critiques.

---

## 5. Architecture Cible

### 5.1 Vue d'ensemble

```text
UI (React/Tauri) / CLI / API clients
        |
API Adapters (FastAPI routers, DTOs, authn/authz, validation I/O)
        |
Application Layer (Use-cases, orchestration, policies, transactions, jobs)
        |
Domain Layer (pipeline rules, plugin contracts, config semantics)
        |
Infrastructure Adapters (DB, FS, network, queue, external APIs, rendering)
```

### 5.2 Domain Layer (coeur metier)

Responsabilites:
- Regles metier pipeline.
- Contrats plugin (capabilities, schema constraints, invariants).
- Modeles metier agnostiques de l'interface.

Contraintes:
- Pas d'acces direct HTTP.
- Pas de dependance UI.
- Erreurs metier exprimees en types/domain errors, pas en details transport.

### 5.3 Application Layer (use-cases)

Responsabilites:
- Orchestrer les scenarios (start import, build transform plan, run export, preview widget, deploy).
- Gerer transactions, retries, policies metier.
- Unifier les jobs et leur lifecycle.

Valeur:
- Les routers deviennent minces.
- Les tests se concentrent sur les use-cases.
- La logique n'est plus dispersee par endpoint.

### 5.4 Adapters Layer

Responsabilites:
- API adapters: mapping HTTP <-> use-cases.
- Infra adapters: DB, fichiers, reseau, appels externes, renderers.
- UI adapters: transformation schema metier vers schema UI (sans polluer le domain).

Positionnement cle:
- Les **hints UI** restent possibles, mais isoles dans un contrat d'adaptation.
- Le core ne connait pas les composants React.

### 5.5 Jobs et traitements asynchrones

Cible:
- Job model persistable (etat, progression, erreurs, metadata).
- Reprise possible apres restart.
- API de controle standardisee (start, pause, resume, cancel, retry).
- Streaming/polling harmonise selon le besoin, avec semantics identiques.

### 5.6 Contrats et versioning

Cible:
- Versionner explicitement:
  - API endpoints sensibles.
  - JSON schema exposes au frontend.
  - Formats de config (transform/import/export).
- Maintenir compatibilite backward sur une fenetre definie.

### 5.7 Securite structurelle

Cible:
- Une couche unique de politiques de chemin (allowlist roots, path normalization, deny traversal).
- Une politique reseau explicite par use-case.
- Validation stricte des entrees externes (fichiers, URL, templates, scripts).

### 5.8 Observabilite

Cible minimale:
- Correlation ID par requete/job.
- Logs structures (niveau, contexte, duration, outcome).
- Metriques cle:
  - temps de job,
  - taux d'echec,
  - retries,
  - latence endpoints critiques.

### 5.9 Qualite et tests

Cible:
- Tests unitaires domaine/use-cases.
- Tests integration adapters (DB/FS/API externes mockes proprement).
- Tests e2e sur parcours critiques GUI/API.
- Tests de securite sur path policies et permissions.

---

## 6. Roadmap d'Evolution (3 Etapes)

### Etape 1 (0-3 mois): Stabilisation et Frontieres

Objectif: augmenter la fiabilite sans changer le modele produit.

Livrables:
- Carte des use-cases principaux et extraction des premiers services applicatifs.
- Standard job model (etat + persistence minimale).
- Couche centralisee de path/security policies.
- Instrumentation de base (logs structures + correlation id).

Resultat attendu:
- Moins de logique dans les routers.
- Moins de comportements divergents sur erreurs et permissions.

### Etape 2 (3-6 mois): Structuration Application

Objectif: rendre l'orchestration explicite et testable.

Livrables:
- Migration progressive des workflows majeurs vers use-cases:
  - import,
  - transform,
  - export,
  - enrichment/deploy.
- Contrat unifie de job control.
- Contrat d'adaptation UI formalise (schema metier -> schema formulaire UI).

Resultat attendu:
- API plus stable.
- Dette de couplage core/UI reduite.
- Meilleure testabilite de bout en bout.

### Etape 3 (6-12 mois): Acceleration Produit

Objectif: exploiter la nouvelle structure pour livrer plus vite et plus surement.

Livrables:
- Versioning des contrats sensibles (API/schema/config).
- Catalogue plugin/capabilities mieux gouverne.
- Capacite headless renforcee pour automation externe.
- SLO/SLI de fiabilite sur jobs critiques.

Resultat attendu:
- Plateforme plus previsible pour l'equipe et les integrateurs.
- Time-to-market conserve, avec moins de regressions structurelles.

---

## 7. Decisions d'Architecture a Prendre (Backlog ADR)

1. **ADR: Frontiere Domain/Application/Adapters**
- Convention de dependances autorisees/interdites.

2. **ADR: Job Persistence Model**
- Stockage, retention, reprise, idempotence.

3. **ADR: Contract Versioning Strategy**
- Regles de compatibilite et de deprecation.

4. **ADR: Filesystem Security Policy**
- Roots autorises, politiques d'acces, audits.

5. **ADR: UI Contract Boundary**
- Ce qui vit dans le core vs ce qui vit dans l'adapter UI.

6. **ADR: Observability Standard**
- Format log, correlation, metriques obligatoires.

---

## 8. Ce que cette Architecture Ouvre

- Support propre de plusieurs canaux (desktop, web, cli, automation).
- Capacite a ajouter de nouveaux plugins et templates sans regressions transverses.
- Base plus solide pour industrialisation (audit, support, debugging, monitoring).
- Possibilite d'evoluer un jour vers des composants separes, mais depuis une base deja propre.

---

## 9. Alternatives Envisagees

### 9.1 Re-ecriture complete

Non retenue. Cout eleve, risque produit fort, peu de valeur immediate.

### 9.2 Microservices court terme

Non retenue. Complexite operationnelle prematuree. Le principal goulot est la structure interne, pas la distribution reseau.

### 9.3 Statut quo

Non retenu. La vitesse court terme resterait bonne, mais la complexite cumulative ralentira fortement les evolutions.

---

## 10. Plan 30/60/90 jours (pragmatique)

### J+30

- Alignement equipe sur frontieres cibles.
- Liste priorisee de 5 use-cases a extraire.
- Definition du contrat job standard.

### J+60

- Premier lot de use-cases en production.
- Policies securite fichiers centralisees.
- Correlation id et logs structures actifs.

### J+90

- Workflows critiques migres (import/transform/export au minimum partiel).
- Dashboard minimal de metriques techniques.
- Premier ADR lot complete.

---

## 11. Definition de Succes

Le plan est reussi si, dans 12 mois:

- Les evolutions UI n'obligent plus des adaptations fragiles du coeur metier.
- Les workflows critiques sont pilotables et recuperables apres incident.
- Les contrats principaux ont une politique de versioning explicite.
- Les regressions "transverses" diminuent de facon visible.
- Le rythme de livraison reste au moins equivalent a aujourd'hui.

---

## 12. Conclusion

La bonne direction pour Niamoto est une **architecture evolutive et pragmatique**:
- conserver la force du monolithe modulaire,
- installer une separation nette des responsabilites,
- et durcir la fiabilite operationnelle.

Ce choix maximise la valeur produit a court terme tout en preparant une base saine pour les prochaines annees.
