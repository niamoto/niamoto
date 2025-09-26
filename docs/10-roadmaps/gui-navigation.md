# Roadmap : Architecture de Navigation et Interface Export
## Niamoto GUI - Décembre 2024 / Janvier 2025

---

## 📌 Vue d'ensemble

### Objectif Principal
Créer une architecture de navigation évolutive et une interface complète pour la gestion des exports, permettant aux utilisateurs de configurer visuellement leur site statique sans connaissances techniques.

### Contexte
- **Problème actuel** : Navigation trop simple (4 liens plats) qui ne permettra pas d'accueillir les fonctionnalités futures
- **Besoin Export** : Interface pour configurer le site statique (pages, templates, widgets)
- **Vision future** : Support pour data explorer, live preview, plugins, documentation intégrée

### Dates Clés
- **Début** : 16 décembre 2024
- **MVP Navigation** : 20 décembre 2024
- **MVP Export** : 3 janvier 2025

---

## 🏗️ Architecture Proposée

### Navigation Hiérarchique à 2 Niveaux

```typescript
interface NavigationStructure {
  sections: [
    {
      id: 'pipeline',
      label: 'Pipeline',
      icon: Workflow,
      items: [
        { id: 'import', label: 'Import Data', path: '/import' },
        { id: 'transform', label: 'Transform', path: '/transform' },
        { id: 'export', label: 'Export Site', path: '/export' }
      ]
    },
    {
      id: 'content',
      label: 'Content',
      icon: FileText,
      items: [
        { id: 'pages', label: 'Static Pages', path: '/content/pages' },
        { id: 'templates', label: 'Templates', path: '/content/templates' },
        { id: 'assets', label: 'Assets', path: '/content/assets' }
      ]
    },
    {
      id: 'data',
      label: 'Data & Preview',
      icon: Database,
      items: [
        { id: 'explorer', label: 'Data Explorer', path: '/data/explorer' },
        { id: 'preview', label: 'Live Preview', path: '/data/preview' },
        { id: 'api', label: 'API Explorer', path: '/data/api' }
      ]
    },
    {
      id: 'tools',
      label: 'Tools',
      icon: Wrench,
      items: [
        { id: 'plugins', label: 'Plugin Manager', path: '/tools/plugins' },
        { id: 'settings', label: 'Settings', path: '/tools/settings' },
        { id: 'docs', label: 'Documentation', path: '/tools/docs' }
      ]
    }
  ]
}
```

### Layout Principal

```
┌──────────────────────────────────────────────────────────────┐
│ 🌿 Niamoto              [Cmd+K] [🔍] [🔔] [👤] [?]           │
├─────────────┬────────────────────────────────────────────────┤
│             │  Breadcrumb > Current Page                      │
│ PIPELINE    ├────────────────────────────────────────────────┤
│ ├─ Import   │                                                 │
│ ├─ Transform│                                                 │
│ └─ Export   │         Zone de contenu principal               │
│             │                                                 │
│ CONTENT     │                                                 │
│ ├─ Pages    │                                                 │
│ ├─ Templates│                                                 │
│ └─ Assets   │                                                 │
│             │                                                 │
│ DATA        │                                                 │
│ ├─ Explorer │                                                 │
│ └─ Preview  │                                                 │
│             │                                                 │
│ TOOLS       │                                                 │
│ ├─ Plugins  │                                                 │
│ └─ Settings │                                                 │
│             │                                                 │
│ [≡] Collapse│                                                 │
└─────────────┴────────────────────────────────────────────────┘
```

---

## 📝 Interface Export Détaillée

### Architecture Multi-Onglets

L'interface d'export sera organisée en 5 onglets principaux :

#### 1. **Site Configuration** - Paramètres généraux
- Titre du site
- Logo et favicon
- Couleurs et thème
- Navigation principale
- Métadonnées SEO

#### 2. **Static Pages** - Gestion des pages
- Liste des pages statiques
- Éditeur Markdown intégré
- Support templates HTML
- Preview temps réel
- Gestion des URLs

#### 3. **Groups Config** - Configuration par groupe
- Sélection du groupe (taxon, plot, shape, custom)
- Configuration des widgets par groupe
- Drag-and-drop pour le layout
- Mapping données-widgets
- Templates de page

#### 4. **Templates** - Gestion des templates
- Browser de templates
- Upload de nouveaux templates
- Éditeur de code avec syntax highlighting
- Variables disponibles
- Héritage de templates

#### 5. **Preview** - Prévisualisation
- iFrame avec site généré
- Navigation entre pages
- Mode responsive (desktop/tablet/mobile)
- Rechargement automatique
- Export final

---

## 📅 Planning d'Implémentation

### Phase 1 : Refactoring Navigation (16-18 décembre)

#### Jour 1 : Architecture de base
- [ ] Créer `NavigationSidebar.tsx` avec structure hiérarchique
- [ ] Implémenter `TopBar.tsx` avec actions rapides
- [ ] Ajouter `BreadcrumbNav.tsx` pour le contexte
- [ ] Créer store Zustand pour l'état de navigation

#### Jour 2 : Composants et routing
- [ ] Implémenter sections collapsibles
- [ ] Ajouter animations de transition
- [ ] Configurer routes imbriquées React Router
- [ ] Créer `CommandPalette.tsx` (Cmd+K)

#### Jour 3 : Responsive et polish
- [ ] Mode responsive (sidebar compact sur mobile)
- [ ] Persistance état sidebar (localStorage)
- [ ] Tooltips et accessibilité
- [ ] Tests unitaires

### Phase 2 : Interface Export (19-23 décembre)

#### Jour 4-5 : Infrastructure Export
- [ ] Créer `ExportBuilder.tsx` container principal
- [ ] Implémenter système de tabs
- [ ] API endpoints pour configuration
- [ ] Store Zustand pour état export

#### Jour 6 : Site Configuration
- [ ] `SiteConfigEditor.tsx` - Formulaire config générale
- [ ] `NavigationEditor.tsx` - Gestion menu navigation
- [ ] `ThemeCustomizer.tsx` - Personnalisation visuelle
- [ ] Validation et sauvegarde auto

#### Jour 7 : Pages Statiques
- [ ] `StaticPagesManager.tsx` - CRUD pages
- [ ] `MarkdownEditor.tsx` - Éditeur avec preview
- [ ] `TemplateSelector.tsx` - Choix template/markdown
- [ ] Intégration markdown-it ou similar

#### Jour 8 : Configuration Groupes
- [ ] `GroupsExportConfig.tsx` - Config par groupe
- [ ] `WidgetLayoutEditor.tsx` - Drag-and-drop layout
- [ ] `DataWidgetMapper.tsx` - Mapping données-widgets
- [ ] `CompatibilityChecker.tsx` - Validation compatibilité

#### Jour 9 : Templates et Preview
- [ ] `TemplatesManager.tsx` - Gestion templates
- [ ] `CodeEditor.tsx` - Éditeur avec highlighting
- [ ] `SitePreview.tsx` - iFrame preview
- [ ] `ExportGenerator.tsx` - Génération finale

### Phase 3 : Intégration et Tests (26-27 décembre)

#### Jour 10 : Intégration
- [ ] Connexion avec backend FastAPI
- [ ] Gestion des erreurs
- [ ] Optimisations performance
- [ ] Documentation inline

#### Jour 11 : Tests et Polish
- [ ] Tests E2E interface export
- [ ] Tests unitaires composants
- [ ] Corrections bugs
- [ ] Documentation utilisateur

---

## 🔧 Stack Technique

### Frontend
```json
{
  "core": {
    "react": "^19.0.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "react-router-dom": "^6.20.0"
  },
  "ui": {
    "tailwindcss": "^4.0.0",
    "@shadcn/ui": "latest",
    "lucide-react": "latest"
  },
  "state": {
    "zustand": "^4.4.0",
    "@tanstack/react-query": "^5.0.0"
  },
  "editor": {
    "@uiw/react-md-editor": "^4.0.0",
    "@monaco-editor/react": "^4.6.0"
  },
  "dnd": {
    "@dnd-kit/sortable": "^8.0.0",
    "@dnd-kit/core": "^6.1.0"
  },
  "utils": {
    "cmdk": "^0.2.0",
    "react-hook-form": "^7.48.0",
    "zod": "^3.22.0"
  }
}
```

### Backend Endpoints

```python
# Navigation & Config
GET /api/navigation/structure
GET /api/user/preferences
PUT /api/user/preferences

# Export - Site Config
GET /api/export/site-config
PUT /api/export/site-config
POST /api/export/validate-config

# Export - Pages
GET /api/export/pages
POST /api/export/pages
PUT /api/export/pages/{id}
DELETE /api/export/pages/{id}

# Export - Templates
GET /api/export/templates
POST /api/export/templates/upload
DELETE /api/export/templates/{id}

# Export - Groups
GET /api/export/groups
GET /api/export/groups/{name}/config
PUT /api/export/groups/{name}/config
GET /api/export/groups/{name}/compatible-widgets

# Export - Generation
POST /api/export/generate
GET /api/export/preview
GET /api/export/status
GET /api/export/download
```

---

## 🎨 Design System

### Variables CSS
```css
:root {
  /* Navigation */
  --sidebar-width-full: 260px;
  --sidebar-width-compact: 64px;
  --sidebar-width-mobile: 0px;
  --topbar-height: 56px;
  --breadcrumb-height: 36px;

  /* Export Builder */
  --tab-height: 48px;
  --widget-min-height: 120px;
  --widget-gap: 16px;
  --editor-min-height: 400px;

  /* Transitions */
  --transition-fast: 150ms;
  --transition-normal: 250ms;
  --transition-slow: 350ms;
}
```

### Composants Réutilisables

```typescript
// Navigation
<NavigationSection />
<NavigationItem />
<CollapsibleSection />
<CommandPalette />

// Export
<TabContainer />
<ConfigForm />
<MarkdownEditor />
<DragDropZone />
<WidgetCard />
<PreviewFrame />

// Shared
<PageHeader />
<ActionBar />
<EmptyState />
<LoadingState />
<ErrorBoundary />
```

---

## 📊 Métriques de Succès

### Performance
- Navigation sidebar render : < 50ms
- Tab switching : < 100ms
- Markdown preview : < 200ms
- Site generation : < 30s

### Utilisabilité
- Temps configuration export simple : < 10 min
- Taux d'erreur configuration : < 5%
- Découvrabilité features : > 90%

### Technique
- Couverture tests : > 80%
- Bundle size : < 500KB
- Lighthouse score : > 90

---

## 🚧 Risques et Mitigations

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| Complexité navigation | Élevé | Moyenne | Tests utilisateurs précoces |
| Performance drag-drop | Moyen | Faible | Utiliser bibliothèque optimisée |
| Compatibilité templates | Élevé | Moyenne | Validation stricte côté serveur |
| Migration breaking | Élevé | Faible | Feature flags et rollback |

---

## 🔄 Migration Strategy

### Étape 1 : Coexistence (Semaine 1)
- Nouveau layout derrière feature flag
- Anciennes routes restent fonctionnelles
- A/B testing avec utilisateurs volontaires

### Étape 2 : Migration Progressive (Semaine 2)
- Nouveau layout par défaut pour nouveaux utilisateurs
- Migration assistée pour utilisateurs existants
- Documentation et tutoriels

### Étape 3 : Dépréciation (Semaine 3+)
- Ancien layout marqué comme déprécié
- Redirection automatique
- Suppression dans version suivante

---

## 📈 Évolutions Futures

### Q1 2025
- Mode collaboratif temps réel
- Versioning des configurations
- Templates marketplace

### Q2 2025
- IA pour suggestions de layout
- Générateur de contenu automatique
- Analytics intégrés

### Q3 2025
- Export multi-formats (PDF, DOCX)
- API publique
- Webhooks et automatisations

---

## 👥 Responsabilités

- **Product Owner** : Julien Barbe
- **Architecture** : Julien Barbe + Claude
- **Frontend Dev** : Julien Barbe
- **Backend Dev** : Julien Barbe
- **QA** : Automatisé + Manuel

---

## 📝 Notes de Décision

### Décisions Prises
- **13/12/2024** : Architecture navigation hiérarchique à 2 niveaux
- **13/12/2024** : Export avec interface multi-onglets
- **13/12/2024** : Support Markdown + Templates HTML
- **13/12/2024** : Drag-and-drop pour layout widgets

### Points Ouverts
- Choix éditeur Markdown (MDEditor vs Monaco)
- Stratégie de cache pour preview
- Gestion des conflits templates

---

*Document créé le 13/12/2024*
*Dernière mise à jour : 13/12/2024*
*Version : 1.0*
