# Niamoto - Dossier de Decision Architecture 2026-2027 (COMEX/CTO)

**Date**: 2026-02-11
**Horizon**: 12 mois
**Decision attendue**: GO sur la trajectoire d'evolution architecture

---

## 1. Message cle (en 30 secondes)

Niamoto a une base saine et operationnelle.
Le sujet n'est pas de reconstruire, mais de **fiabiliser et structurer** pour tenir la croissance produit.

Decision recommandee:

- garder le monolithe modulaire,
- renforcer ses frontieres internes (Domain / Application / Adapters),
- prioriser 4 chantiers: jobs resilients, securite structurelle, observabilite, contrats versionnes.

---

## 2. Probleme business a resoudre

Sans action architecture dans les 12 prochains mois:

- augmentation du cout de maintenance,
- multiplication des regressions transverses,
- baisse progressive de la vitesse de delivery,
- risque de fragilite operationnelle sur les workflows longs.

En synthese: le produit peut continuer d'ajouter des features, mais le risque d'instabilite monte trimestre apres trimestre.

---

## 3. Arbitrage propose

### Ce que nous faisons

1. **Evolution incrementale du monolithe modulaire** (pas de big bang).
2. **Structuration interne**:
- Domain: regles metier,
- Application: use-cases et orchestration,
- Adapters: API/DB/FS/reseau/UI mapping.
3. **Industrialisation operationnelle**:
- jobs persistants et recuperables,
- policies securite centralisees,
- observabilite standard,
- contrats API/schema/config versionnes.

### Ce que nous ne faisons pas (maintenant)

- pas de re-ecriture totale,
- pas de bascule microservices court terme.

---

## 4. Pourquoi cette option

Comparatif de decision:

- **Statut quo**: cout immediat nul, cout cache eleve a 6-12 mois.
- **Re-ecriture**: risque et cout tres eleves, interruption roadmap.
- **Microservices immediats**: complexite operationnelle prematuree.
- **Evolution incrementale (recommandee)**: meilleur ratio valeur/risque, compatible avec les engagements produit.

---

## 5. Cible 12 mois

```text
UI / CLI / API clients
    -> API Adapters
    -> Application Layer (use-cases)
    -> Domain Layer
    -> Infrastructure Adapters
```

Effets attendus:

- meilleure predictibilite des livraisons,
- baisse des incidents sur flux critiques,
- meilleure capacite d'evolution multi-canaux (desktop/web/cli/automation),
- scalabilite equipe (onboarding et maintenance facilites).

---

## 6. Plan de transformation

### Vague 1 (0-3 mois) - Fondations
- guardrails architecture + ADR prioritaires,
- modele de job unifie (v1),
- baseline securite fichiers/reseau,
- baseline observabilite.

### Vague 2 (3-6 mois) - Flux critiques
- migration progressive import/transform/export vers use-cases,
- unification du controle des jobs,
- frontiere claire schema metier -> schema UI.

### Vague 3 (6-12 mois) - Standardisation
- versioning des contrats sensibles,
- gouvernance plugins/capabilities,
- renforcement du mode headless.

---

## 7. Indicateurs de succes (COMEX)

KPIs suivis trimestriellement:

- lead time sur flux critiques (stable ou en baisse),
- regressions transverses (en baisse),
- MTTR incidents jobs longs (en baisse),
- % workflows critiques portes par use-cases (en hausse),
- % contrats sensibles versionnes (en hausse).

---

## 8. Gouvernance et responsabilites

- **Sponsor**: CTO
- **Pilotage**: Architecture + Product + Engineering
- **Rythme**: revue trimestrielle COMEX/CTO
- **Mecanisme de decision**: backlog ADR + KPI trimestriels

---

## 9. Decision demandee au COMEX/CTO

1. **Valider le GO** sur l'evolution incrementale du monolithe modulaire.
2. **Valider la priorisation 2026**:
- fiabilite jobs,
- securite structurelle,
- observabilite,
- contrats versionnes.
3. **Mandater la gouvernance trimestrielle** avec arbitrages ADR et suivi KPI.
