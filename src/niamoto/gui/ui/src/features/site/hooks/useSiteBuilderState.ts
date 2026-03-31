/**
 * useSiteBuilderState - State management hook for the Site Builder
 *
 * Manages all edited state (site settings, navigation, footer, pages),
 * change detection, save logic, and page CRUD handlers.
 * Extracted from SiteBuilder.tsx for cleaner separation of concerns.
 */

import { useState, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import {
  useSiteConfig,
  useUpdateSiteConfig,
  useUpdateGroupIndexConfig,
  useGroups,
  useTemplates,
  type SiteSettings,
  type NavigationItem,
  type FooterSection,
  type StaticPage,
  type SiteConfigUpdate,
  type GroupInfo,
  DEFAULT_SITE_SETTINGS,
  DEFAULT_STATIC_PAGE,
  ROOT_INDEX_OUTPUT_FILE,
  ROOT_INDEX_TEMPLATE,
  getCanonicalStaticPageOutputFile,
  hasRootIndexPage,
  isRootIndexTemplate,
} from '@/shared/hooks/useSiteConfig'

export type SelectionType = 'general' | 'appearance' | 'navigation' | 'footer' | 'page' | 'group' | 'new-page'

export interface Selection {
  type: SelectionType
  id?: string
}

export function useSiteBuilderState(initialSection: string = 'pages') {
  const { t, i18n } = useTranslation(['site', 'common', 'indexConfig'])

  // Data fetching
  const { data: siteConfig, isLoading, error, refetch } = useSiteConfig()
  const { data: groupsData, isLoading: groupsLoading } = useGroups()
  const { data: templatesData } = useTemplates()
  const updateMutation = useUpdateSiteConfig()
  const updateGroupIndexMutation = useUpdateGroupIndexConfig()

  // Local editing state
  const [editedSite, setEditedSite] = useState<SiteSettings>(DEFAULT_SITE_SETTINGS)
  const [editedNavigation, setEditedNavigation] = useState<NavigationItem[]>([])
  const [editedFooterNavigation, setEditedFooterNavigation] = useState<FooterSection[]>([])
  const [editedPages, setEditedPages] = useState<StaticPage[]>([])

  // Delete confirmation dialog state
  const [pageToDelete, setPageToDelete] = useState<string | null>(null)

  // UI state
  const mapSectionToSelection = (section: string): Selection | null => {
    switch (section) {
      case 'general':
      case 'identity':
        return { type: 'general' }
      case 'appearance':
      case 'theme':
        return { type: 'appearance' }
      case 'navigation':
        return { type: 'navigation' }
      case 'pages':
        return null
      default:
        return { type: 'general' }
    }
  }
  const [selection, setSelection] = useState<Selection | null>(() => mapSectionToSelection(initialSection))

  useEffect(() => {
    setSelection(mapSectionToSelection(initialSection))
  }, [initialSection])

  // Groups from API (read-only)
  const groups: GroupInfo[] = groupsData?.groups ?? []

  // Sync local state with fetched data
  useEffect(() => {
    if (siteConfig) {
      setEditedSite(siteConfig.site)
      setEditedNavigation(siteConfig.navigation)
      setEditedFooterNavigation(siteConfig.footer_navigation || [])
      setEditedPages(siteConfig.static_pages)
    }
  }, [siteConfig])

  // Check for unsaved changes
  const hasChanges = useMemo(() => {
    if (!siteConfig) return false
    return (
      JSON.stringify(editedSite) !== JSON.stringify(siteConfig.site) ||
      JSON.stringify(editedNavigation) !== JSON.stringify(siteConfig.navigation) ||
      JSON.stringify(editedFooterNavigation) !== JSON.stringify(siteConfig.footer_navigation || []) ||
      JSON.stringify(editedPages) !== JSON.stringify(siteConfig.static_pages)
    )
  }, [siteConfig, editedSite, editedNavigation, editedFooterNavigation, editedPages])

  const hasExistingHomePage = useMemo(
    () => hasRootIndexPage(editedPages),
    [editedPages]
  )

  const availableNewPageTemplates = useMemo(() => {
    const templates = templatesData?.templates ?? []
    if (!hasExistingHomePage) {
      return templates
    }
    return templates.filter((template) => template.name !== ROOT_INDEX_TEMPLATE)
  }, [hasExistingHomePage, templatesData])

  // Save handler
  const handleSave = async () => {
    if (!siteConfig) return

    const update: SiteConfigUpdate = {
      site: editedSite,
      navigation: editedNavigation,
      footer_navigation: editedFooterNavigation,
      static_pages: editedPages,
      template_dir: siteConfig.template_dir,
      output_dir: siteConfig.output_dir,
      copy_assets_from: siteConfig.copy_assets_from,
    }

    try {
      await updateMutation.mutateAsync(update)
      toast.success(t('messages.configSaved'), {
        description: t('messages.configSavedDesc'),
      })
    } catch (err) {
      toast.error(t('common:status.error'), {
        description: err instanceof Error ? err.message : t('messages.saveFailed'),
      })
    }
  }

  // Show template list for adding new page
  const handleAddPage = () => {
    setSelection({ type: 'new-page' })
  }

  // Create page after template selection
  const handleTemplateSelected = (templateName: string) => {
    if (templateName === ROOT_INDEX_TEMPLATE && hasExistingHomePage) {
      toast.error(t('messages.homePageExists'), {
        description: t('messages.homePageExistsDesc'),
      })
      return
    }

    const baseName = templateName === ROOT_INDEX_TEMPLATE
      ? 'home'
      : templateName.replace('.html', '')
    const existingNames = new Set(editedPages.map((p) => p.name))

    let pageName = baseName
    let counter = 1
    while (existingNames.has(pageName)) {
      pageName = `${baseName}-${counter}`
      counter++
    }

    const newPage: StaticPage = {
      ...DEFAULT_STATIC_PAGE,
      name: pageName,
      output_file:
        templateName === ROOT_INDEX_TEMPLATE
          ? ROOT_INDEX_OUTPUT_FILE
          : `${pageName}.html`,
      template: templateName,
    }
    setEditedPages([...editedPages, newPage])
    setSelection({ type: 'page', id: newPage.name })

    toast.success(t('pages.pageCreated'), {
      description: t('pages.pageCreatedDesc', { name: newPage.name }),
      action: {
        label: t('navigation.addToMenu'),
        onClick: () => {
          setEditedNavigation((nav) => [
            ...nav,
            { text: newPage.name, url: `/${newPage.output_file}` },
          ])
          toast.success(t('navigation.linkAdded'), {
            description: t('navigation.linkAddedDesc'),
          })
        },
      },
    })
  }

  // Create page from navigation builder (inline creation)
  const handleCreatePageFromNavigation = async (pageName: string, templateName: string): Promise<StaticPage | null> => {
    if (templateName === ROOT_INDEX_TEMPLATE && hasExistingHomePage) {
      toast.error(t('messages.homePageExists'), {
        description: t('messages.homePageExistsDesc'),
      })
      return null
    }

    const existingNames = new Set(editedPages.map((p) => p.name))
    let finalName = pageName
    let counter = 1
    while (existingNames.has(finalName)) {
      finalName = `${pageName}-${counter}`
      counter++
    }

    const newPage: StaticPage = {
      ...DEFAULT_STATIC_PAGE,
      name: finalName,
      output_file:
        templateName === ROOT_INDEX_TEMPLATE
          ? ROOT_INDEX_OUTPUT_FILE
          : `${finalName}.html`,
      template: templateName,
    }

    setEditedPages((pages) => [...pages, newPage])

    toast.success(t('pages.pageCreated'), {
      description: t('pages.pageCreatedDesc', { name: finalName }),
    })

    return newPage
  }

  // Update page (handles name changes)
  const handleUpdatePage = (updatedPage: StaticPage) => {
    const oldName = selection?.id
    const normalizedPage = {
      ...updatedPage,
      output_file: getCanonicalStaticPageOutputFile(updatedPage),
    }

    if (
      isRootIndexTemplate(normalizedPage.template) &&
      editedPages.some(
        (page) => page.name !== oldName && isRootIndexTemplate(page.template)
      )
    ) {
      toast.error(t('messages.homePageExists'), {
        description: t('messages.homePageExistsDesc'),
      })
      return
    }

    setEditedPages((pages) =>
      pages.map((p) => (p.name === oldName ? normalizedPage : p))
    )
    if (oldName && normalizedPage.name !== oldName) {
      setSelection({ type: 'page', id: normalizedPage.name })
    }
  }

  // Delete page - opens confirmation dialog
  const handleDeletePage = (pageName: string) => {
    setPageToDelete(pageName)
  }

  // Confirm delete page (with auto-save)
  const confirmDeletePage = async () => {
    if (!pageToDelete || !siteConfig) return

    const pageObj = editedPages.find((p) => p.name === pageToDelete)
    if (!pageObj) return

    const newPages = editedPages.filter((p) => p.name !== pageToDelete)
    const pageUrl = `/${pageObj.output_file}`
    const newNavigation = editedNavigation.filter((item) => item.url !== pageUrl)
    const newFooterNavigation = editedFooterNavigation.map((section) => ({
      ...section,
      links: section.links.filter((link) => link.url !== pageUrl),
    }))

    setPageToDelete(null)
    setSelection(null)

    setEditedPages(newPages)
    setEditedNavigation(newNavigation)
    setEditedFooterNavigation(newFooterNavigation)

    try {
      await updateMutation.mutateAsync({
        site: editedSite,
        navigation: newNavigation,
        footer_navigation: newFooterNavigation,
        static_pages: newPages,
        template_dir: siteConfig.template_dir,
        output_dir: siteConfig.output_dir,
        copy_assets_from: siteConfig.copy_assets_from,
      })
      toast.success(t('pages.pageDeleted'), {
        description: t('pages.pageDeletedDesc'),
      })
    } catch (err) {
      setEditedPages(editedPages)
      setEditedNavigation(editedNavigation)
      setEditedFooterNavigation(editedFooterNavigation)
      toast.error(t('common:status.error'), {
        description: err instanceof Error ? err.message : t('messages.saveFailed'),
      })
    }
  }

  // Duplicate a page
  const handleDuplicatePage = (page: StaticPage) => {
    if (isRootIndexTemplate(page.template)) {
      toast.error(t('messages.homePageDuplicateBlocked'), {
        description: t('messages.homePageDuplicateBlockedDesc'),
      })
      return
    }

    const existingNames = new Set(editedPages.map((p) => p.name))
    let newName = `${page.name}-copy`
    let counter = 1
    while (existingNames.has(newName)) {
      newName = `${page.name}-copy-${counter}`
      counter++
    }

    const newPage: StaticPage = {
      ...page,
      name: newName,
      output_file: `${newName}.html`,
    }

    setEditedPages((pages) => [...pages, newPage])
    setSelection({ type: 'page', id: newName })
    toast.success(t('pages.pageDuplicated'), {
      description: t('pages.pageDuplicatedDesc', { name: newName }),
    })
  }

  // Add page to main navigation
  const handleAddPageToNavigation = (page: StaticPage) => {
    setEditedNavigation((nav) => [
      ...nav,
      { text: page.name, url: `/${page.output_file}` },
    ])
    toast.success(t('navigation.linkAdded'), {
      description: t('navigation.linkAddedDesc'),
    })
  }

  const handleEnableGroupIndexPage = async (groupName: string) => {
    try {
      await updateGroupIndexMutation.mutateAsync({
        groupName,
        config: {
          enabled: true,
          template: '_group_index.html',
          page_config: {
            title: t('indexConfig:defaultTitle', { groupBy: groupName }),
            description: '',
            items_per_page: 24,
          },
          filters: [],
          display_fields: [],
          views: [
            { type: 'grid', default: true },
            { type: 'list', default: false },
          ],
        },
      })

      toast.success(t('collectionViewer.indexPageActivated'), {
        description: t('collectionViewer.indexPageActivatedDesc'),
      })
    } catch (err) {
      toast.error(t('common:status.error'), {
        description: err instanceof Error ? err.message : t('messages.saveFailed'),
      })
    }
  }

  return {
    // Data fetching state
    siteConfig,
    isLoading,
    error,
    refetch,
    groupsLoading,
    groups,
    availableNewPageTemplates,

    // Edited state
    editedSite,
    setEditedSite,
    editedNavigation,
    setEditedNavigation,
    editedFooterNavigation,
    setEditedFooterNavigation,
    editedPages,
    setEditedPages,

    // UI state
    selection,
    setSelection,
    pageToDelete,
    setPageToDelete,
    hasChanges,
    hasExistingHomePage,

    // Mutation state
    isSaving: updateMutation.isPending,
    isEnablingIndexPage: updateGroupIndexMutation.isPending,

    // Handlers
    handleSave,
    handleAddPage,
    handleTemplateSelected,
    handleCreatePageFromNavigation,
    handleUpdatePage,
    handleDeletePage,
    confirmDeletePage,
    handleDuplicatePage,
    handleAddPageToNavigation,
    handleEnableGroupIndexPage,

    // i18n
    i18nLanguage: i18n.language,
  }
}
