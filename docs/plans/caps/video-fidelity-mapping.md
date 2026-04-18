# Video Fidelity Mapping

Référence de calage entre les captures réelles de l’application et la composition Remotion de [MarketingLandscape.tsx](/Users/julienbarbe/Dev/clients/niamoto/media/demo-video/src/compositions/MarketingLandscape.tsx).

Objectif : corriger la vidéo pour qu’elle colle à l’interface actuelle au lieu de rester sur des écrans génériques sombres.

## Séquence de référence

### Intro / accueil

- [01.splash-loading.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/01.splash-loading.png) : splash réel
- [02.welcome-project-picker.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/02.welcome-project-picker.png) : écran d’accueil avec choix créer / ouvrir

### Création de projet

- [03.project-create-empty.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/03.project-create-empty.png) : formulaire vide
- [04.project-create-name.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/04.project-create-name.png) : saisie du nom
- [05.project-create-ready.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/05.project-create-ready.png) : formulaire complété

### Import

- [06.dashboard-get-started.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/06.dashboard-get-started.png) : dashboard de démarrage
- [07.import-sources-select.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/07.import-sources-select.png) : sélection des sources
- [08.import-sources-review.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/08.import-sources-review.png) : import avec liste de fichiers
- [09.import-analysis-running.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/09.import-analysis-running.png) : analyse en cours
- [10.import-analysis-progress.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/10.import-analysis-progress.png) : progression d’analyse
- [11.import-config-detected.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/11.import-config-detected.png) : configuration détectée
- [12.import-processing-running.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/12.import-processing-running.png) : import en cours
- [13.data-dashboard-summary.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/13.data-dashboard-summary.png) : données importées

### Collections

- [14.collections-widget-config.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/14.collections-widget-config.png) : configuration d’un widget
- [15.collections-overview.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/15.collections-overview.png) : vue d’ensemble collections
- [16.collections-add-widget-modal.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/16.collections-add-widget-modal.png) : ajout de widget
- [17.collections-widget-catalog.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/17.collections-widget-catalog.png) : catalogue de widgets
- [18.collections-explorer-detail.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/18.collections-explorer-detail.png) : explorer / détail de collection
- [20.collections-processing.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/20.collections-processing.png) : calcul des collections

### Site Builder

- [21.site-builder-home-page.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/21.site-builder-home-page.png) : page d’accueil du site
- [22.site-builder-methodology-page.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/22.site-builder-methodology-page.png) : page méthodologie
- [23.site-builder-collection-page.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/23.site-builder-collection-page.png) : page de collection
- [19.public-site-dashboard.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/19.public-site-dashboard.png) : rendu public à injecter dans les previews

### Publication / déploiement

- [24.publish-preview-loading.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/24.publish-preview-loading.png) : publication avec preview en chargement
- [25.publish-generation-preview.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/25.publish-generation-preview.png) : preview visible pendant la génération
- [26.deploy-provider-picker.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/26.deploy-provider-picker.png) : choix du provider
- [27.deploy-github-pages-config.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/27.deploy-github-pages-config.png) : configuration GitHub Pages
- [28.deploy-build-log.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/28.deploy-build-log.png) : log de déploiement
- [29.deploy-success.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/29.deploy-success.png) : succès du déploiement

## Mapping par acte

| Acte vidéo | Captures de vérité | Ce que la vidéo actuelle doit corriger |
| --- | --- | --- |
| Intro | 01 | L’intro doit reprendre le vrai splash clair et le vrai logo, pas un fond sombre abstrait. |
| Act 1 — Welcome | 02 | L’acte doit copier l’écran de choix réel, avec les vrais boutons, le toggle et la vraie hiérarchie visuelle. |
| Act 2 — Project Wizard | 03, 04, 05 | L’acte doit suivre le vrai formulaire de création, pas une carte générique dark. |
| Act 3 — Import | 06 à 13 | L’acte doit montrer le vrai flux produit : dashboard de démarrage, import des sources, analyse, config détectée, puis dashboard importé. |
| Act 4 — Collections | 14 à 18, 20 | L’acte doit quitter la simple grille de trois cartes et montrer le vrai travail widget / modal / explorer / calcul. |
| Act 5 — Site Builder | 21, 22, 23, 19 | L’acte doit coller au vrai builder à trois colonnes et utiliser un vrai aperçu inspiré du site généré. |
| Act 6 — Publish | 24 à 29 | L’acte doit inclure le vrai panneau de preview, la génération, le choix du provider, la config GitHub Pages, les logs et l’état final. |

## Ordre de correction recommandé

### Priorité 1 — Shell global

- Refaire la palette globale pour coller aux captures claires.
- Remplacer le fond noir et les surfaces sombres dans tous les actes.
- Corriger le logo et le traitement du rendu pour supprimer l’effet pixelisé.
- Reprendre [AppWindow](/Users/julienbarbe/Dev/clients/niamoto/media/demo-video/src/ui/AppWindow.tsx), [Sidebar](/Users/julienbarbe/Dev/clients/niamoto/media/demo-video/src/ui/Sidebar.tsx) et [TopBar](/Users/julienbarbe/Dev/clients/niamoto/media/demo-video/src/ui/TopBar.tsx) depuis les captures réelles.

### Priorité 2 — Actes les plus faux aujourd’hui

- [Act1Welcome.tsx](/Users/julienbarbe/Dev/clients/niamoto/media/demo-video/src/acts/Act1Welcome.tsx)
- [Act2ProjectWizard.tsx](/Users/julienbarbe/Dev/clients/niamoto/media/demo-video/src/acts/Act2ProjectWizard.tsx)
- [Act4Collections.tsx](/Users/julienbarbe/Dev/clients/niamoto/media/demo-video/src/acts/Act4Collections.tsx)
- [Act6Publish.tsx](/Users/julienbarbe/Dev/clients/niamoto/media/demo-video/src/acts/Act6Publish.tsx)

Raison : ce sont les actes où la vidéo actuelle est la plus éloignée des écrans réels.

### Priorité 3 — Actes déjà proches en structure

- [Act3Import.tsx](/Users/julienbarbe/Dev/clients/niamoto/media/demo-video/src/acts/Act3Import.tsx)
- [Act5SiteBuilder.tsx](/Users/julienbarbe/Dev/clients/niamoto/media/demo-video/src/acts/Act5SiteBuilder.tsx)

Raison : leur structure générale est bonne, mais le niveau de fidélité visuelle et le contenu doivent être réalignés sur les captures.

## Décisions visuelles à prendre dès maintenant

- Utiliser les captures comme vérité de palette, d’espacement et de structure.
- Considérer [19.public-site-dashboard.png](/Users/julienbarbe/Dev/clients/niamoto/docs/assets/screenshots/desktop/19.public-site-dashboard.png) comme référence de contenu pour les aperçus de site, pas comme un acte desktop autonome.
- Garder le storytelling actuel de la vidéo, mais remplacer les écrans “fictifs” par des reconstitutions proches de l’application actuelle.
