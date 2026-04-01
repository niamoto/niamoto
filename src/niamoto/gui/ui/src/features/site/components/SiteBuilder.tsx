/**
 * SiteBuilder - Unified site configuration interface
 *
 * Split Preview layout with:
 * - Left panel: Tree navigation (Pages, Navigation, Settings, Collections)
 * - Center panel: Contextual editor
 * - Right panel: Live preview (toggleable)
 *
 * Orchestrator component — state lives in useSiteBuilderState,
 * sub-components handle display.
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Loader2,
  Save,
  AlertCircle,
  Eye,
  EyeOff,
  RotateCcw,
} from 'lucide-react'
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from '@/components/ui/resizable'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { type DeviceSize } from '@/components/ui/preview-frame'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'
import { LocalizedInput } from '@/components/ui/localized-input'
import {
  useFileContent,
  useGroupIndexPreview,
  isRootIndexTemplate,
} from '@/shared/hooks/useSiteConfig'
import { LanguageProvider } from '@/shared/contexts/LanguageContext'

// Sub-components
import { SiteConfigForm } from './SiteConfigForm'
import { ThemeConfigForm } from './ThemeConfigForm'
import { NavigationBuilder } from './NavigationBuilder'
import { FooterSectionsEditor } from './FooterSectionsEditor'
import { StaticPageEditor } from './StaticPageEditor'
import { TemplateList } from './TemplateList'
import { GroupPageViewer } from './GroupPageViewer'
import { PagesOverview } from './PagesOverview'
import { SitePreview, GroupIndexPreviewPanel } from './SiteBuilderPreview'
import { UnifiedSiteTree } from './UnifiedSiteTree'

// Hooks
import { useSiteBuilderState } from '../hooks/useSiteBuilderState'
import { buildUnifiedTree, resetIdCounter } from '../hooks/useUnifiedSiteTree'
import { generateFooterFromTree } from '../utils/generateFooter'
import { SiteSetupWizard } from './SiteSetupWizard'

// =============================================================================
// MAIN SITE BUILDER COMPONENT
// =============================================================================

interface SiteBuilderProps {
  initialSection?: 'general' | 'appearance' | 'navigation' | 'pages'
}

export function SiteBuilder({ initialSection = 'pages' }: SiteBuilderProps) {
  const { t } = useTranslation(['site', 'common'])
  const state = useSiteBuilderState(initialSection)
  const [showWizard, setShowWizard] = useState(false)
  const [wizardDismissed, setWizardDismissed] = useState(false)

  // Adapter: when NavigationBuilder or StaticPageEditor update navigation[],
  // rebuild the full tree. External links cannot be hidden (P1-a fix), so
  // all external links are in navigation[] and the rebuild is lossless.
  // Hidden pages/collections survive via their backing stores (allPages, groups).
  const handleNavigationChange = (newNavigation: import('@/shared/hooks/useSiteConfig').NavigationItem[]) => {
    resetIdCounter()
    state.setUnifiedTree(buildUnifiedTree(newNavigation, state.allPages, state.groups))
  }

  // Preview state
  const currentGroupForPreview = state.selection?.type === 'group'
    ? state.groups.find((g) => g.name === state.selection?.id)
    : null
  const groupHasIndex = currentGroupForPreview?.index_generator?.enabled ?? false
  const previewAvailable = state.selection?.type === 'page'
    || (state.selection?.type === 'appearance' && state.editedPages.length > 0)
    || (state.selection?.type === 'group' && groupHasIndex)
  const [previewEnabled, setPreviewEnabled] = useState(false)
  const showPreview = previewAvailable && previewEnabled
  const [previewDevice, setPreviewDevice] = useState<DeviceSize>('desktop')

  // Group index preview
  const groupIndexPreviewMutation = useGroupIndexPreview()
  const [groupIndexHtml, setGroupIndexHtml] = useState<string | null>(null)

  // File content for preview
  const previewPageForAppearance = state.selection?.type === 'appearance' ? state.editedPages[0] : null
  const previewFilePath = state.selection?.type === 'page'
    ? state.editedPages.find((p) => p.name === state.selection?.id)?.context?.content_source
    : previewPageForAppearance?.context?.content_source ?? null
  const { data: previewFileData } = useFileContent(previewFilePath)

  const loadGroupIndexPreview = () => {
    if (state.selection?.type === 'group' && groupHasIndex && state.selection.id) {
      groupIndexPreviewMutation.mutate(
        {
          groupName: state.selection.id,
          request: {
            site: state.editedSite as Record<string, unknown>,
            navigation: state.editedNavigation.map(n => ({
              text: n.text as string,
              url: n.url,
              children: n.children,
            })),
            gui_lang: state.i18nLanguage?.split('-')[0] || 'fr',
          },
        },
        {
          onSuccess: (data) => setGroupIndexHtml(data.html),
          onError: (error) => {
            setGroupIndexHtml(`<div style="padding: 20px; color: #ef4444;">Erreur: ${error.message}</div>`)
          },
        }
      )
    }
  }

  useEffect(() => {
    if (state.selection?.type === 'group' && groupHasIndex && previewEnabled && state.selection.id) {
      loadGroupIndexPreview()
    } else if (state.selection?.type !== 'group') {
      setGroupIndexHtml(null)
    }
  }, [state.selection?.type, state.selection?.id, groupHasIndex, previewEnabled])

  // Current page for preview
  const currentPage = state.selection?.type === 'page'
    ? state.editedPages.find((p) => p.name === state.selection?.id)
    : state.selection?.type === 'appearance' && state.editedPages.length > 0
      ? state.editedPages[0]
      : null

  const previewFileContent = previewFileData?.content

  // Current group for viewer
  const currentGroup = state.selection?.type === 'group'
    ? state.groups.find((g) => g.name === state.selection?.id)
    : null

  // Preview link click handler
  const handlePreviewLinkClick = (href: string) => {
    const normalizedHref = href.replace(/^\//, '')
    const filename = normalizedHref.split('/').pop() || href

    const groupByIndex = state.groups.find(g => {
      const indexPattern = g.index_output_pattern || `${g.name}/index.html`
      return normalizedHref === indexPattern
    })
    if (groupByIndex) {
      state.setSelection({ type: 'group', id: groupByIndex.name })
      toast.info(t('common:messages.navigatingTo', { name: `${groupByIndex.name}/` }))
      return
    }

    const groupByPath = state.groups.find(g => {
      return normalizedHref.startsWith(`${g.name}/`) && normalizedHref !== `${g.name}/index.html`
    })
    if (groupByPath) {
      state.setSelection({ type: 'group', id: groupByPath.name })
      toast.info(t('preview.collectionDetailPage', { group: groupByPath.name }), {
        description: t('preview.collectionDetailPageDesc'),
      })
      return
    }

    const targetPage = state.editedPages.find(p =>
      p.output_file === normalizedHref ||
      p.output_file === href
    ) || state.editedPages.find(p =>
      p.output_file === filename
    )
    if (targetPage) {
      state.setSelection({ type: 'page', id: targetPage.name })
      toast.info(t('common:messages.navigatingTo', { name: targetPage.name }))
      return
    }

    toast.warning(t('common:messages.pageNotFound', { href }))
  }

  // Check if site is empty (condition on API data, not local state)
  const isSiteEmpty = state.siteConfig &&
    state.siteConfig.static_pages.length === 0 &&
    state.siteConfig.navigation.length === 0

  // Wizard completion handler — applies preset and auto-saves so that
  // siteConfig refreshes (otherwise isSiteEmpty stays true and the wizard reopens)
  const handleWizardComplete = async (result: {
    tree: import('../hooks/useUnifiedSiteTree').UnifiedTreeItem[]
    pages: import('@/shared/hooks/useSiteConfig').StaticPage[]
    footerSections: import('@/shared/hooks/useSiteConfig').FooterSection[]
    site: import('@/shared/hooks/useSiteConfig').SiteSettings
  }) => {
    state.setAllPages(result.pages)
    state.setUnifiedTree(result.tree)
    state.setEditedFooterNavigation(result.footerSections)
    state.setEditedSite(result.site)
    state.setSelection(null)
    setShowWizard(false)
    setWizardDismissed(true)

    // Auto-save: persist immediately so siteConfig refreshes and isSiteEmpty becomes false
    if (state.siteConfig) {
      const { decomposeUnifiedTree } = await import('../hooks/useUnifiedSiteTree')
      const { navigation, staticPages } = decomposeUnifiedTree(result.tree, result.pages)
      try {
        await state.saveConfig({
          site: result.site,
          navigation,
          footer_navigation: result.footerSections,
          static_pages: staticPages,
        })
        toast.success(t('presets.applied'))
      } catch {
        toast.success(t('presets.applied'))
        // Save failed but local state is applied — user can retry save manually
      }
    } else {
      toast.success(t('presets.applied'))
    }
  }

  // Render editor based on selection
  const renderEditor = () => {
    // Show wizard for empty sites (unless dismissed) or when explicitly triggered
    if ((!state.selection && isSiteEmpty && !wizardDismissed) || showWizard) {
      return (
        <SiteSetupWizard
          groups={state.groups}
          editedSite={state.editedSite}
          onComplete={handleWizardComplete}
          onSetEditedSite={state.setEditedSite}
        />
      )
    }

    if (!state.selection) {
      return (
        <PagesOverview
          staticPages={state.editedPages}
          groups={state.groups}
          navigation={state.editedNavigation}
          footerNavigation={state.editedFooterNavigation}
          onSelectPage={(name) => state.setSelection({ type: 'page', id: name })}
          onSelectGroup={(name) => state.setSelection({ type: 'group', id: name })}
          onAddPage={state.handleAddPage}
          onDeletePage={state.handleDeletePage}
          onDuplicatePage={state.handleDuplicatePage}
          onAddToNavigation={state.handleAddPageToNavigation}
        />
      )
    }

    switch (state.selection.type) {
      case 'general':
        return (
          <ScrollArea className="h-full">
            <div className="p-6">
              <SiteConfigForm config={state.editedSite} onChange={state.setEditedSite} />
            </div>
          </ScrollArea>
        )

      case 'appearance':
        return (
          <ScrollArea className="h-full">
            <div className="p-6">
              <ThemeConfigForm config={state.editedSite} onChange={state.setEditedSite} />
            </div>
          </ScrollArea>
        )

      case 'navigation':
        return (
          <ScrollArea className="h-full">
            <div className="p-6">
                <NavigationBuilder
                  items={state.editedNavigation}
                  onChange={handleNavigationChange}
                  staticPages={state.editedPages}
                  groups={state.groups}
                  templates={state.availableNewPageTemplates}
                  onCreatePage={state.handleCreatePageFromNavigation}
                  title={t('builder.mainMenu')}
                  description={t('navigation.mainDescription')}
                  allowSubmenus={true}
                />
            </div>
          </ScrollArea>
        )

      case 'footer':
        return (
          <ScrollArea className="h-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">{t('tree.footerMenu')}</h2>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const generated = generateFooterFromTree(state.unifiedTree, state.editedSite)
                    state.setEditedFooterNavigation(generated)
                    toast.success(t('footer.regenerated'))
                  }}
                >
                  {t('footer.regenerate')}
                </Button>
              </div>
              <FooterSectionsEditor
                sections={state.editedFooterNavigation}
                onChange={state.setEditedFooterNavigation}
                staticPages={state.editedPages}
                groups={state.groups}
              />
            </div>
          </ScrollArea>
        )

      case 'page': {
        const pageIndex = state.editedPages.findIndex((p) => p.name === state.selection?.id)
        const page = pageIndex >= 0 ? state.editedPages[pageIndex] : null
        if (!page) {
          return (
            <div className="flex h-full items-center justify-center">
              <p className="text-muted-foreground">{t('common:messages.notFound')}</p>
            </div>
          )
        }
        return (
          <StaticPageEditor
            key={`page-${pageIndex}`}
            page={page}
            onChange={state.handleUpdatePage}
            onDelete={() => state.handleDeletePage(page.name)}
            onBack={() => state.setSelection(null)}
            hasExistingIndexPage={state.editedPages.some(
              (candidate) =>
                candidate.name !== page.name && isRootIndexTemplate(candidate.template)
            )}
            menuRefs={state.findMenuRefsForPage(page.name).map(item => ({ id: item.id, label: item.label }))}
            onUpdateMenuLabel={state.updateMenuItemLabel}
            onRemoveMenuItem={state.removeMenuItem}
            onAddToMenu={() => state.addPageToMenu(page.name)}
          />
        )
      }

      case 'group':
        if (!currentGroup) {
          return (
            <div className="flex h-full items-center justify-center">
              <p className="text-muted-foreground">{t('common:messages.notFound')}</p>
            </div>
          )
        }
        return (
          <ScrollArea className="h-full">
            <div className="p-6">
              <GroupPageViewer
                group={currentGroup}
                onBack={() => state.setSelection(null)}
                onEnableIndexPage={() => state.handleEnableGroupIndexPage(currentGroup.name)}
                isEnablingIndexPage={state.isEnablingIndexPage}
                menuRefs={state.findMenuRefsForCollection(currentGroup.name).map(item => ({ id: item.id, label: item.label }))}
                onUpdateMenuLabel={state.updateMenuItemLabel}
                onRemoveMenuItem={state.removeMenuItem}
                onAddToMenu={() => state.addCollectionToMenu(currentGroup.name)}
              />
            </div>
          </ScrollArea>
        )

      case 'new-page':
        return (
          <TemplateList
            templates={state.availableNewPageTemplates}
            onSelect={state.handleTemplateSelected}
            onBack={() => state.setSelection(null)}
          />
        )

      case 'external-link': {
        const linkItem = state.unifiedTree
          .flatMap(i => [i, ...i.children])
          .find(i => i.type === 'external-link' && i.id === state.selection?.id)
        if (!linkItem) return null
        return (
          <ScrollArea className="h-full">
            <div className="p-6 space-y-4">
              <h2 className="text-lg font-semibold">{t('navigation.editLink')}</h2>
              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium">{t('navigation.linkText')}</label>
                  <div className="mt-1">
                    <LocalizedInput
                      value={linkItem.label}
                      onChange={(val) => state.updateExternalLink(linkItem.id, val ?? '', linkItem.url ?? '')}
                      placeholder="Link text"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium">URL</label>
                  <input
                    type="url"
                    className="mt-1 w-full rounded-md border px-3 py-2 text-sm"
                    value={linkItem.url ?? ''}
                    onChange={(e) => state.updateExternalLink(linkItem.id, linkItem.label, e.target.value)}
                    placeholder="https://"
                  />
                </div>
              </div>
            </div>
          </ScrollArea>
        )
      }

      default:
        return null
    }
  }

  // Loading state
  if (state.isLoading) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{t('messages.loadingConfig')}</p>
        </div>
      </div>
    )
  }

  // Error state
  if (state.error) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {t('messages.loadError', { error: state.error instanceof Error ? state.error.message : t('common:messages.unknownError') })}
          </AlertDescription>
        </Alert>
        <Button onClick={() => state.refetch()} className="mt-4">
          {t('messages.retry')}
        </Button>
      </div>
    )
  }

  return (
    <LanguageProvider
      languages={state.editedSite.languages || [state.editedSite.lang]}
      defaultLang={state.editedSite.lang}
    >
    <div className="flex h-full flex-col">
      {/* Header / Toolbar */}
      <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold">{state.editedSite.title || 'Site Builder'}</h1>
          <p className="text-xs text-muted-foreground">
            {t('description')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!isSiteEmpty && !showWizard && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                if (window.confirm(t('wizard.reconfigureWarning'))) {
                  setShowWizard(true)
                }
              }}
            >
              <RotateCcw className="h-4 w-4 mr-1" />
              {t('wizard.reconfigure')}
            </Button>
          )}
          {previewAvailable && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPreviewEnabled(!previewEnabled)}
            >
              {previewEnabled ? (
                <EyeOff className="h-4 w-4 mr-2" />
              ) : (
                <Eye className="h-4 w-4 mr-2" />
              )}
              {previewEnabled ? t('common:actions.hidePreview') : t('preview.title')}
            </Button>
          )}
          {state.hasChanges && (
            <Button
              size="sm"
              onClick={state.handleSave}
              disabled={state.isSaving}
            >
              {state.isSaving ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Save className="h-4 w-4 mr-2" />
              )}
              {t('common:actions.save')}
            </Button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <ResizablePanelGroup direction="horizontal" className="flex-1 overflow-hidden">
        {/* Left Panel - Unified Tree */}
        <ResizablePanel id="tree" order={0} defaultSize={15} minSize={12} maxSize={25}>
          <UnifiedSiteTree
            items={state.unifiedTree}
            selection={state.selection}
            onSelect={state.setSelection}
            onToggleVisibility={state.toggleItemVisibility}
            onTreeChange={state.setUnifiedTree}
            onAddPage={state.handleAddPage}
            onAddExternalLink={state.addExternalLink}
            onRemoveExternalLink={state.removeExternalLink}
          />
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Center Panel - Editor */}
        <ResizablePanel id="editor" order={1} defaultSize={showPreview ? 50 : 85} minSize={30} className="overflow-hidden">
          {renderEditor()}
        </ResizablePanel>

        {/* Right Panel - Preview (optional) */}
        {showPreview && (
          <>
            <ResizableHandle withHandle />
            <ResizablePanel id="preview" order={2} defaultSize={35} minSize={20} maxSize={50}>
              {state.selection?.type === 'group' ? (
                <GroupIndexPreviewPanel
                  html={groupIndexHtml}
                  isLoading={groupIndexPreviewMutation.isPending}
                  device={previewDevice}
                  onDeviceChange={setPreviewDevice}
                  groupName={state.selection.id ?? ''}
                  onLinkClick={handlePreviewLinkClick}
                  onRefresh={loadGroupIndexPreview}
                />
              ) : (
                <SitePreview
                  page={currentPage ?? null}
                  site={state.editedSite}
                  navigation={state.editedNavigation}
                  footerNavigation={state.editedFooterNavigation}
                  device={previewDevice}
                  onDeviceChange={setPreviewDevice}
                  fileContent={previewFileContent}
                  onLinkClick={handlePreviewLinkClick}
                />
              )}
            </ResizablePanel>
          </>
        )}
      </ResizablePanelGroup>

      {/* Delete confirmation dialog */}
      <AlertDialog open={!!state.pageToDelete} onOpenChange={(open) => !open && state.setPageToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t('common:dialogs.deleteConfirm', { item: state.pageToDelete })}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('common:dialogs.cannotUndo')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common:actions.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={state.confirmDeletePage}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('common:actions.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
    </LanguageProvider>
  )
}

export default SiteBuilder
