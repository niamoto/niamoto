/**
 * useSiteBuilderState - State management hook for the Site Builder
 *
 * Phase C: unified tree is the source of truth for page structure.
 * editedSite and editedFooterNavigation remain separate (independent concerns).
 * On save, decomposeUnifiedTree() reconstructs navigation[] + static_pages[] for the API.
 */

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
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

  // Sync local state from API data.
  // First load: wait for groups to avoid misclassifying collections as external links.
  // Subsequent siteConfig changes (after save): rebuild immediately.
  // Groups-only changes (after enabling index): patch hasIndex without full rebuild.
  const prevSiteConfigRef = useRef(siteConfig)
  const initialBuildDone = useRef(false)

  useEffect(() => {
    if (!siteConfig) return

    const siteConfigChanged = siteConfig !== prevSiteConfigRef.current
    prevSiteConfigRef.current = siteConfig

    if (!initialBuildDone.current) {
      // First build: wait for groups to be loaded
      if (groupsLoading) return
      initialBuildDone.current = true
    } else if (!siteConfigChanged) {
      // After initial build, only rebuild if siteConfig actually changed
      // (avoids discarding edits when groupsLoading toggles)
      return
    }

    setEditedSite(siteConfig.site)
    setEditedFooterNavigation(siteConfig.footer_navigation || [])
    setAllPages(siteConfig.static_pages)
    resetIdCounter()
    setUnifiedTree(
      buildUnifiedTree(siteConfig.navigation, siteConfig.static_pages, groups)
    )
  }, [siteConfig, groupsLoading])

  // When groups change (e.g. after enabling index page), patch hasIndex on existing
  // tree items without discarding unsaved edits
  useEffect(() => {
    if (!initialBuildDone.current || groups.length === 0) return
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
    const filtered = hasExistingHomePage
      ? templates.filter((template) => template.name !== ROOT_INDEX_TEMPLATE)
      : templates
    // Smart default: templates not yet used appear first
    const usedTemplates = new Set(allPages.map(p => p.template))
    return [...filtered].sort((a, b) => {
      const aUsed = usedTemplates.has(a.name) ? 1 : 0
      const bUsed = usedTemplates.has(b.name) ? 1 : 0
      return aUsed - bUsed
    })
  }, [hasExistingHomePage, templatesData, allPages])

  // ---------------------------------------------------------------------------
  // Save — decompose tree → API format
  // ---------------------------------------------------------------------------

  /** Save with explicit payload (used by wizard auto-save) */
  const saveConfig = async (data: {
    site: SiteSettings
    navigation: import('@/shared/hooks/useSiteConfig').NavigationItem[]
    footer_navigation: FooterSection[]
    static_pages: StaticPage[]
  }) => {
    if (!siteConfig) return
    await updateMutation.mutateAsync({
      ...data,
      template_dir: siteConfig.template_dir,
      output_dir: siteConfig.output_dir,
      copy_assets_from: siteConfig.copy_assets_from,
    })
  }

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
      const item = findTreeItem(prev, i => i.id === itemId)
      if (!item) return prev

      // External links cannot be hidden (they have no backing store outside navigation[]).
      // They can only be deleted.
      if (item.type === 'external-link') return prev

      const willBeHidden = item.visible

      if (willBeHidden) {
        // Hiding: remove from current position and add to root hidden section.
        // Children are preserved so showing it again restores the submenu.
        const treeWithout = removeTreeItem(prev, itemId)
        const hiddenItem = { ...item, visible: false }
        const roots = [...treeWithout, hiddenItem]
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

  const updateExternalLink = useCallback((itemId: string, label: import('@/components/ui/localized-input').LocalizedString, url: string) => {
    setUnifiedTree(prev => updateTreeItem(prev, itemId, item => ({
      ...item,
      label,
      url,
    })))
  }, [])

  // ---------------------------------------------------------------------------
  // Menu label helpers (for StaticPageEditor / GroupPageViewer)
  // ---------------------------------------------------------------------------

  /** Find all tree items referencing a given page (by pageRef). A page can appear multiple times (root + submenus). */
  const findMenuRefsForPage = useCallback((pageName: string): UnifiedTreeItem[] => {
    const results: UnifiedTreeItem[] = []
    const walk = (items: UnifiedTreeItem[]) => {
      for (const item of items) {
        if (item.type === 'page' && item.pageRef === pageName && item.visible) results.push(item)
        walk(item.children)
      }
    }
    walk(unifiedTree)
    return results
  }, [unifiedTree])

  /** Find all tree items referencing a given collection (by collectionRef). */
  const findMenuRefsForCollection = useCallback((groupName: string): UnifiedTreeItem[] => {
    const results: UnifiedTreeItem[] = []
    const walk = (items: UnifiedTreeItem[]) => {
      for (const item of items) {
        if (item.type === 'collection' && item.collectionRef === groupName && item.visible) results.push(item)
        walk(item.children)
      }
    }
    walk(unifiedTree)
    return results
  }, [unifiedTree])

  /** Update the label of a specific tree item by id. */
  const updateMenuItemLabel = useCallback((itemId: string, label: import('@/components/ui/localized-input').LocalizedString) => {
    setUnifiedTree(prev => updateTreeItem(prev, itemId, item => ({ ...item, label })))
  }, [])

  /** Remove a menu occurrence. If other visible occurrences exist for the same
   *  page/collection, just delete this node. Otherwise hide it (move to hidden section). */
  const removeMenuItem = useCallback((itemId: string) => {
    setUnifiedTree(prev => {
      const item = findTreeItem(prev, i => i.id === itemId)
      if (!item) return prev

      // Count other visible occurrences of the same page or collection
      const ref = item.pageRef || item.collectionRef
      const hasOtherVisible = ref ? !!findTreeItem(prev, i =>
        i.id !== itemId && i.visible &&
        ((item.type === 'page' && i.pageRef === ref) ||
         (item.type === 'collection' && i.collectionRef === ref))
      ) : false

      const treeWithout = removeTreeItem(prev, itemId)

      if (hasOtherVisible) {
        // Other occurrences exist — just delete this node, no hidden copy
        return treeWithout
      }

      // Last occurrence — hide instead of delete (preserves the item)
      const hiddenItem = { ...item, visible: false, children: [] }
      const menuItems = treeWithout.filter(i => i.visible)
      const hiddenItems = treeWithout.filter(i => !i.visible)
      return [...menuItems, hiddenItem, ...hiddenItems]
    })
  }, [])

  /** Add a page to the menu as a visible item. */
  const addPageToMenu = useCallback((pageName: string) => {
    const page = allPages.find(p => p.name === pageName)
    if (!page) return
    setUnifiedTree(prev => {
      // If the page is already in the tree as hidden, make it visible
      const existing = findTreeItem(prev, i => i.type === 'page' && i.pageRef === pageName && !i.visible)
      if (existing) {
        const updated = updateTreeItem(prev, existing.id, i => ({ ...i, visible: true }))
        const menuItems = updated.filter(i => i.visible)
        const hiddenItems = updated.filter(i => !i.visible)
        return [...menuItems, ...hiddenItems]
      }
      // Otherwise create a new visible item
      const newItem: UnifiedTreeItem = {
        id: `page-menu-${Date.now()}`,
        type: 'page',
        label: page.name,
        visible: true,
        pageRef: page.name,
        url: `/${page.output_file}`,
        template: page.template,
        children: [],
      }
      const menuItems = prev.filter(i => i.visible)
      const hiddenItems = prev.filter(i => !i.visible)
      return [...menuItems, newItem, ...hiddenItems]
    })
  }, [allPages])

  /** Add a collection to the menu as a visible item. */
  const addCollectionToMenu = useCallback((groupName: string) => {
    const group = groups.find(g => g.name === groupName)
    if (!group || !group.index_output_pattern) return
    setUnifiedTree(prev => {
      const existing = findTreeItem(prev, i => i.type === 'collection' && i.collectionRef === groupName && !i.visible)
      if (existing) {
        const updated = updateTreeItem(prev, existing.id, i => ({ ...i, visible: true }))
        const menuItems = updated.filter(i => i.visible)
        const hiddenItems = updated.filter(i => !i.visible)
        return [...menuItems, ...hiddenItems]
      }
      const newItem: UnifiedTreeItem = {
        id: `collection-menu-${Date.now()}`,
        type: 'collection',
        label: group.name,
        visible: true,
        collectionRef: group.name,
        url: `/${group.index_output_pattern}`,
        hasIndex: true,
        children: [],
      }
      const menuItems = prev.filter(i => i.visible)
      const hiddenItems = prev.filter(i => !i.visible)
      return [...menuItems, newItem, ...hiddenItems]
    })
  }, [groups])

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
    saveConfig,
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

    // Menu label helpers (for StaticPageEditor / GroupPageViewer)
    findMenuRefsForPage,
    findMenuRefsForCollection,
    updateMenuItemLabel,
    removeMenuItem,
    addPageToMenu,
    addCollectionToMenu,

    // Tree mutations (for UnifiedSiteTree)
    toggleItemVisibility,
    addExternalLink,
    removeExternalLink,
    updateExternalLink,

    // i18n
    i18nLanguage: i18n.language,
  }
}
