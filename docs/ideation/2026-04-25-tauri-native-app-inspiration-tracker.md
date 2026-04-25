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

## Idées candidates

### 1. Mémorisation du contexte desktop

**Statut : phase 1 en cours.**
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
- la première brique mémorise la dernière route sûre par projet ;
- la restauration se fait seulement au démarrage sur la route d’accueil, pour
  ne pas empêcher l’utilisateur de revenir volontairement au dashboard ;
- les sélections fines par module seront ajoutées ensuite seulement si elles
  ont un vrai bénéfice utilisateur.

### 2. Virtualisation ciblée des listes lourdes

**Statut : candidat à mesurer avant implémentation.**
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

### 3. Command palette comme vrai centre d’action

**Statut : candidat moyen terme.**
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

### 4. Historique local des actions et jobs

**Statut : candidat moyen terme.**
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

1. Implémenter la mémorisation du contexte desktop.
2. Mesurer une vraie liste lourde avant de choisir une solution de
   virtualisation.
3. Faire un scan ciblé de Yaak, GitButler et Spacedrive pour extraire des
   patterns concrets, pas seulement des impressions.

### Moyen terme

1. Renforcer la command palette avec des actions réelles.
2. Construire un historique local des actions/jobs.
3. Revenir sur Collections seulement après avoir clarifié ce que le mode
   preview-first améliorerait réellement.

## Questions ouvertes

- Quel état doit être global, et quel état doit être attaché à un projet ?
- Est-ce que Niamoto doit restaurer automatiquement la dernière page, ou ouvrir
  un écran d’accueil projet avec reprise explicite ?
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
