# Niamoto - Plan d'Execution Architecture (2026-2027)

**Date**: 2026-02-11
**Perimetre**: GUI, API, Core, operations techniques
**Horizon**: T1 2026 -> T1 2027
**But**: executer la cible architecture sans ralentir la roadmap produit

---

## 1. Cadre d'execution

### 1.1 Principe

Execution incrementale par trimestres, avec des lots deployables:

- pas de big-bang,
- pas de gel produit,
- chaque lot livre une valeur operationnelle mesurable.

### 1.2 Gouvernance

- **SteerCo technique (mensuel)**: CTO, Head of Product, Lead Engineer.
- **Architecture sync (hebdo)**: Tech Lead Core, Tech Lead API, Tech Lead UI, QA Lead, DevOps.
- **Rituel ADR (bi-hebdo)**: decisions structurelles arbitrees rapidement.

### 1.3 Owners proposes (roles)

- **Owner A - Tech Lead Core**: Domain + plugins + contrats metier.
- **Owner B - Tech Lead API**: couche application/use-cases + routers + contrats API.
- **Owner C - Tech Lead UI**: adaptation schema UI + parcours critiques front.
- **Owner D - DevOps/SRE**: observabilite, run, resilience jobs.
- **Owner E - QA Lead**: strategie de tests, non-regression, qualite release.
- **Owner F - Product Manager**: priorisation et alignement roadmap produit.

Note: les owners sont proposes par role; a mapper sur des noms lors du kickoff.

---

## 2. Backlog structurant (epics)

### EPIC 1 - Frontieres Domain/Application/Adapters
- Extraire les use-cases critiques hors routers.
- Definir conventions de dependances.
- Mettre en place revues d'architecture sur nouveaux modules.

**Owner principal**: Owner B
**Co-owners**: Owner A, Owner C

### EPIC 2 - Jobs resilients
- Standardiser le modele de job.
- Persister etat/progression/erreurs.
- Uniformiser start/pause/resume/cancel/retry.

**Owner principal**: Owner B
**Co-owner**: Owner D

### EPIC 3 - Securite structurelle
- Centraliser policies de chemins fichiers.
- Durcir validation des acces reseau/externes.
- Ajouter tests de securite automatises.

**Owner principal**: Owner B
**Co-owners**: Owner D, Owner E

### EPIC 4 - Contrats et versioning
- Versionner API/schema/config sensibles.
- Introduire politique de compatibilite et de deprecation.
- Publier changelog de contrat.

**Owner principal**: Owner A
**Co-owners**: Owner B, Owner C

### EPIC 5 - Observabilite et fiabilite
- Correlation ID, logs structures, metriques jobs/endpoints.
- Dashboard technique et alertes minimales.
- Postmortem standardises sur incidents.

**Owner principal**: Owner D
**Co-owner**: Owner E

### EPIC 6 - Qualite et tests
- Renforcer tests use-cases et integration adapters.
- Ajouter e2e front sur parcours critiques.
- Definir gates CI sur risques architecturels.

**Owner principal**: Owner E
**Co-owners**: Owner B, Owner C

---

## 3. Planning trimestriel

### T1 2026 (fev-mar 2026) - Fondations

### Objectif
Mettre en place les fondations d'architecture et de gouvernance sans perturber la livraison feature.

### Milestones
1. **M1.1 - Architecture guardrails**
- Conventions de modules et dependances formalisees.
- 2 ADR minimales: frontieres couches + politique jobs.

2. **M1.2 - Job contract v1**
- Modele unifie de job (etat/progression/erreurs).
- API de controle normalisee pour au moins 1 workflow critique.

3. **M1.3 - Security baseline**
- Librairie interne de path policies (allowlist roots + normalization).
- Adoption sur endpoints fichiers les plus critiques.

4. **M1.4 - Observability baseline**
- Correlation id et logs structures sur workflows critiques.
- Dashboard minimal "sante jobs + erreurs".

### Owners
- M1.1: Owner B (A/C)
- M1.2: Owner B (D)
- M1.3: Owner B (D/E)
- M1.4: Owner D (B/E)

### Definition of Done (trimestre)
- conventions approuvees et appliquees sur nouveaux changements,
- au moins 1 flux critique porte par use-case + job contract v1,
- policies securite actives sur perimetre prioritaire,
- dashboard technique disponible.

---

### T2 2026 (avr-juin 2026) - Migration des flux critiques

### Objectif
Basculer progressivement les workflows coeur vers la couche application/use-cases.

### Milestones
1. **M2.1 - Use-cases import/transform/export**
- migration progressive de la logique applicative hors routers.
- tests de non-regression associes.

2. **M2.2 - Job persistence v2**
- persistence fiable pour jobs critiques.
- reprise basique apres restart.

3. **M2.3 - UI contract boundary**
- adaptateur schema metier -> schema UI explicite.
- reduction du couplage direct core <-> composants UI.

4. **M2.4 - Securite et tests**
- extension des policies securite a tous endpoints fichiers/reseau critiques.
- test suite securite de base en CI.

### Owners
- M2.1: Owner B (A/E)
- M2.2: Owner B (D)
- M2.3: Owner C (A/B)
- M2.4: Owner E (B/D)

### Definition of Done (trimestre)
- import/transform/export pilotes par use-cases sur le chemin principal,
- jobs critiques persistants et recuperables au redemarrage,
- frontiere UI contract documentee et appliquee,
- tests securite critiques en CI.

---

### T3 2026 (juil-sept 2026) - Versioning et industrialisation

### Objectif
Stabiliser les interfaces et renforcer la gouvernance plugin/contrats.

### Milestones
1. **M3.1 - Contract versioning v1**
- versioning explicite API/schema/config sensibles.
- politique de deprecation publiee.

2. **M3.2 - Plugin governance**
- catalogue de capabilities plugins.
- checks de compatibilite minimaux.

3. **M3.3 - Reliability hardening**
- alerting prioritaire sur jobs critiques.
- playbooks incidents standardises.

4. **M3.4 - E2E coverage**
- e2e UI/API sur parcours critiques (dont operations longues).

### Owners
- M3.1: Owner A (B/C)
- M3.2: Owner A (B)
- M3.3: Owner D (E/B)
- M3.4: Owner E (C/B)

### Definition of Done (trimestre)
- contrats sensibles versionnes,
- politique de deprecation active,
- monitoring/alerting utile en operation,
- couverture e2e significative sur flux critiques.

---

### T4 2026 (oct-dec 2026) - Consolidation plateforme

### Objectif
Consolider la plateforme et preparer 2027 (scale produit + integrabilite).

### Milestones
1. **M4.1 - Headless readiness**
- workflows majeurs utilisables proprement via API/CLI/automation.

2. **M4.2 - Performance and cost hygiene**
- revue perf jobs/endpoints critiques.
- optimisation priorisee par impact.

3. **M4.3 - Architecture review 2027**
- bilan de la transformation.
- decisions de next step (continuer monolithe modulaire ou extractions ciblees).

### Owners
- M4.1: Owner B (A/C)
- M4.2: Owner D (B)
- M4.3: Owner A (CTO + F)

### Definition of Done (trimestre)
- headless mode stable pour cas prioritaires,
- gains mesurables sur latence/fiabilite,
- feuille de route architecture 2027 validee.

---

### T1 2027 (jan-mar 2027) - Extension controlee

### Objectif
Capitaliser sur la base assainie pour accelerer les evolutions metier.

### Milestones
1. **M5.1 - Product acceleration pack**
- templates/plugins livrables plus rapidement via nouveaux garde-fous.

2. **M5.2 - Selective extraction decision**
- evaluation factuelle d'extractions techniques ciblees (si necessaire).

### Owners
- M5.1: Owner F (A/B/C/E)
- M5.2: Owner A (CTO/D)

---

## 4. KPIs trimestriels (pilotage)

### 4.1 Delivery & Quality
- lead time median des changements sur flux critiques,
- taux de rollback/rework sur incidents de regression,
- taux de succes des runs CI sur suites critiques.

### 4.2 Fiabilite operationnelle
- taux d'echec jobs critiques,
- MTTR incident workflows longs,
- taux de jobs recuperes apres restart.

### 4.3 Gouvernance architecture
- pourcentage de workflows passes en use-cases,
- nombre de contrats sensibles versionnes,
- avancement backlog ADR (ouvert -> decide -> applique).

### 4.4 Securite technique
- couverture tests securite endpoints critiques,
- nombre de non-conformites path/reseau detectees en CI.

---

## 5. RACI simplifie

| Domaine | R (Responsible) | A (Accountable) | C (Consulted) | I (Informed) |
|---|---|---|---|---|
| Domain & plugins | Owner A | CTO | B, C, E | F |
| Application/use-cases | Owner B | CTO | A, C, E | F |
| UI contract & parcours | Owner C | Head of Product | A, B, E | CTO |
| Jobs/Observability/Run | Owner D | CTO | B, E | F |
| Test strategy & gates | Owner E | CTO | B, C, D | F |
| Priorisation roadmap | Owner F | Head of Product | A, B, C | CTO |

---

## 6. Risques et mitigations

1. **Risque: surcharge equipe / dispersion**
- Mitigation: limiter a 2 epics architecture actives en parallele.

2. **Risque: ralentissement feature delivery**
- Mitigation: lots petits, objectifs trimestriels explicites, feature flags.

3. **Risque: refactor sans gains visibles**
- Mitigation: KPIs obligatoires par milestone + revues mensuelles.

4. **Risque: dette de migration inachevee**
- Mitigation: Definition of Done stricte par trimestre et fermeture obligatoire des migrations partiellement engagees.

---

## 7. Prochaines actions (30 jours)

1. Nommer les owners (noms reels) pour A/B/C/D/E/F.
2. Prioriser 5 use-cases cibles pour la vague T1 2026.
3. Ouvrir et arbitrer les 2 premieres ADR (frontieres couches, modele de jobs).
4. Definir les KPIs baseline (valeurs initiales) pour mesure d'impact.
