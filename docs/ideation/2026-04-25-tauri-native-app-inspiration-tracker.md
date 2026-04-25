---
date: 2026-04-25
topic: tauri-native-app-inspiration
status: active
---

# Suivi: inspirations Tauri et expérience desktop native

## Objectif

Ce document suit les idées issues de l’analyse de Tolaria et d’autres
applications Tauri qui paraissent plus natives, plus rapides ou plus fluides que
Niamoto.

Le but n’est pas de copier une architecture complète. Le but est d’identifier
des détails à fort effet produit qui peuvent rendre Niamoto plus crédible comme
application desktop locale, sans casser son modèle actuel :

- projet local ;
- workflows `import -> transform -> export` ;
- édition du site ;
- publication ;
- backend Python/FastAPI ;
- shell Tauri avec frontend React.

## Sources à suivre

| Application | Dépôt | Pourquoi elle est pertinente |
|---|---|---|
| Tolaria | https://github.com/refactoringhq/tolaria | Référence initiale. Démarrage perçu très propre, shell dense, sensation desktop forte, moins “site web dans une webview”. |
| Yaak | https://github.com/mountain-loop/yaak | API client Tauri/Rust/React. Intéressant pour les workspaces locaux, les variables, les plugins et les raccourcis. |
| GitButler | https://github.com/gitbutlerapp/gitbutler | Application desktop complexe avec backend Rust, historique d’actions, états de travail et forte logique locale. |
| Spacedrive | https://github.com/spacedriveapp/spacedrive | Gros produit local-first avec index local, cache, client typé et expérience multi-surface. |
| Duckling | https://github.com/l1xnan/duckling | Viewer rapide pour CSV/Parquet/DB. Pertinent pour tables lourdes et previews de données. |
| Kanri | https://github.com/kanriapp/kanri | App offline locale simple. Pertinente pour persistance, raccourcis, backups et simplicité du modèle. |
| RapidRAW | https://github.com/CyberTimon/RapidRAW | Exemple d’UI Tauri orientée performance et traitement lourd local. |
| NeoHtop | https://github.com/Abdenasser/neohtop | Exemple d’UI temps réel dense et très réactive dans Tauri. |

## Scan ciblé du 2026-04-25

### Yaak

Source : https://github.com/mountain-loop/yaak

Points observés :

- stack Tauri, Rust et React ;
- app offline-first, sans cloud lock-in ;
- modèle workspace avec collections, variables d’environnement, secrets dans le
  keychain OS et miroir possible vers le filesystem ;
- architecture très orientée plugins : auth, importeurs, template functions,
  filtres, thèmes ;
- frontend React récent avec TanStack Query, TanStack Router, TanStack Virtual
  et CodeMirror.

Inspiration réaliste pour Niamoto :

- renforcer les workflows projet comme objets locaux explicites ;
- mieux exposer les importeurs, exporteurs et configurations comme actions
  réutilisables ;
- garder l’idée de plugins, mais côté produit éviter une surface trop technique
  pour les utilisateurs métier.

### GitButler

Source : https://github.com/gitbutlerapp/gitbutler

Points observés :

- desktop Tauri avec UI Svelte/TypeScript et backend Rust ;
- même moteur Rust utilisé côté app desktop et CLI ;
- intégrations forge, PR, CI et actions Git complexes présentées comme un état
  de travail local ;
- dépendances desktop utiles : Tauri store, updater, deep-link, filesystem,
  shell et log.

Inspiration réaliste pour Niamoto :

- traiter `import`, `transform`, `export`, `publish` comme des actions de
  workflow avec statut, durée, résultat et erreurs ;
- construire une timeline locale des actions récentes avant d’ajouter des
  automatisations plus ambitieuses ;
- éviter de cacher les étapes complexes : les rendre inspectables, rejouables
  ou au moins clairement traçables.

### Spacedrive

Source : https://github.com/spacedriveapp/spacedrive

Points observés :

- Tauri 2, React, Vite, TanStack Query, Tailwind et design system partagé ;
- core Rust local-first, SQLite, actions/queries typées et génération de types
  TypeScript ;
- architecture CQRS/DDD avec opérations enregistrées comme actions ou queries ;
- opérations transactionnelles prévisualisables avant exécution, puis
  transformées en jobs durables.

Inspiration réaliste pour Niamoto :

- formaliser progressivement une notion d’action de workflow côté GUI ;
- commencer petit : journal local des jobs/actions et prérequis visibles avant
  lancement ;
- ne pas viser une refonte backend CQRS, mais reprendre le principe de
  commandes explicites, typées et traçables.

## Ce qui a déjà été testé dans Niamoto

| Sujet | Statut | Notes |
|---|---|---|
| Shell desktop plus natif | Testé et validé | Densification du chrome, barre de statut basse, retrait de redondances et meilleure continuité visuelle. Voir `docs/superpowers/specs/2026-04-23-desktop-shell-workbench-trial-design.md`. |
| Breadcrumbs moins présents | Testé | Les breadcrumbs ont été retirés ou réduits là où ils surchargeaient l’interface. |
| Sidebar plus utile par défaut | Testé | Largeur minimale corrigée pour rendre le type de page et les actions visibles. |
| Markdown authoring content-first | Testé | Passage vers une édition plus directe, avec modes `Write`, `Preview` et `Source`. Voir `docs/superpowers/specs/2026-04-23-site-markdown-authoring-design.md`. |
| Tables markdown | Testé | Amélioration du rendu des tableaux pour éviter l’affichage brut inutile. |
| Project picker | Testé | Correction de l’ouverture de projets et ajustement du hover pour rester plus neutre et lisible. |
| Crash collections React depth | Corrigé | Garde-fous ajoutés sur les updates redondants et meilleur reporting du composant fautif. |
| Mémoire de route par projet | Livré | `main` contient la restauration de la dernière route sûre par `projectScope`. Commit `9ef712ee`. |
| Préférences de vues par projet | Livré localement | Branche `desktop-context-tabs` mergée dans `main` en fast-forward. Couvre les onglets/panneaux simples, sans restauration de sélections métier fines. Commit `4af36604`. |
| Palette de commandes workflow | Livré localement | Branche `command-palette-workflows` mergée dans `main` en fast-forward. Objectif : transformer `Cmd+K` en accès rapide aux workflows Niamoto sans lancer directement les jobs longs. Commit `9f027000`. |
| Mesure des listes lourdes | Livré localement | Branche `list-performance-metrics` mergée dans `main`. Instrumentation dev-only conservée, avec premiers signaux orientant plutôt vers Data Explorer que Collections. Commit `b475a6c7`. |
| Optimisation table Data Explorer | Livré | Branche `data-explorer-table-performance` mergée dans `main`. Première tranche sans dépendance : tableau mémoïsé et virtualisation verticale légère au-dessus de 60 lignes. Commit `da402378`. |
| Scan Yaak/GitButler/Spacedrive | Documenté | Les trois références orientent la suite vers un historique local des workflows/actions plutôt que vers une nouvelle refonte visuelle. |
| Historique workflows lecture seule | En cours | Branche `workflow-history-view`. Ajout d’une page `/tools/history`, accès `Cmd+K` et correction de l’historique backend pour inclure le dernier job terminal. |

## Idées candidates

### 1. Mémorisation du contexte desktop

**Statut : phases 1 et 2 livrées localement.**
**Coût estimé : faible à moyen.**
**Risque : faible si les valeurs sont restaurées prudemment.**

Persister et restaurer le contexte local de travail :

- dernier projet ouvert ;
- dernière section visitée ;
- dernier onglet actif par module ;
- tailles de panneaux ;
- sélection courante quand elle existe encore ;
- mode d’affichage pertinent, par exemple preview/source/write.

Pourquoi c’est intéressant :

- effet desktop immédiat ;
- faible complexité produit ;
- renforce l’idée que Niamoto est une application locale qui reprend là où
  l’utilisateur s’est arrêté ;
- ne demande pas de nouvelle fonctionnalité métier.

Points de vigilance :

- ne jamais planter si une entité restaurée n’existe plus ;
- ne pas restaurer une route invalide après changement de projet ;
- garder une séparation claire entre préférences globales et état par projet.

Décision d’implémentation :

- la mémoire desktop doit être attachée à un `projectScope`, pas globale ;
- la première brique mémorise la dernière route sûre par projet et est mergée
  dans `main` ;
- la restauration se fait seulement au démarrage sur la route d’accueil, pour
  ne pas empêcher l’utilisateur de revenir volontairement au dashboard ;
- la deuxième brique mémorise les préférences de vues simples par projet :
  onglets Collections, Data Explorer, Config Editor, Publish History, panneau
  compact et device de preview Publish ;
- les sélections fines par module seront ajoutées ensuite seulement si elles
  ont un vrai bénéfice utilisateur.

Découpage validé :

| Phase | Statut | Périmètre | Règle de prudence |
|---|---|---|---|
| Phase 1 | Livrée sur `main` | Dernière route sûre par projet | Restaurer seulement depuis `/`, et uniquement vers des routes connues. |
| Phase 2 | Livrée localement sur `main` | Préférences de vues simples par projet | Stocker seulement des valeurs typées et autorisées. |
| Phase 3 | À décider | Sélections fines par module | Ne pas restaurer d’ID ou d’entité sans vérifier qu’ils existent encore. |
| Phase 4 | À mesurer | Tailles de panneaux hors Site Builder | Ne pas généraliser avant d’identifier les panneaux vraiment utiles. |

Ce qui doit rester global :

- thème ;
- langue d’interface ;
- activation de l’ouverture automatique du dernier projet ;
- raccourcis et préférences shell qui ne dépendent pas du dataset.

Ce qui doit rester par projet :

- dernière route ;
- onglets et panneaux de travail ;
- device de preview Publish ;
- layout du Site Builder ;
- futures sélections métier seulement si elles peuvent être validées contre les
  données du projet courant.

### 2. Virtualisation ciblée des listes lourdes

**Statut : mesure en cours avant implémentation.**
**Coût estimé : moyen.**
**Risque : moyen si appliqué trop largement.**

Utiliser `react-virtuoso` ou équivalent uniquement là où les volumes sont
réellement visibles :

- tables de sources/imports ;
- grands catalogues de widgets ;
- historiques longs ;
- listes d’entités dans collections ;
- previews de fichiers tabulaires.

Pourquoi c’est intéressant :

- retrouve la fluidité des apps Tauri très réactives ;
- utile sur Windows et machines modestes ;
- évite d’optimiser à l’aveugle tout le frontend.

Critère d’entrée :

- identifier une liste qui dépasse clairement les performances acceptables ;
- mesurer le nombre d’éléments et le coût de rendu ;
- corriger un cas réel, pas une abstraction.

Décision de première tranche :

- ajouter une instrumentation dev-only commune exposée dans
  `window.__NIAMOTO_RENDER_METRICS__` ;
- persister aussi les 200 dernières mesures dans `localStorage` sous
  `niamoto:dev-render-metrics`, pour pouvoir les relire après une session de
  test manuel ;
- commencer par mesurer les listes suivantes : tables et rows du Data Explorer,
  exports du Data Explorer, historique Publish, arbre Collections, contenu de
  collection, liste de widgets, previews actives, sources, colonnes et champs de
  schéma ;
- ne pas introduire `react-virtuoso` avant d’avoir identifié un écran réel où
  le coût de rendu est visible.

Résultats provisoires :

- Collections ne justifie pas une virtualisation à ce stade : environ 20 widgets
  et rendus majoritairement sous quelques dizaines de millisecondes ;
- Data Explorer montre des signaux plus nets, notamment certaines tables de
  100 lignes et 13 à 21 colonnes pouvant atteindre environ 50 à 90 ms ;
- garder l’instrumentation dev-only, mais relever les seuils Collections pour
  éviter de polluer les sessions de développement normales.

Première optimisation Data Explorer :

- extraire le tableau de résultats dans un composant mémoïsé pour éviter de le
  recalculer quand l’utilisateur tape dans le champ de recherche ;
- stabiliser les callbacks transmis au tableau ;
- virtualiser verticalement les pages de résultats au-dessus de 60 lignes, sans
  ajouter de dépendance externe ;
- garder `react-virtuoso` comme option seulement si cette optimisation ne suffit
  pas sur les tables réellement lentes.

### 3. Command palette comme vrai centre d’action

**Statut : tranche courte en cours.**
**Coût estimé : moyen.**
**Risque : faible si elle reste additive.**

Transformer progressivement `Cmd+K` en surface d’action centrale :

- ouvrir les sections ;
- lancer import/transform/export ;
- rechercher une page du site ;
- ouvrir un projet récent ;
- accéder aux actions de diagnostic ;
- afficher les raccourcis disponibles.

Pourquoi c’est intéressant :

- rapproche Niamoto des apps desktop modernes ;
- donne une vitesse experte sans changer la navigation principale ;
- peut réduire la charge cognitive des écrans très riches.

Point important :

- la palette ne doit pas devenir un remplacement de navigation pour les
  nouveaux utilisateurs. Elle doit être un accélérateur.

Décision de première tranche :

- ajouter des raccourcis de navigation actionnables vers les workflows
  `import`, `collections`, `site`, `publish`, `deploy`, `history` ;
- ajouter des deep links vers les onglets `import.yml`, `transform.yml` et
  `export.yml` du Config Editor ;
- ne pas exécuter directement import, transform, export ou deploy depuis la
  palette tant que la confirmation, les prérequis et le suivi de job ne sont
  pas clarifiés.

### 4. Historique local des actions et jobs

**Statut : tranche 1 en cours.**
**Coût estimé : moyen à élevé.**
**Risque : moyen.**

Créer une timeline locale claire :

- imports lancés ;
- transformations ;
- exports ;
- publications ;
- erreurs ;
- fichiers générés ;
- durée et statut.

Inspirations principales :

- GitButler pour la présentation d’un état de travail complexe ;
- Yaak pour les workspaces locaux et l’historique d’actions ;
- Niamoto lui-même, qui a déjà des signaux dispersés de jobs, fraîcheur et
  diagnostics.

Pourquoi c’est intéressant :

- améliore la confiance dans les workflows longs ;
- aide au debug utilisateur ;
- réduit le besoin de lire les logs bruts.

Décision proposée après le scan :

- commencer par un historique lecture seule des dernières actions connues ;
- inclure au minimum : type d’action, cible, statut, durée, horodatage, message
  d’erreur et liens vers fichiers générés quand ils existent ;
- ne pas lancer d’actions longues depuis la palette tant que cet historique et
  les prérequis ne sont pas visibles ;
- intégrer l’accès depuis `Cmd+K` seulement comme raccourci vers la page de
  suivi, pas comme exécution directe.

Tranche 1 :

- ajouter une page `/tools/history` lisible depuis la palette de commandes ;
- réutiliser `/pipeline/history` et `/pipeline/status` sans nouveau modèle
  backend ;
- inclure le dernier job terminal encore stocké dans `active_job.json`, sinon
  l’historique visible est toujours en retard d’une action ;
- afficher d’abord type, cible, statut, durée, date relative, message d’erreur
  et résumé des métriques disponibles ;
- garder les liens vers fichiers générés pour une tranche ultérieure, car les
  payloads actuels ne les exposent pas de façon stable.

### 5. Inspecteur contextuel léger

**Statut : différé.**
**Coût estimé : moyen.**
**Risque : élevé côté pertinence produit.**

Un inspecteur pourrait afficher des informations contextuelles sur la sélection
courante :

- page du site sélectionnée ;
- widget sélectionné ;
- source de données utilisée ;
- statut de fraîcheur ;
- erreurs ou avertissements liés ;
- raccourcis d’actions possibles.

Pourquoi c’est intéressant :

- peut rendre les surfaces complexes plus lisibles ;
- crée une logique desktop de sélection + propriétés.

Pourquoi c’est différé :

- le contenu vraiment utile n’est pas encore assez évident ;
- risque de créer un panneau de plus sans bénéfice net ;
- mieux vaut d’abord améliorer les flows existants.

### 6. Édition markdown plus native

**Statut : partiellement testé.**
**Coût estimé : moyen.**
**Risque : moyen.**

Continuer l’amélioration de l’éditeur actuel avant toute migration :

- slash menu plus évident ;
- insertion de blocs plus directe ;
- meilleure édition des tableaux ;
- mode écriture plus immédiat ;
- séparation plus claire entre contenu et configuration.

Décision actuelle :

- ne pas remplacer l’éditeur tant que le shell autour de l’édition n’a pas été
  poussé assez loin ;
- comparer avec Tolaria surtout sur les détails d’interaction inline, pas sur
  la stack complète.

### 7. Preview-first editing dans Collections

**Statut : différé.**
**Coût estimé : moyen à élevé.**
**Risque : élevé.**

Idée :

- afficher la collection comme une preview proche de la page finale ;
- permettre de cliquer un widget pour l’éditer ;
- rendre la structure plus évidente sans passer par une liste abstraite.

Pourquoi c’est intéressant :

- rapproche configuration et résultat final ;
- peut rendre Collections moins technique.

Pourquoi c’est différé :

- la partie actuelle fonctionne déjà ;
- la bonne représentation n’est pas encore claire ;
- risque de refondre trop large pour un gain incertain.

## Prochaine séquence proposée

### Court terme

1. Pousser `main` après validation des branches mergées localement.
   Statut : fait le 2026-04-25, `main` poussé jusqu’à `da402378`.
2. Tester manuellement deux projets récents pour vérifier que la mémoire ne se
   mélange pas entre projets.
3. Reprendre les mesures Data Explorer après optimisation de table pour décider
   si une virtualisation plus robuste est nécessaire.
   Statut : première mesure validée, `taxons` est passé de 89 ms à 40 ms sur
   100 lignes et 21 colonnes.
4. Faire un scan ciblé de Yaak, GitButler et Spacedrive pour extraire des
   patterns concrets, pas seulement des impressions.
   Statut : fait le 2026-04-25.

### Moyen terme

1. Renforcer la command palette avec des actions réelles.
2. Construire un historique local des actions/jobs.
   Candidat désormais prioritaire avant l’exécution directe d’actions longues.
3. Revenir sur Collections seulement après avoir clarifié ce que le mode
   preview-first améliorerait réellement.

## Questions ouvertes

- Quel état doit être global, et quel état doit être attaché à un projet ?
  Décision actuelle : global pour les préférences shell générales, par projet
  pour le contexte de travail et les vues.
- Est-ce que Niamoto doit restaurer automatiquement la dernière page, ou ouvrir
  un écran d’accueil projet avec reprise explicite ?
  Décision actuelle : restauration automatique uniquement si l’app démarre sur
  `/`, afin de respecter un retour volontaire au dashboard.
- Quelles listes sont réellement lentes aujourd’hui avec de vrais projets ?
- La command palette doit-elle lancer des actions longues, ou seulement naviguer
  vers les écrans qui les lancent ?
- Quels signaux de jobs existent déjà côté API et lesquels doivent être
  normalisés avant une timeline propre ?

## Critères pour accepter une idée

Une idée doit être priorisée seulement si elle respecte au moins deux critères :

- rend Niamoto plus rapide à comprendre ;
- améliore la sensation desktop locale ;
- réduit un frottement utilisateur existant ;
- reste générique entre projets écologiques ;
- peut être testée en une itération raisonnable ;
- n’ajoute pas de couche de configuration inutile.

## Critères de rejet

Une idée doit être repoussée si :

- elle copie une app externe sans correspondre au modèle Niamoto ;
- elle introduit une nouvelle surface sans clarifier le workflow ;
- elle dépend d’une refonte backend large ;
- elle optimise un problème non mesuré ;
- elle rend l’interface plus impressionnante mais moins compréhensible.

## Journal

- 2026-04-25 : création du suivi après les essais inspirés de Tolaria et la
  première sélection de dépôts Tauri à scanner.
- 2026-04-25 : phase 1 de mémorisation desktop livrée et poussée sur `main` :
  dernière route sûre par projet.
- 2026-04-25 : phase 2 démarrée sur `desktop-context-tabs` : préférences de
  vues simples par projet.
- 2026-04-25 : revue indépendante de `desktop-context-tabs` : corrections
  appliquées pour forcer le scope desktop explicite, désactiver les préférences
  en web par défaut, préserver les query params Collections et couvrir les cas
  fallback vers scope desktop dans les tests.
- 2026-04-25 : phase 2 de mémorisation desktop mergée localement dans `main`
  avec le commit `4af36604`.
- 2026-04-25 : démarrage de `command-palette-workflows` pour ajouter des
  raccourcis workflow et des deep links vers les fichiers de configuration.
- 2026-04-25 : `command-palette-workflows` mergée localement dans `main` avec
  le commit `9f027000`.
- 2026-04-25 : démarrage de `list-performance-metrics` pour mesurer les listes
  lourdes avant toute virtualisation.
