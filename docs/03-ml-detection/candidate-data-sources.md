# Sources de Données Candidates pour Renforcer le Benchmark ML

## Objet

Ce document liste des sources de données susceptibles de renforcer le benchmark
et le jeu d'entraînement de la détection ML de Niamoto.

L'objectif n'est pas d'accumuler des données "au hasard". L'objectif est
d'élargir le benchmark avec des données qui ressemblent aux cas que Niamoto doit
réellement bien servir :

- inventaires et relevés tropicaux ou subtropicaux ;
- jeux de données semi-standard ou non standardisés ;
- exports tabulaires écologiques réels ;
- jeux de données GBIF, en particulier dans leur noyau standard et leurs
  extensions utiles ;
- données des instances réellement testées.

## Ce qu'on cherche en priorité

Les sources les plus utiles pour la détection ML sont celles qui apportent :

- de **vrais headers terrain** ;
- des colonnes **non triviales** ;
- des formats **tabulaires** (CSV, TSV, DWC-A, exports de portails) ;
- des vocabulaires **métier** ou **locaux** ;
- des valeurs réalistes ;
- une diversité de conventions sans tomber dans des schémas trop exotiques ou
  trop éloignés du produit.

En revanche, les jeux dérivés purement cartographiques, les rasters, ou les
produits déjà fortement agrégés sont généralement de faible valeur pour le
benchmark de détection de colonnes.

## Stratégie de sélection

Je recommande de classer les sources en trois groupes :

### Priorité A — Très proches de la cible produit

À intégrer en premier :

- jeux tropicaux forestiers réels ;
- relevés de Guyane, Gabon, Cameroun, Nouvelle-Calédonie si disponibles ;
- données d'instances réellement testées ;
- exports GBIF ciblés par région et par style.

### Priorité B — Voisins très utiles

À intégrer ensuite :

- grands réseaux forestiers tropicaux ;
- réseaux de placettes végétation ;
- bases africaines et pan-tropicales avec données d'occurrence ou de placettes.

### Priorité C — Élargissement contrôlé

Utiles pour la robustesse, mais secondaires :

- jeux de traits végétaux ;
- marine / littoral si cela devient un besoin réel ;
- régions plus éloignées écologiquement mais encore compatibles avec le produit.

## Shortlist recommandée

## 1. Données locales et d'instances réelles

### 1. Jeux de données des instances testées actuellement

- **Type** : exports tabulaires réels, potentiellement non standardisés
- **Accès** : interne
- **Valeur ML** : maximale
- **Pourquoi** : ce sont les cas les plus proches du produit, avec les vraies
  conventions de colonnes, les vrais problèmes de qualité, et les vraies
  attentes utilisateur
- **Priorité** : A+

Recommandation :

- les intégrer explicitement dans le gold set quand c'est possible ;
- les tagger comme sous-benchmark principal ;
- suivre séparément les résultats par instance.

## 2. Guyane / Amazonie française

### 2. Paracou / ForestScan (CIRAD Dataverse)

- **Région** : Guyane française
- **Type** : tree census data, structure forestière, placettes tropicales
- **Accès** : open data via Dataverse
- **Format attendu** : CSV + métadonnées
- **Pourquoi** : très proche des besoins terrain tropicaux ; excellent candidat
  pour enrichir la partie tropicale non standard du benchmark
- **Priorité** : A
- **Sources** :
  - [Paracou Dataverse](https://dataverse.cirad.fr/dataverse/paracou)
  - [ForestScan data paper (ESSD 2026)](https://essd.copernicus.org/articles/18/1243/2026/essd-18-1243-2026.html)

### 3. Guyafor network — Trinité

- **Région** : Guyane française
- **Type** : forest censuses
- **Accès** : métadonnées et description publiques ; CSV census principal
  restreint, accès sur demande
- **Pourquoi** : utile pour varier les conventions de placettes et les variables
  tropicales tout en restant dans un écosystème proche de Paracou
- **Priorité** : A
- **Source** :
  - [Guyafor / Trinite Forest Censuses](https://dataverse.cirad.fr/dataverse/guyafor)

### 4. Guyafor network — Trésor

- **Région** : Guyane française
- **Type** : tree census in permanent forest plots
- **Accès** : métadonnées et description publiques ; CSV census principal
  restreint, accès sur demande
- **Pourquoi** : complète Paracou/Trinité avec un autre contexte forestier
  tropical de Guyane
- **Priorité** : A
- **Source** :
  - [Tresor Forest Censuses (Guyafor)](https://dataverse.cirad.fr/dataverse/ecofog)

## 3. Afrique centrale et tropicale

### 5. ForestPlots.net — Lopé, Gabon

- **Région** : Gabon
- **Type** : tree census tropical forest plots
- **Accès** : accès encadré, demande/collaboration
- **Pourquoi** : très proche de la cible produit ; utile pour des colonnes de
  parcelles, arbres, biomasse, diamètre, mortalité, etc.
- **Priorité** : A
- **Sources** :
  - [ForestPlots.net - Working with data](https://forestplots.net/en/join-forestplots/working-with-data)
  - [ForestScan data paper (section Lopé)](https://essd.copernicus.org/articles/18/1243/2026/essd-18-1243-2026.html)

### 6. RAINBIO

- **Région** : Afrique tropicale, incluant Gabon/Cameroun
- **Type** : occurrences de plantes vasculaires tropicales
- **Accès** : base publiée ; accès documenté publiquement
- **Pourquoi** : excellent candidat pour renforcer la couverture Afrique
  tropicale, en particulier si l'on veut enrichir taxonomie, localité, habitat
  et champs associés
- **Priorité** : A
- **Sources** :
  - [RAINBIO data paper via GBIF](https://www.gbif.org/en/data-use/83286)
  - [RAINBIO official site](https://gdauby.github.io/rainbio/)

### 7. SEOSAW plot network

- **Région** : Afrique subsaharienne
- **Type** : tree and stem measurements in woodland / savanna plots
- **Accès** : accès sur demande ; échantillon disponible
- **Pourquoi** : utile si vous voulez élargir au-delà de la forêt dense
  tropicale tout en restant sur des données de terrain végétation/boisement
- **Priorité** : B
- **Source** :
  - [SEOSAW data access](https://seosaw.github.io/data)

## 4. GBIF ciblé par région et par style

### 8. GBIF regional occurrence downloads

- **Région** : Nouvelle-Calédonie, Guyane, Gabon, Cameroun, puis autres régions
- **Type** : occurrences standardisées Darwin Core
- **Accès** : via portal + API + snapshots
- **Pourquoi** : GBIF reste une priorité produit, mais il faut le traiter comme
  plusieurs sous-corpus :
  - noyau standard (`gbif_core_standard`)
  - colonnes étendues (`gbif_extended`)
  - sélections régionales prioritaires
- **Priorité** : A
- **Sources** :
  - [GBIF API Downloads](https://techdocs.gbif.org/en/data-use/api-downloads)
  - [GBIF download formats](https://techdocs.gbif.org/en/data-use/download-formats)
  - [GBIF open data on AWS](https://registry.opendata.aws/gbif/)

État actuel :

- un premier lot `gbif_targeted/` a été récupéré sur `NC`, `GF`, `GA`, `CM`
- ce lot est utile mais reste très observationnel
- il ne doit pas être confondu avec un GBIF institutionnel

### 9. GBIF — Nouvelle-Calédonie ciblée

- **Région** : Nouvelle-Calédonie
- **Type** : occurrences GBIF régionales
- **Accès** : via requêtes GBIF ciblées
- **Pourquoi** : permet d'ajouter une masse de données standardisées proches de
  la priorité géographique, même si cela ne remplace pas les jeux terrain non
  standard
- **Priorité** : A
- **Source indicatrice** :
  - [GBIF country report New Caledonia](https://analytics-files.gbif.org/country/NC/GBIF_CountryReport_NC.pdf)

### 10. GBIF — Territoires français ultramarins

- **Région** : Guyane française, Nouvelle-Calédonie, autres outre-mer
- **Type** : occurrence downloads multi-pays/territoires
- **Accès** : via requêtes de téléchargement GBIF
- **Pourquoi** : utile pour construire des sous-corpus ciblés par territoire et
  tester la robustesse du pipeline sur des zones d'intérêt
- **Priorité** : B
- **Exemple de téléchargement GBIF** :
  - [Example occurrence download with French overseas territories](https://www.gbif.org/occurrence/download/0025173-250802193616735)

### 10bis. GBIF ciblé institutionnel

- **Région** : en priorité Gabon et Cameroun à ce stade
- **Type** : occurrences GBIF plus proches des collections et herbaria
- **Accès** : via API publique + filtrage local
- **Pourquoi** : complète le lot régional général avec un signal plus proche des
  exports institutionnels réels
- **Filtre recommandé** :
  - `basisOfRecord in {PRESERVED_SPECIMEN, MATERIAL_SAMPLE, OCCURRENCE}`
  - présence d'au moins un champ institutionnel (`institutionCode`,
    `collectionCode`, `institutionID`, `collectionKey`)
  - exclusion des grands jeux observationnels (`iNaturalist`, `observation.org`,
    `Pl@ntNet`, etc.)
- **État actuel** :
  - `gabon` : bon rendement
  - `cameroon` : bon rendement
  - `new_caledonia` : très faible rendement dans les premiers résultats
  - `guyane` : très faible rendement dans les premiers résultats

## 5. Réseaux forestiers et végétation plus larges

### 11. ForestGEO Data Portal

- **Région** : réseau mondial de placettes forestières
- **Type** : forest plots, inventaires standardisés
- **Accès** : request portal ; données parfois publiques, parfois sur approbation
- **Pourquoi** : très forte valeur si l'on veut enrichir le benchmark avec des
  inventaires forestiers comparables entre régions
- **Priorité** : B
- **Source** :
  - [ForestGEO Data Portal](https://ctfs.si.edu/datarequest/)

### 12. sPlotOpen

- **Région** : global
- **Type** : vegetation plots, co-occurrence species, métadonnées de placettes
- **Accès** : open access
- **Pourquoi** : bonne source pour élargir le benchmark en placettes végétation
  et métadonnées environnementales, utile si Niamoto veut servir autre chose que
  des occurrences brutes
- **Priorité** : B
- **Source** :
  - [sPlotOpen](https://www.idiv.de/research/projects/splot/splotopen-splot/)

### 13. AusPlots / TERN

- **Région** : Australie
- **Type** : vegetation plots / rangelands / survey protocols
- **Accès** : open data / portail TERN selon jeux
- **Pourquoi** : moins proche des régions prioritaires, mais très utile pour
  tester des relevés végétation structurés hors tropiques humides
- **Priorité** : C
- **Source** :
  - [TERN / AusPlots context](https://www.tern.org.au/auscribe-ausplots-field-survey-app/)

## 6. Données de traits et enrichissement sémantique

### 14. TRY Plant Trait Database

- **Région** : global
- **Type** : plant traits
- **Accès** : portail dédié, aujourd'hui très ouvert sur une grande partie des
  données
- **Pourquoi** : moins utile pour le benchmark de détection brute de colonnes
  que pour enrichir les concepts et les affordances autour des traits
- **Priorité** : B/C
- **Sources** :
  - [TRY Home](https://www.try-db.org/TryWeb/Home.php)
  - [TRY data portal](https://www.try-db.org/TryWeb/Database.php)
  - [TRY access / openness](https://www.try-db.org/TryWeb/About.php)

## 7. Marine / littoral si besoin futur

### 15. OBIS

- **Région** : global, incluant Nouvelle-Calédonie
- **Type** : occurrences marines, parfois eDNA, extensions eMoF
- **Accès** : open access, exports complets et API
- **Pourquoi** : pertinent si le produit doit aussi bien gérer le littoral, le
  lagonaire, ou des jeux marins / récifaux de Nouvelle-Calédonie
- **Priorité** : B/C selon besoin
- **Sources** :
  - [OBIS data access](https://obis.org/data/access)
  - [OBIS manual / downloads](https://manual.obis.org/access)
  - [New Caledonia eDNA example dataset](https://obis.org/dataset/33926ad1-6fb9-4299-ad94-1ce5c23773d3)

## Recommandation de priorisation

## Lot 1 — à faire en premier

- données des instances réellement testées
- Paracou / Guyafor (Guyane)
- Trinité / Trésor (Guyane)
- GBIF ciblé Nouvelle-Calédonie / Guyane / Gabon / Cameroun
- ForestPlots Lopé (si accès possible)
- RAINBIO

## Lot 2 — à faire juste après

- split régional GBIF `core_standard` / `extended`
- ForestGEO
- SEOSAW
- sPlotOpen

## Lot 3 — à intégrer seulement si utile

- TRY
- OBIS
- AusPlots

## Comment les utiliser dans le benchmark

Je recommande de ne pas tout mélanger dans un seul score.

### Benchmark principal

Doit refléter la cible produit :

- jeux des instances testées
- données tropicales proches de l'usage
- Guyane / Afrique tropicale / Nouvelle-Calédonie
- GBIF ciblé

### Garde-fous

À surveiller sans leur donner tout le poids du score principal :

- inventaires forestiers très codés
- sous-benchs rares ou petits
- régions éloignées du coeur produit

### Diagnostics

À utiliser pour comprendre, pas pour décider seuls :

- jeux très standardisés
- petits splits homogènes
- corpus très spécialisés

## Critères de sélection avant intégration

Avant d'intégrer une nouvelle source, vérifier :

- le format est-il tabulaire et exploitable rapidement ?
- les headers apportent-ils une vraie variation ?
- les valeurs sont-elles réalistes et suffisamment propres ?
- la licence permet-elle l'usage dans le benchmark local ?
- le jeu est-il proche de la cible produit ou seulement "intéressant" ?

## Décision recommandée

Si on veut être efficace, il faut commencer par des sources qui changent
réellement la qualité du benchmark sur la cible produit.

Ma recommandation nette :

1. **Formaliser les datasets d'instances réelles**
2. **Ajouter Guyane tropicale ouverte (Paracou / Guyafor)**
3. **Ajouter Afrique tropicale proche de l'usage (RAINBIO + ForestPlots si possible)**
4. **Construire des téléchargements GBIF ciblés par région**
5. **Élargir seulement ensuite**

## Références

- [Paracou Dataverse](https://dataverse.cirad.fr/dataverse/paracou)
- [ForestScan ESSD 2026](https://essd.copernicus.org/articles/18/1243/2026/essd-18-1243-2026.html)
- [Guyafor Dataverse](https://dataverse.cirad.fr/dataverse/guyafor)
- [ForestPlots.net](https://forestplots.net/en/join-forestplots/working-with-data)
- [RAINBIO official site](https://gdauby.github.io/rainbio/)
- [RAINBIO via GBIF](https://www.gbif.org/en/data-use/83286)
- [ForestGEO Data Portal](https://ctfs.si.edu/datarequest/)
- [sPlotOpen](https://www.idiv.de/research/projects/splot/splotopen-splot/)
- [TRY Database](https://www.try-db.org/TryWeb/Home.php)
- [OBIS data access](https://obis.org/data/access)
- [GBIF API downloads](https://techdocs.gbif.org/en/data-use/api-downloads)
- [GBIF download formats](https://techdocs.gbif.org/en/data-use/download-formats)
- [GBIF open data](https://registry.opendata.aws/gbif/)
