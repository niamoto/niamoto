/**
 * useSiteBuilderState - State management hook for the Site Builder
 *
 * Phase C: unified tree is the source of truth for page structure.
 * editedSite and editedFooterNavigation remain separate (independent concerns).
 * On save, decomposeUnifiedTree() reconstructs navigation[] + static_pages[] for the API.
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import {
  useSiteConfig,
  useUpdateSiteConfig,
  useUpdateGroupIndexConfig,
  useGroups,
  useTemplates,
  type SiteSettings,
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
import {
  type UnifiedTreeItem,
  buildUnifiedTree,
  decomposeUnifiedTree,
  resetIdCounter,
} from './useUnifiedSiteTree'

export type SelectionType = 'general' | 'appearance' | 'navigation' | 'footer' | 'page' | 'group' | 'new-page' | 'external-link'

export interface Selection {
  type: SelectionType
  id?: string
}

// =============================================================================
// TREE MUTATION HELPERS
// =============================================================================

/** Find and update an item in the tree (shallow: root + children only) */
function updateTreeItem(
  tree: UnifiedTreeItem[],
  id: string,
  updater: (item: UnifiedTreeItem) => UnifiedTreeItem,
): UnifiedTreeItem[] {
  return tree.map(item => {
    if (item.id === id) return updater(item)
    if (item.children.length > 0) {
      return { ...item, children: updateTreeItem(item.children, id, updater) }
    }
    return item
  })
}

/** Remove an item from the tree by id */
function removeTreeItem(tree: UnifiedTreeItem[], id: string): UnifiedTreeItem[] {
  return tree
    .filter(item => item.id !== id)
    .map(item => ({
      ...item,
      children: removeTreeItem(item.children, id),
    }))
}

/** Find an item in the tree by a predicate */
function findTreeItem(
  tree: UnifiedTreeItem[],
  predicate: (item: UnifiedTreeItem) => boolean,
): UnifiedTreeItem | null {
  for (const item of tree) {
    if (predicate(item)) return item
    const found = findTreeItem(item.children, predicate)
    if (found) return found
  }
  return null
}

// =============================================================================
// HOOK
// =============================================================================

export function useSiteBuilderState(initialSection: string = 'pages') {
  const { t, i18n } = useTranslation(['site', 'common', 'indexConfig'])

  // Data fetching
  const { data: siteConfig, isLoading, error, refetch } = useSiteConfig()
  const { data: groupsData, isLoading: groupsLoading } = useGroups()
  const { data: templatesData } = useTemplates()
  const updateMutation = useUpdateSiteConfig()
  const updateGroupIndexMutation = useUpdateGroupIndexConfig()

  // ---------------------------------------------------------------------------
  // Source of truth: unified tree + allPages + editedSite + editedFooterNavigation
  // ---------------------------------------------------------------------------
  const [unifiedTree, setUnifiedTree] = useState<UnifiedTreeItem[]>([])
  const [allPages, setAllPages] = useState<StaticPage[]>([])
  const [editedSite, setEditedSite] = useState<SiteSettings>(DEFAULT_SITE_SETTINGS)
  const [editedFooterNavigation, setEditedFooterNavigation] = useState<FooterSection[]>([])

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

  // Sync local state from API data — only when siteConfig changes (not groups)
  useEffect(() => {
    if (siteConfig) {
      setEditedSite(siteConfig.site)
      setEditedFooterNavigation(siteConfig.footer_navigation || [])
      setAllPages(siteConfig.static_pages)
      resetIdCounter()
      setUnifiedTree(
        buildUnifiedTree(siteConfig.navigation, siteConfig.static_pages, groups)
      )
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- groups excluded intentionally:
    // re-syncing on groups change would discard unsaved tree edits
  }, [siteConfig])

  // When groups change (e.g. after enabling index page), update hasIndex on existing
  // tree items without discarding unsaved edits (reorder, toggles, external links)
  useEffect(() => {
    if (groups.length === 0) return
    setUnifiedTree(prev => {
      const groupMap = new Map(groups.map(g => [g.name, g]))
      const updateItem = (item: UnifiedTreeItem): UnifiedTreeItem => {
        if (item.type === 'collection' && item.collectionRef) {
          const group = groupMap.get(item.collectionRef)
          if (group) {
            const newHasIndex = !!group.index_output_pattern
            if (item.hasIndex !== newHasIndex) {
              return {
                ...item,
                hasIndex: newHasIndex,
                url: group.index_output_pattern ? `/${group.index_output_pattern}` : item.url,
              }
            }
          }
        }
        return { ...item, children: item.children.map(updateItem) }
      }
      return prev.map(updateItem)
    })
  }, [groups])

  // ---------------------------------------------------------------------------
  // Derived state from tree + allPages
  // ---------------------------------------------------------------------------

  /** Decompose tree for API compatibility (navigation[] + static_pages[]) */
  const decomposed = useMemo(
    () => decomposeUnifiedTree(unifiedTree, allPages),
    [unifiedTree, allPages],
  )

  /** editedNavigation and editedPages derived from tree (for backward compat with sub-components) */
  const editedNavigation = decomposed.navigation
  const editedPages = decomposed.staticPages

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
    () => hasRootIndexPage(allPages),
    [allPages]
  )

  const availableNewPageTemplates = useMemo(() => {
    const templates = templatesData?.templates ?? []
    if (!hasExistingHomePage) return templates
    return templates.filter((template) => template.name !== ROOT_INDEX_TEMPLATE)
  }, [hasExistingHomePage, templatesData])

  // ---------------------------------------------------------------------------
  // Save — decompose tree → API format
  // ---------------------------------------------------------------------------

  const handleSave = async () => {
    if (!siteConfig) return

    const { navigation, staticPages } = decomposeUnifiedTree(unifiedTree, allPages)

    const update: SiteConfigUpdate = {
      site: editedSite,
      navigation,
      footer_navigation: editedFooterNavigation,
      static_pages: staticPages,
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

  // ---------------------------------------------------------------------------
  // Page CRUD — mutate both allPages and unifiedTree
  // ---------------------------------------------------------------------------

  const handleAddPage = () => {
    setSelection({ type: 'new-page' })
  }

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
    const existingNames = new Set(allPages.map((p) => p.name))

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

    // Add to allPages
    setAllPages(prev => [...prev, newPage])

    // Add to tree as visible item at end of menu section
    const newTreeItem: UnifiedTreeItem = {
      id: `page-new-${Date.now()}`,
      type: 'page',
      label: newPage.name,
      visible: true,
      pageRef: newPage.name,
      url: `/${newPage.output_file}`,
      template: newPage.template,
      children: [],
    }
    setUnifiedTree(prev => {
      // Insert before hidden items
      const menuItems = prev.filter(i => i.visible)
      const hiddenItems = prev.filter(i => !i.visible)
      return [...menuItems, newTreeItem, ...hiddenItems]
    })

    setSelection({ type: 'page', id: newPage.name })
    toast.success(t('pages.pageCreated'), {
      description: t('pages.pageCreatedDesc', { name: newPage.name }),
    })
  }

  const handleCreatePageFromNavigation = async (pageName: string, templateName: string): Promise<StaticPage | null> => {
    if (templateName === ROOT_INDEX_TEMPLATE && hasExistingHomePage) {
      toast.error(t('messages.homePageExists'), {
        description: t('messages.homePageExistsDesc'),
      })
      return null
    }

    const existingNames = new Set(allPages.map((p) => p.name))
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

    setAllPages((pages) => [...pages, newPage])
    // The nav builder will handle the tree item via its own callback

    toast.success(t('pages.pageCreated'), {
      description: t('pages.pageCreatedDesc', { name: finalName }),
    })

    return newPage
  }

  const handleUpdatePage = (updatedPage: StaticPage) => {
    const oldName = selection?.id
    const normalizedPage = {
      ...updatedPage,
      output_file: getCanonicalStaticPageOutputFile(updatedPage),
    }

    if (
      isRootIndexTemplate(normalizedPage.template) &&
      allPages.some(
        (page) => page.name !== oldName && isRootIndexTemplate(page.template)
      )
    ) {
      toast.error(t('messages.homePageExists'), {
        description: t('messages.homePageExistsDesc'),
      })
      return
    }

    // Update allPages
    setAllPages((pages) =>
      pages.map((p) => (p.name === oldName ? normalizedPage : p))
    )

    // Update tree item refs — preserve label (custom menu text) unless
    // the label was the old page name (meaning no custom text was set)
    if (oldName) {
      const updatePageItem = (item: UnifiedTreeItem): UnifiedTreeItem => {
        if (item.type !== 'page' || item.pageRef !== oldName) return item
        const labelWasPageName = item.label === oldName
        return {
          ...item,
          // Only update label if it matched the old page name (no custom text)
          label: labelWasPageName ? normalizedPage.name : item.label,
          pageRef: normalizedPage.name,
          url: `/${normalizedPage.output_file}`,
          template: normalizedPage.template,
        }
      }

      setUnifiedTree(prev =>
        prev.map(item => {
          const updated = updatePageItem(item)
          return {
            ...updated,
            children: updated.children.map(updatePageItem),
          }
        })
      )
    }

    if (oldName && normalizedPage.name !== oldName) {
      setSelection({ type: 'page', id: normalizedPage.name })
    }
  }

  const handleDeletePage = (pageName: string) => {
    setPageToDelete(pageName)
  }

  const confirmDeletePage = async () => {
    if (!pageToDelete || !siteConfig) return

    const pageObj = allPages.find((p) => p.name === pageToDelete)
    if (!pageObj) return

    // Compute new state
    const newAllPages = allPages.filter((p) => p.name !== pageToDelete)
    const treeItem = findTreeItem(unifiedTree, i => i.type === 'page' && i.pageRef === pageToDelete)
    const newTree = treeItem ? removeTreeItem(unifiedTree, treeItem.id) : unifiedTree
    const pageUrl = `/${pageObj.output_file}`
    const newFooterNavigation = editedFooterNavigation.map((section) => ({
      ...section,
      links: section.links.filter((link) => link.url !== pageUrl),
    }))

    setPageToDelete(null)
    setSelection(null)

    // Update local state
    setAllPages(newAllPages)
    setUnifiedTree(newTree)
    setEditedFooterNavigation(newFooterNavigation)

    // Persist — decompose tree for API
    const { navigation, staticPages } = decomposeUnifiedTree(newTree, newAllPages)
    try {
      await updateMutation.mutateAsync({
        site: editedSite,
        navigation,
        footer_navigation: newFooterNavigation,
        static_pages: staticPages,
        template_dir: siteConfig.template_dir,
        output_dir: siteConfig.output_dir,
        copy_assets_from: siteConfig.copy_assets_from,
      })
      toast.success(t('pages.pageDeleted'), {
        description: t('pages.pageDeletedDesc'),
      })
    } catch (err) {
      // Revert on error
      setAllPages(allPages)
      setUnifiedTree(unifiedTree)
      setEditedFooterNavigation(editedFooterNavigation)
      toast.error(t('common:status.error'), {
        description: err instanceof Error ? err.message : t('messages.saveFailed'),
      })
    }
  }

  const handleDuplicatePage = (page: StaticPage) => {
    if (isRootIndexTemplate(page.template)) {
      toast.error(t('messages.homePageDuplicateBlocked'), {
        description: t('messages.homePageDuplicateBlockedDesc'),
      })
      return
    }

    const existingNames = new Set(allPages.map((p) => p.name))
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

    setAllPages((pages) => [...pages, newPage])

    // Add as hidden item (not in menu by default)
    const newTreeItem: UnifiedTreeItem = {
      id: `page-dup-${Date.now()}`,
      type: 'page',
      label: newName,
      visible: false,
      pageRef: newName,
      url: `/${newPage.output_file}`,
      template: newPage.template,
      children: [],
    }
    setUnifiedTree(prev => [...prev, newTreeItem])

    setSelection({ type: 'page', id: newName })
    toast.success(t('pages.pageDuplicated'), {
      description: t('pages.pageDuplicatedDesc', { name: newName }),
    })
  }

  const handleAddPageToNavigation = (page: StaticPage) => {
    // Find the tree item for this page and make it visible
    const item = findTreeItem(unifiedTree, i => i.type === 'page' && i.pageRef === page.name)
    if (item) {
      setUnifiedTree(prev => {
        const updated = updateTreeItem(prev, item.id, i => ({ ...i, visible: true }))
        // Move from hidden to end of menu section
        const menuItems = updated.filter(i => i.visible)
        const hiddenItems = updated.filter(i => !i.visible)
        return [...menuItems, ...hiddenItems]
      })
    }
    toast.success(t('navigation.linkAdded'), {
      description: t('navigation.linkAddedDesc'),
    })
  }

  // ---------------------------------------------------------------------------
  // Page ↔ menu helpers (for StaticPageEditor)
  // ---------------------------------------------------------------------------

  const isPageInMenu = useCallback((pageName: string): boolean => {
    const item = findTreeItem(unifiedTree, i => i.type === 'page' && i.pageRef === pageName)
    return item?.visible ?? false
  }, [unifiedTree])

  const togglePageInMenu = useCallback((pageName: string) => {
    const item = findTreeItem(unifiedTree, i => i.type === 'page' && i.pageRef === pageName)
    if (!item) return

    setUnifiedTree(prev => {
      const updated = updateTreeItem(prev, item.id, i => ({ ...i, visible: !i.visible }))
      // Re-sort: menu items first, then hidden
      const menuItems = updated.filter(i => i.visible)
      const hiddenItems = updated.filter(i => !i.visible)
      return [...menuItems, ...hiddenItems]
    })

    if (item.visible) {
      toast.success(t('navigation.linkRemoved'))
    } else {
      toast.success(t('navigation.linkAdded'))
    }
  }, [unifiedTree, t])

  // ---------------------------------------------------------------------------
  // Tree mutations (for UnifiedSiteTree component)
  // ---------------------------------------------------------------------------

  const toggleItemVisibility = useCallback((itemId: string) => {
    setUnifiedTree(prev => {
      // Find the item and its current visibility
      const item = findTreeItem(prev, i => i.id === itemId)
      if (!item) return prev

      const willBeHidden = item.visible

      if (willBeHidden) {
        // Hiding: remove from its current position (may be nested) and add to root as hidden
        const treeWithout = removeTreeItem(prev, itemId)
        const hiddenItem = { ...item, visible: false, children: [] }
        // Also promote any children to root hidden items
        const promotedChildren = item.children.map(c => ({ ...c, visible: false, children: [] as UnifiedTreeItem[] }))
        const roots = [...treeWithout, hiddenItem, ...promotedChildren]
        const menuItems = roots.filter(i => i.visible)
        const hiddenItems = roots.filter(i => !i.visible)
        return [...menuItems, ...hiddenItems]
      } else {
        // Showing: update visibility in place, then repartition roots
        const updated = updateTreeItem(prev, itemId, i => ({ ...i, visible: true }))
        const menuItems = updated.filter(i => i.visible)
        const hiddenItems = updated.filter(i => !i.visible)
        return [...menuItems, ...hiddenItems]
      }
    })
  }, [])

  const addExternalLink = useCallback(() => {
    const newItem: UnifiedTreeItem = {
      id: `link-${Date.now()}`,
      type: 'external-link',
      label: '',
      visible: true,
      url: 'https://',
      children: [],
    }
    setUnifiedTree(prev => {
      const menuItems = prev.filter(i => i.visible)
      const hiddenItems = prev.filter(i => !i.visible)
      return [...menuItems, newItem, ...hiddenItems]
    })
    setSelection({ type: 'external-link', id: newItem.id })
  }, [])

  const removeExternalLink = useCallback((itemId: string) => {
    setUnifiedTree(prev => removeTreeItem(prev, itemId))
    setSelection(null)
  }, [])

  const updateExternalLink = useCallback((itemId: string, label: string, url: string) => {
    setUnifiedTree(prev => updateTreeItem(prev, itemId, item => ({
      ...item,
      label,
      url,
    })))
  }, [])

  // ---------------------------------------------------------------------------
  // Group index page
  // ---------------------------------------------------------------------------

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

  // ---------------------------------------------------------------------------
  // Return
  // ---------------------------------------------------------------------------

  return {
    // Data fetching state
    siteConfig,
    isLoading,
    error,
    refetch,
    groupsLoading,
    groups,
    availableNewPageTemplates,

    // Source of truth
    unifiedTree,
    setUnifiedTree,
    allPages,
    setAllPages,

    // Derived (backward compat for sub-components that still need arrays)
    editedNavigation,
    editedPages,

    // Independent state
    editedSite,
    setEditedSite,
    editedFooterNavigation,
    setEditedFooterNavigation,

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

    // Page handlers
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

    // Page ↔ menu (for StaticPageEditor)
    isPageInMenu,
    togglePageInMenu,

    // Tree mutations (for UnifiedSiteTree)
    toggleItemVisibility,
    addExternalLink,
    removeExternalLink,
    updateExternalLink,

    // i18n
    i18nLanguage: i18n.language,
  }
}
