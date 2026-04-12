---
title: Eliminate UI flickering and achieve native-like rendering smoothness
type: refactor
date: 2026-04-12
---

# Eliminate UI flickering and achieve native-like rendering smoothness

## Overview

L’interface React/Tauri de Niamoto souffre de plusieurs micro-flashs visuels qui dégradent fortement la perception de qualité de l’application desktop : transitions de pages avec état intermédiaire trop visible, chargement initial encore trop “web”, sidebar qui saute au montage, et écrans de chargement génériques là où des squelettes contextuels seraient plus stables.

L’objectif de ce plan est d’améliorer la fluidité perçue sans refonte de stack, en s’appuyant sur les primitives déjà disponibles dans React 19, React Router 7 et Tauri 2. La cible n’est pas “zéro animation”, mais une navigation et un démarrage qui donnent une impression proche d’une application native sur macOS, Windows et Linux.

## Validation externe

Ce plan a été revu le 12 avril 2026 à partir de :

- la documentation officielle React Router 7.14.0 sur `createBrowserRouter`, les route objects, `lazy`, `useNavigation` et le préchargement des liens ;
- la documentation officielle React 19.2 sur `startTransition` ;
- la documentation officielle Tauri v2 sur les splashscreens et les versions de webviews ;
- la documentation MDN sur `rel="preload"` pour les fonts ;
- l’application open source [Jan](https://github.com/janhq/jan), qui utilise Tauri 2 et un loader HTML initial dans [`web-app/index.html`](https://github.com/janhq/jan/blob/main/web-app/index.html) sans orchestration de splashscreen multi-fenêtres dans [`src-tauri/tauri.conf.json`](https://github.com/janhq/jan/blob/main/src-tauri/tauri.conf.json).

## Ce qui change après validation

La validation externe confirme la direction générale, mais modifie plusieurs décisions du plan initial :

1. **Le préchargement des routes doit d’abord utiliser les primitives natives de React Router 7**. Après migration vers un Data Router, la sidebar doit utiliser `NavLink` avec `prefetch="intent"` comme mécanisme principal. Un registre manuel de `import()` ne doit rester qu’en fallback pour la CommandPalette et les navigations non basées sur des liens.
2. **`startTransition` ne doit pas être appliqué mécaniquement à tous les `navigate()`**. La doc React confirme que `startTransition` rend les mises à jour non bloquantes, mais n’expose pas d’état pending à lui seul. Il faut donc le réserver aux navigations programmatiques réellement coûteuses, après mesure.
3. **Le plus gros gain de démarrage est dans le shell HTML initial, pas dans une nouvelle mécanique de splashscreen Tauri**. La doc Tauri présente le splashscreen multi-fenêtres comme un lab, pas comme la voie par défaut. Pour cette itération, il faut conserver un modèle à fenêtre principale unique et améliorer la continuité visuelle entre le loader Rust actuel et l’UI React.
4. **Le plan initial préchargeait les mauvaises fonts**. Dans le code actuel, le thème par défaut `frond` utilise Plus Jakarta Sans et JetBrains Mono, pas Nunito ni DM Sans.
5. **La phase 3 doit être resserrée**. `contain`, `React.memo` et d’autres optimisations “deep polish” ne doivent pas faire partie du chemin critique sans preuve de gain au profiling.
6. **Les routes de redirection inutiles doivent être traitées comme une source de micro-churn**. Aujourd’hui, la navigation “Site” cible `/site`, puis redirige vers `/site/pages`. Ce type de détour doit être supprimé des points d’entrée principaux.

## Problèmes constatés dans le code actuel

Les constats suivants sont confirmés par le code du dépôt :

1. **Chargement de pages lazy via `Suspense` avec fallback plein écran** dans [`src/niamoto/gui/ui/src/app/App.tsx`](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/app/App.tsx), ce qui rend le spinner trop visible pendant certaines transitions.
2. **Responsive sidebar appliqué après paint** dans [`src/niamoto/gui/ui/src/components/layout/MainLayout.tsx`](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/components/layout/MainLayout.tsx), via `useEffect`.
3. **Fonts locales injectées après coup** dans [`src/niamoto/gui/ui/src/themes/index.ts`](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/themes/index.ts), alors que [`index.html`](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/index.html) est quasi vide.
4. **Attribut `data-platform` posé en `useEffect`** dans [`src/niamoto/gui/ui/src/shared/hooks/usePlatform.ts`](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/shared/hooks/usePlatform.ts), alors que plusieurs règles CSS dans [`src/niamoto/gui/ui/src/index.css`](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/index.css) en dépendent dès le premier paint.
5. **`ProjectHub` affiche un spinner centré générique** dans [`src/niamoto/gui/ui/src/features/dashboard/views/ProjectHub.tsx`](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/dashboard/views/ProjectHub.tsx).
6. **`DashboardView` retourne `null`** tant que `pipeline` n’est pas prêt dans [`src/niamoto/gui/ui/src/features/dashboard/components/DashboardView.tsx`](/Users/julienbarbe/Dev/clients/niamoto/src/niamoto/gui/ui/src/features/dashboard/components/DashboardView.tsx).
7. **`/site` et `/site/navigation` redirigent vers `/site/pages`**, ce qui ajoute du churn inutile aux flux de navigation.
8. **Le loader Rust remplace le contenu du webview par du HTML inline puis renavigue vers l’URL finale**, dans [`src-tauri/src/lib.rs`](/Users/julienbarbe/Dev/clients/niamoto/src-tauri/src/lib.rs). Cela explique une partie de la transition perceptible au démarrage.

## Non-objectifs

Ce plan ne couvre pas :

- la migration du data fetching React Query vers des `loader` React Router ;
- l’introduction d’un splashscreen Tauri multi-fenêtres ;
- une refonte visuelle du produit ;
- une campagne large de `React.memo`, `useCallback` ou `contain` avant profiling ;
- l’adoption immédiate de la View Transitions API native.

## Stratégie révisée

Le travail est découpé en trois phases. Les deux premières sont le chemin critique. La troisième ne contient que du polish mesuré.

### Phase 1 — Stabiliser le premier paint et les états de chargement

Objectif : supprimer les flashs les plus visibles sans modifier l’architecture du routing.

#### 1.1 — Précharger les vraies fonts du thème par défaut

Fichier : `src/niamoto/gui/ui/index.html`

Précharger les fonts réellement utilisées par le thème `frond` :

- `/fonts/fonts.css`
- `/fonts/plus-jakarta-sans/400-latin.woff2`
- `/fonts/plus-jakarta-sans/500-latin.woff2`
- `/fonts/plus-jakarta-sans/600-latin.woff2`
- `/fonts/jetbrains-mono/400-latin.woff2`

Décisions :

- charger `fonts.css` directement dans `index.html` ;
- garder `loadLocalFonts()` dans `src/themes/index.ts`, mais le transformer en no-op si le stylesheet est déjà présent ;
- ne pas précharger tout le catalogue de fonts, seulement celles du thème par défaut et des poids visibles au premier écran.

Pourquoi :

- MDN confirme que `rel="preload"` peut démarrer tôt le téléchargement des ressources critiques ;
- pour les fonts, il faut utiliser `as="font"` et `crossorigin` ;
- précharger les mauvaises fonts ne résout rien et peut dégrader le rendu initial.

#### 1.2 — Ajouter un bootstrap thème minimal dans `index.html`

Fichier : `src/niamoto/gui/ui/index.html`

Ajouter un script synchrone très petit qui :

- lit la forme réelle de `localStorage["niamoto-theme"]` ;
- récupère `themeId` et `mode` ;
- résout `mode === "system"` avec `matchMedia('(prefers-color-scheme: dark)')` ;
- applique uniquement un sous-ensemble minimal de variables :
  - `--background`
  - `--foreground`
  - `color-scheme`
  - éventuellement `--sidebar` si cela évite un flash visible du shell

Décisions :

- ne pas injecter tout le thème dans `index.html` ;
- maintenir une petite map `THEME_BOOTSTRAP` des thèmes bundlés, limitée aux couleurs de shell ;
- ajouter un test de cohérence qui vérifie que les valeurs bootstrap restent alignées avec les presets TS.

Pourquoi :

- aujourd’hui, `ThemeProvider` applique le thème tôt via `useLayoutEffect`, mais `index.html` est encore vide pendant la toute première frame ;
- le mode persistant par défaut est `system`, donc supposer `light` est incorrect ;
- le risque principal est la dérive entre bootstrap HTML et tokens TS, d’où le test de parité.

#### 1.3 — Poser `data-platform` avant le mount React

Fichier : `src/niamoto/gui/ui/index.html`

Ajouter un script synchrone qui calcule la plateforme et pose `document.documentElement.dataset.platform` avant le mount.

Modifier ensuite `usePlatform.ts` pour :

- lire d’abord l’attribut déjà présent ;
- retomber sur la détection synchrone existante seulement si l’attribut manque ;
- éviter de réécrire inutilement l’attribut en `useEffect`.

Pourquoi :

- plusieurs styles desktop dépendent déjà de `data-platform` dans `index.css` ;
- actuellement, l’information plateforme est correcte mais appliquée trop tard dans le DOM.

#### 1.4 — Remplacer les états blancs et spinners génériques par des squelettes structurels

Fichiers :

- `src/niamoto/gui/ui/src/features/dashboard/views/ProjectHub.tsx`
- `src/niamoto/gui/ui/src/features/dashboard/components/DashboardView.tsx`

Créer un `DashboardSkeleton` réutilisable qui correspond au layout réel :

- en-tête ;
- grille de cartes ;
- grand bloc de contenu.

Décisions :

- `ProjectHub` ne doit plus afficher `Loader2` centré ;
- `DashboardView` ne doit plus retourner `null` ;
- les squelettes doivent reprendre le rythme du layout réel, pas juste empiler des rectangles arbitraires.

#### 1.5 — Corriger l’initialisation responsive de la sidebar avant paint

Fichier : `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx`

Premier correctif :

- passer le handler de resize de `useEffect` à `useLayoutEffect`.

Si un saut reste visible sur petits écrans :

- déplacer la valeur initiale de `sidebarMode` vers une détection client au premier accès au store, afin d’éviter qu’un mode persistant inadapté soit peint une première fois.

Pourquoi :

- `useLayoutEffect` est le correctif à faible risque ;
- si le store persiste `full` mais que la fenêtre démarre étroite, un simple changement d’effet peut ne pas suffire.

#### 1.6 — Garder le fade-in du root comme correctif optionnel, pas comme pilier

Fichier : `src/niamoto/gui/ui/src/index.css`

Le fade-in de `#root` reste une option, mais seulement après les correctifs 1.1 à 1.5.

Contraintes :

- durée courte, de l’ordre de 120 à 160 ms ;
- pas d’effet si `prefers-reduced-motion: reduce` ;
- ne pas l’utiliser pour masquer un défaut structurel persistant.

Pourquoi :

- un fade-in trop tôt introduit facilement une sensation de mollesse ;
- il est utile pour lisser la jonction Rust -> React, mais ne doit pas devenir le mécanisme principal.

### Phase 2 — Moderniser le routing avec les primitives React Router 7

Objectif : supprimer le “triple flash” à la navigation et utiliser les mécanismes natifs de pending UI et de préchargement.

#### 2.1 — Migrer vers `createBrowserRouter` avec parité route par route

Créer `src/niamoto/gui/ui/src/app/router.tsx` et migrer de `BrowserRouter` vers `RouterProvider`.

Avant tout changement, établir la matrice de parité suivante :

| Route actuelle | Composant cible | Type d’export | Note |
|---|---|---|---|
| `/` | `ProjectHub` | `default` | vue d’accueil projet |
| `/sources/*` | `DataModule` | named | module sidebar |
| `/groups/*` | `CollectionsModule` | named | module sidebar |
| `/site` | redirection aujourd’hui | n/a | à supprimer des points d’entrée principaux |
| `/site/pages` | `SitePagesPage` | `default` | vraie cible de navigation |
| `/site/navigation` | redirection aujourd’hui | n/a | à supprimer ou à garder comme alias faible |
| `/site/general` | `SiteGeneralPage` | `default` | page simple |
| `/site/appearance` | `SiteAppearancePage` | `default` | page simple |
| `/tools/explorer` | `DataExplorer` | named | palette / outil |
| `/tools/preview` | `LivePreview` | named | palette / outil |
| `/tools/settings` | `Settings` | named | palette / outil |
| `/tools/plugins` | `Plugins` | named | palette / outil |
| `/tools/docs` | `ApiDocs` | named | palette / outil |
| `/tools/config-editor` | `ConfigEditor` | named | palette / outil |
| `/publish/*` | `PublishModule` | named | module sidebar |

Décisions :

- conserver `WelcomeScreen` et `ProjectCreationWizard` hors du router, comme aujourd’hui ;
- migrer uniquement le routing d’application une fois l’état “project loaded” atteint ;
- remplacer les wrappers `Suspense` route par route par `lazy` au niveau des route objects.

Pourquoi :

- la doc React Router 7 confirme que `lazy` peut charger le composant et le loader en parallèle avant rendu ;
- cela évite que chaque route lazy passe par un fallback `Suspense` plein écran.

#### 2.2 — Utiliser `lazy` comme mécanisme principal de code splitting

Après migration Data Router :

- chaque route majeure doit utiliser `lazy` ;
- le rendu principal ne doit plus être enveloppé dans un `Suspense` plein écran pour chaque navigation ;
- les loading states restantes doivent venir du chargement métier, pas du chargement du chunk.

Conséquence attendue :

- la navigation passe de “sortie -> spinner global -> contenu” à “sortie -> entrée -> état contextuel éventuel”.

#### 2.3 — Précharger la sidebar avec `prefetch="intent"`

Fichier : `src/niamoto/gui/ui/src/components/layout/NavigationSidebar.tsx`

Après migration vers le Data Router :

- utiliser `NavLink` avec `prefetch="intent"` sur les entrées de navigation principales ;
- conserver le styling existant ;
- vérifier qu’aucun sélecteur CSS du type `:last-child` ne dépend de la structure exacte du `nav`.

Pourquoi :

- React Router 7 fournit déjà ce comportement ;
- cela évite de maintenir un registre manuel fragile pour les routes normales.

#### 2.4 — Garder un préchargement manuel uniquement pour la CommandPalette

Fichier : `src/niamoto/gui/ui/src/components/layout/CommandPalette.tsx`

La palette déclenche des navigations programmatiques, pas des `NavLink`.

Décision :

- introduire une petite helper `preloadRoute(path)` uniquement pour la palette et d’autres actions impératives comparables ;
- réutiliser les mêmes imports dynamiques que ceux du router pour éviter toute divergence.

#### 2.5 — Utiliser `useNavigation()` pour le pending UI global

Fichier : `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx`

Utiliser `useNavigation()` pour exposer un état pending global léger :

- faible baisse d’opacité du contenu principal ;
- ou fine barre de progression ;
- mais pas de spinner plein écran.

Pourquoi :

- c’est la primitive officielle de React Router pour le pending UI ;
- cela donne un feedback instantané sans casser la continuité visuelle.

#### 2.6 — Réserver `startTransition` aux vrais points chauds

Ne pas lancer un sweep automatique des 18 fichiers qui appellent `navigate()`.

Plan :

1. migrer le router ;
2. mesurer les navigations programmatiques encore saccadées ;
3. n’ajouter `startTransition` que sur les chemins où les descendants coûtent réellement cher.

Candidats probables :

- `CommandPalette`
- certains CTA de `DashboardView`
- quelques sélections de modules si elles déclenchent des re-renders lourds

Pourquoi :

- la doc React confirme que `startTransition` rend l’update non bloquante ;
- la même doc confirme aussi que `startTransition` ne fournit pas l’état pending, donc il ne remplace pas `useNavigation()`.

#### 2.7 — Supprimer les points d’entrée basés sur redirection

Fichiers probables :

- `src/niamoto/gui/ui/src/stores/navigationStore.ts`
- `src/niamoto/gui/ui/src/features/site/views/SiteIndexPage.tsx`
- `src/niamoto/gui/ui/src/features/site/views/SiteNavigationPage.tsx`

Décisions :

- faire pointer la navigation principale “Site” directement vers `/site/pages` ;
- garder éventuellement `/site` comme alias de compatibilité ;
- évaluer si `/site/navigation` doit disparaître ou rester comme alias silencieux.

Pourquoi :

- une redirection immédiate ajoute du churn de navigation et complique l’observation du pending UI ;
- ce correctif est petit et améliore la lisibilité du router.

### Phase 3 — Démarrage desktop et polish mesuré

Objectif : améliorer la continuité Rust -> React et corriger les derniers sauts visibles, sans ouvrir un chantier spéculatif.

#### 3.1 — Conserver le modèle à fenêtre unique dans cette itération

Le pattern officiel Tauri “splashscreen” repose sur :

- une fenêtre `main` cachée ;
- une seconde fenêtre `splashscreen` visible ;
- puis fermeture de l’une et affichage de l’autre.

Décision :

- ne pas adopter ce pattern dans Niamoto pour cette itération ;
- conserver la fenêtre principale actuelle et améliorer son loader ;
- reconsidérer un splashscreen séparé seulement si les mesures prouvent que le chargement actuel reste trop abrupt après les phases 1 et 2.

Pourquoi :

- Tauri présente ce pattern comme un lab, pas comme une obligation architecturale ;
- l’app open source Jan montre une autre voie crédible : loader initial dans `index.html` et fenêtre principale standard.

#### 3.2 — Rapprocher visuellement le loader Rust et le shell React

Fichier : `src-tauri/src/lib.rs`

Améliorer `show_loading_status()` en priorisant :

1. cohérence light/dark ;
2. couleurs de fond compatibles avec le shell React ;
3. typographie et loader cohérents avec l’identité visuelle.

Décision :

- si lire le thème persistant exact depuis la config est peu coûteux, le faire ;
- sinon, rester sur une palette light/dark cohérente avec `frond`, sans introduire une duplication lourde de tous les thèmes.

Pourquoi :

- la transition la plus visible vient de la différence de shell entre Rust et React ;
- répliquer tous les thèmes côté Rust serait coûteux pour un gain marginal.

#### 3.3 — Corriger le resize initial de `ModuleLayout`

Fichier : `src/niamoto/gui/ui/src/components/layout/ModuleLayout.tsx`

Le `ResizeObserver` actuel peut provoquer un saut visible après montage.

Décision :

- faire une mesure initiale avant paint via `useLayoutEffect` ou une mesure synchrone équivalente ;
- laisser ensuite `ResizeObserver` prendre le relais pour les changements dynamiques ;
- limiter l’auto-grow à une seule correction initiale si possible.

#### 3.4 — Accessibilité et motion

Fichiers :

- `src/niamoto/gui/ui/src/index.css`
- composants motion concernés

Ajouter ou vérifier :

- `prefers-reduced-motion` sur le fade-in éventuel ;
- `prefers-reduced-motion` sur les squelettes pulsés ;
- comportement stable des transitions de page quand la réduction des animations est active.

#### 3.5 — Expériences optionnelles, uniquement après preuve

Hors chemin critique :

- `React.memo` ciblé ;
- `useCallback` ciblé ;
- `contain: layout style` sur certaines zones ;
- réévaluation de la View Transitions API plus tard.

Pourquoi :

- Tauri utilise WebView2 sur Windows, `WKWebView` sur macOS et `webkit2gtk` sur Linux ;
- les optimisations très dépendantes du moteur doivent être testées après stabilisation du chemin principal.

## Plan d’exécution

### Ordre recommandé

1. Phase 1 complète
2. Mesure visuelle rapide avant/après
3. Phase 2 avec matrice de parité
4. Nouvelle mesure visuelle
5. Phase 3 seulement si les gains des phases 1 et 2 sont validés

### Découpage concret

- **PR 1** : shell HTML, fonts, `data-platform`, squelettes dashboard, sidebar avant paint
- **PR 2** : migration router, pending UI, préchargement natif, suppression des routes de redirection en entrée
- **PR 3** : polish startup Rust + `ModuleLayout` + accessibilité motion

## Critères d’acceptation

### Fonctionnels

- [ ] Le démarrage ne montre plus de flash blanc entre le loader Rust et l’UI React
- [ ] La navigation entre modules ne montre plus de spinner plein écran pour un simple chargement de chunk
- [ ] `ProjectHub` n’utilise plus de spinner centré générique
- [ ] `DashboardView` n’affiche plus d’écran vide tant que le pipeline charge
- [ ] `data-platform` est correct dès le premier paint
- [ ] La navigation “Site” n’introduit plus de redirection visible
- [ ] La CommandPalette peut précharger la destination sélectionnée avant navigation

### Non fonctionnels

- [ ] Pas de régression du flux `WelcomeScreen` / `ProjectCreationWizard`
- [ ] Compatibilité vérifiée sur macOS, Windows et Linux
- [ ] Respect de `prefers-reduced-motion`
- [ ] Pas d’augmentation de bundle injustifiée ; toute hausse notable est expliquée
- [ ] Aucun correctif de fluidité ne dépend d’une API non garantie sur Linux

## Quality Gates

- [ ] `cd src/niamoto/gui/ui && pnpm build`
- [ ] tests UI ou router ciblés si de nouveaux helpers ou redirects sont modifiés
- [ ] capture vidéo 60 fps avant/après pour la navigation principale et le cold start
- [ ] vérification manuelle du shell sur macOS
- [ ] vérification CI ou manuelle sur Windows et Linux
- [ ] contrôle DevTools / profiling seulement pour les optimisations de phase 3

## Risques et mitigations

| Risque | Impact | Mitigation |
|---|---|---|
| Dérive entre bootstrap HTML et thèmes TS | Moyen | map bootstrap minimale + test de parité |
| Régression de routing pendant la migration `createBrowserRouter` | Haut | matrice de parité explicite + smoke tests des routes |
| Préchargement manuel divergent du router | Moyen | helper partagée, basée sur les mêmes imports que le router |
| `startTransition` ajouté partout sans bénéfice réel | Moyen | ciblage après mesure, pas de sweep global |
| Linux se comporte différemment à cause de `webkit2gtk` | Moyen | vérification dédiée Linux, pas d’API moderne en dépendance dure |
| Le fade-in masque un vrai bug de timing | Faible | l’ajouter en dernier, le garder optionnel |

## Métriques de succès

| Métrique | Avant | Cible |
|---|---|---|
| Flash blanc au démarrage | visible sur certaines machines | non visible |
| Spinner global à la navigation | visible selon le chunk | absent pour les navigations normales |
| Écran vide dashboard | possible | remplacé par un squelette |
| Saut de sidebar au montage | visible | non visible |
| États visuels par navigation | sortie -> spinner -> contenu | sortie -> entrée -> pending subtil éventuel |
| Navigation “Site” | redirection implicite | cible directe |

## Alternatives considérées

### Migrer tout le data fetching vers des `loader`

Avantage :

- meilleur contrôle des états pending avant rendu.

Pourquoi ce n’est pas retenu maintenant :

- cela toucherait trop de pages et de hooks React Query pour cette itération ;
- la dette principale aujourd’hui est la fluidité perçue du shell, pas la stratégie de data fetching.

### Introduire un splashscreen Tauri séparé

Avantage :

- contrôle très fin du bootstrap avant d’afficher la fenêtre principale.

Pourquoi ce n’est pas retenu maintenant :

- complexité supplémentaire ;
- duplication potentielle entre loader Rust, splashscreen et shell React ;
- les docs Tauri le présentent comme un lab, et une app comme Jan obtient déjà une continuité correcte avec un loader HTML initial.

### Optimiser immédiatement avec `React.memo` et `contain`

Avantage :

- possibilité de grappiller des gains de re-render et de layout.

Pourquoi ce n’est pas retenu maintenant :

- trop spéculatif sans profiling ;
- risque de complexifier le code pour un gain faible ou invisible.

## Références

### Références internes

- Routing actuel : `src/niamoto/gui/ui/src/app/App.tsx`
- Layout principal : `src/niamoto/gui/ui/src/components/layout/MainLayout.tsx`
- Sidebar : `src/niamoto/gui/ui/src/components/layout/NavigationSidebar.tsx`
- Palette : `src/niamoto/gui/ui/src/components/layout/CommandPalette.tsx`
- Theme provider : `src/niamoto/gui/ui/src/components/theme/ThemeProvider.tsx`
- Registre de thèmes : `src/niamoto/gui/ui/src/themes/index.ts`
- Thème `frond` : `src/niamoto/gui/ui/src/themes/presets/frond.ts`
- Platform hook : `src/niamoto/gui/ui/src/shared/hooks/usePlatform.ts`
- Dashboard : `src/niamoto/gui/ui/src/features/dashboard/components/DashboardView.tsx`
- Hub projet : `src/niamoto/gui/ui/src/features/dashboard/views/ProjectHub.tsx`
- Module layout : `src/niamoto/gui/ui/src/components/layout/ModuleLayout.tsx`
- Loader Rust / navigation du webview : `src-tauri/src/lib.rs`

### Références externes

- React Router 7.14.0, Route Object et `lazy` : <https://reactrouter.com/start/data/route-object>
- React Router 7.14.0, `useNavigation` : <https://reactrouter.com/api/hooks/useNavigation>
- React Router 7 API, `Link` / `NavLink` `prefetch` : <https://api.reactrouter.com/v7/interfaces/react-router.LinkProps.html>
- React 19.2, `startTransition` : <https://react.dev/reference/react/startTransition>
- Tauri v2, splashscreen lab : <https://v2.tauri.app/learn/splashscreen/>
- Tauri v2, versions de webviews : <https://v2.tauri.app/reference/webview-versions/>
- MDN, `rel="preload"` : <https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/rel/preload>
- Jan, shell HTML initial : <https://github.com/janhq/jan/blob/main/web-app/index.html>
- Jan, config Tauri : <https://github.com/janhq/jan/blob/main/src-tauri/tauri.conf.json>
