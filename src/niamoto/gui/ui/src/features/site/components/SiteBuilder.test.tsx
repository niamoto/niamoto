import { describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { SiteBuilder } from './SiteBuilder'

const stateRef = {
  value: null as any,
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (_key: string, defaultValue?: string) => defaultValue ?? 'Site setup',
    i18n: { language: 'fr', resolvedLanguage: 'fr' },
  }),
}))

vi.mock('../hooks/useSiteBuilderState', () => ({
  useSiteBuilderState: () => stateRef.value,
}))

vi.mock('@/shared/hooks/useSiteConfig', () => ({
  useFileContent: () => ({ data: null }),
  useGroupIndexPreview: () => ({ mutate: vi.fn(), isPending: false }),
  getCanonicalStaticPageOutputFile: (page: { output_file?: string | null }) => page.output_file ?? 'index.html',
  isRootIndexTemplate: (template?: string | null) => template === 'index.html',
}))

vi.mock('./SiteSetupWizard', () => ({
  SiteSetupWizard: () => <div>Site setup</div>,
}))

vi.mock('./PagesOverview', () => ({
  PagesOverview: () => <div>Pages overview</div>,
}))

vi.mock('./UnifiedSiteTree', () => ({
  UnifiedSiteTree: () => <div>Tree</div>,
}))

vi.mock('./SiteBuilderPreview', () => ({
  SitePreview: () => <div>Preview</div>,
  GroupIndexPreviewPanel: () => <div>Group preview</div>,
}))

function buildState(overrides: Record<string, unknown> = {}) {
  return {
    siteConfig: {
      site: { title: 'Niamoto', lang: 'fr', languages: ['fr'], primary_color: '#228b22', nav_color: '#ffffff' },
      navigation: [],
      footer_navigation: [],
      static_pages: [],
      template_dir: 'templates/',
      output_dir: 'exports/web',
      copy_assets_from: [],
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    groupsLoading: false,
    groups: [],
    availableNewPageTemplates: [],
    unifiedTree: [],
    setUnifiedTree: vi.fn(),
    allPages: [],
    setAllPages: vi.fn(),
    editedNavigation: [],
    editedPages: [],
    editedSite: { title: 'Niamoto', lang: 'fr', languages: ['fr'], primary_color: '#228b22', nav_color: '#ffffff' },
    setEditedSite: vi.fn(),
    editedFooterNavigation: [],
    setEditedFooterNavigation: vi.fn(),
    selection: null,
    setSelection: vi.fn(),
    pageToDelete: null,
    setPageToDelete: vi.fn(),
    hasChanges: false,
    hasExistingHomePage: false,
    isSaving: false,
    isEnablingIndexPage: false,
    handleSave: vi.fn(),
    saveConfig: vi.fn(),
    handleAddPage: vi.fn(),
    handleTemplateSelected: vi.fn(),
    handleCreatePageFromNavigation: vi.fn(),
    handleUpdatePage: vi.fn(),
    handleDeletePage: vi.fn(),
    confirmDeletePage: vi.fn(),
    handleDuplicatePage: vi.fn(),
    handleAddPageToNavigation: vi.fn(),
    handleEnableGroupIndexPage: vi.fn(),
    isPageInMenu: vi.fn(() => false),
    togglePageInMenu: vi.fn(),
    findMenuRefsForPage: vi.fn(() => []),
    findMenuRefsForCollection: vi.fn(() => []),
    updateMenuItemLabel: vi.fn(),
    removeMenuItem: vi.fn(),
    addPageToMenu: vi.fn(),
    addCollectionToMenu: vi.fn(),
    toggleItemVisibility: vi.fn(),
    addExternalLink: vi.fn(),
    removeExternalLink: vi.fn(),
    updateExternalLink: vi.fn(),
    ...overrides,
  }
}

describe('SiteBuilder empty-state regressions', () => {
  it('renders Site Setup for an empty persisted config', () => {
    stateRef.value = buildState()
    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).toContain('Site setup')
  })

  it('renders Site Setup again when the draft becomes empty after deleting home', () => {
    stateRef.value = buildState({
      siteConfig: {
        site: { title: 'Niamoto', lang: 'fr', languages: ['fr'], primary_color: '#228b22', nav_color: '#ffffff' },
        navigation: [{ text: 'Home', url: '/index.html' }],
        footer_navigation: [],
        static_pages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
        template_dir: 'templates/',
        output_dir: 'exports/web',
        copy_assets_from: [],
      },
      editedNavigation: [],
      editedPages: [],
      hasChanges: true,
    })

    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).toContain('Site setup')
  })

  it('renders the overview path for a genuinely configured root page', () => {
    stateRef.value = buildState({
      siteConfig: {
        site: { title: 'Niamoto', lang: 'fr', languages: ['fr'], primary_color: '#228b22', nav_color: '#ffffff' },
        navigation: [{ text: 'Home', url: '/index.html' }],
        footer_navigation: [],
        static_pages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
        template_dir: 'templates/',
        output_dir: 'exports/web',
        copy_assets_from: [],
      },
      editedNavigation: [{ text: 'Home', url: '/index.html' }],
      editedPages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
    })

    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).not.toContain('<div>Site setup</div>')
    expect(html).toContain('Pages overview')
  })
})
