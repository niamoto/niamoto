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
  Settings,
  Palette,
  Navigation,
  FileText,
  Folder,
  Lock,
  Loader2,
  Save,
  AlertCircle,
  Eye,
  EyeOff,
  Link2,
} from 'lucide-react'
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from '@/components/ui/resizable'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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
import { cn } from '@/lib/utils'
import {
  useFileContent,
  useGroupIndexPreview,
  type NavigationItem,
  type FooterSection,
  type GroupInfo,
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
import { PagesOverview, getTemplateIcon, isPageInNavigation } from './PagesOverview'
import { SitePreview, GroupIndexPreviewPanel } from './SiteBuilderPreview'

// State hook
import { useSiteBuilderState, type Selection, type SelectionType } from '../hooks/useSiteBuilderState'

// =============================================================================
// SITE TREE COMPONENT (will be replaced by UnifiedSiteTree in Phase B)
// =============================================================================

interface SiteTreeProps {
  navigation: NavigationItem[]
  footerNavigation: FooterSection[]
  pages: import('@/shared/hooks/useSiteConfig').StaticPage[]
  groups: GroupInfo[]
  groupsLoading: boolean
  selection: Selection | null
  onSelect: (selection: Selection) => void
  onAddPage: () => void
}

function SiteTree({
  navigation,
  footerNavigation,
  pages,
  groups,
  groupsLoading,
  selection,
  onSelect,
  onAddPage,
}: SiteTreeProps) {
  const { t } = useTranslation(['site', 'common'])
  const isSelected = (type: SelectionType, id?: string) => {
    if (!selection) return false
    if (selection.type !== type) return false
    if (id !== undefined) return selection.id === id
    return true
  }

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1">
        <Accordion
          type="multiple"
          defaultValue={['pages', 'navigation', 'settings', 'collections']}
          className="px-2 py-2"
        >
          {/* Pages Section */}
          <AccordionItem value="pages" className="border-none">
            <AccordionTrigger className="py-2 text-sm hover:no-underline">
              <span className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Pages
                <Badge variant="secondary" className="ml-auto text-[10px]">
                  {pages.length}
                </Badge>
              </span>
            </AccordionTrigger>
            <AccordionContent className="pb-2">
              <div className="space-y-1 pl-6">
                {pages.length === 0 ? (
                  <p className="px-2 py-1.5 text-xs text-muted-foreground italic">
                    {t('tree.noPages')}
                  </p>
                ) : (
                  pages.map((page, index) => {
                    const Icon = getTemplateIcon(page.template)
                    const pageUrl = `/${page.output_file}`
                    const inMainNav = isPageInNavigation(pageUrl, navigation)
                    const inFooterNav = footerNavigation.some(s => s.links.some(l => l.url === pageUrl))
                    const isLinked = inMainNav || inFooterNav

                    return (
                      <button
                        key={`${page.name}-${index}`}
                        className={cn(
                          'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                          isSelected('page', page.name)
                            ? 'bg-primary/10 text-primary'
                            : 'hover:bg-muted/50'
                        )}
                        onClick={() => onSelect({ type: 'page', id: page.name })}
                      >
                        <Icon className="h-4 w-4 shrink-0" />
                        <span className="truncate flex-1 text-left">{page.name}</span>
                        {isLinked && (
                          <Link2 className="h-3 w-3 shrink-0 text-muted-foreground" />
                        )}
                      </button>
                    )
                  })
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full justify-start text-xs text-muted-foreground hover:text-foreground"
                  onClick={onAddPage}
                >
                  {t('pages.addPage')}
                </Button>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Navigation Section */}
          <AccordionItem value="navigation" className="border-none">
            <AccordionTrigger className="py-2 text-sm hover:no-underline">
              <span className="flex items-center gap-2">
                <Navigation className="h-4 w-4" />
                Navigation
              </span>
            </AccordionTrigger>
            <AccordionContent className="pb-2">
              <div className="space-y-1 pl-6">
                <button
                  className={cn(
                    'flex w-full items-center justify-between rounded-md px-2 py-1.5 text-sm transition-colors',
                    isSelected('navigation')
                      ? 'bg-primary/10 text-primary'
                      : 'hover:bg-muted/50'
                  )}
                  onClick={() => onSelect({ type: 'navigation' })}
                >
                  <span className="flex items-center gap-2">
                    <Navigation className="h-4 w-4" />
                    {t('tree.mainMenu')}
                  </span>
                  <Badge variant="secondary" className="text-[10px]">
                    {navigation.length}
                  </Badge>
                </button>
                <button
                  className={cn(
                    'flex w-full items-center justify-between rounded-md px-2 py-1.5 text-sm transition-colors',
                    isSelected('footer')
                      ? 'bg-primary/10 text-primary'
                      : 'hover:bg-muted/50'
                  )}
                  onClick={() => onSelect({ type: 'footer' })}
                >
                  <span className="flex items-center gap-2">
                    <Navigation className="h-4 w-4" />
                    {t('tree.footerMenu')}
                  </span>
                  <Badge variant="secondary" className="text-[10px]">
                    {footerNavigation.length}
                  </Badge>
                </button>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Settings Section */}
          <AccordionItem value="settings" className="border-none">
            <AccordionTrigger className="py-2 text-sm hover:no-underline">
              <span className="flex items-center gap-2">
                <Settings className="h-4 w-4" />
                {t('tree.settings')}
              </span>
            </AccordionTrigger>
            <AccordionContent className="pb-2">
              <div className="space-y-1 pl-6">
                <button
                  className={cn(
                    'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                    isSelected('general')
                      ? 'bg-primary/10 text-primary'
                      : 'hover:bg-muted/50'
                  )}
                  onClick={() => onSelect({ type: 'general' })}
                >
                  <Settings className="h-4 w-4" />
                  {t('tree.general')}
                </button>
                <button
                  className={cn(
                    'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                    isSelected('appearance')
                      ? 'bg-primary/10 text-primary'
                      : 'hover:bg-muted/50'
                  )}
                  onClick={() => onSelect({ type: 'appearance' })}
                >
                  <Palette className="h-4 w-4" />
                  {t('tree.appearance')}
                </button>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Collections Section */}
          <AccordionItem value="collections" className="border-none">
            <AccordionTrigger className="py-2 text-sm hover:no-underline">
              <span className="flex items-center gap-2">
                <Folder className="h-4 w-4 text-amber-600" />
                {t('tree.collections')}
                {groupsLoading ? (
                  <Loader2 className="h-3 w-3 animate-spin ml-auto" />
                ) : (
                  <Badge variant="secondary" className="ml-auto text-[10px]">
                    {groups.length}
                  </Badge>
                )}
              </span>
            </AccordionTrigger>
            <AccordionContent className="pb-2">
              <div className="space-y-1 pl-6">
                {groupsLoading ? (
                  <div className="flex items-center gap-2 px-2 py-1.5 text-xs text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    {t('common:status.loading')}
                  </div>
                ) : groups.length === 0 ? (
                  <p className="px-2 py-1.5 text-xs text-muted-foreground italic">
                    {t('tree.noCollections')}
                  </p>
                ) : (
                  groups.map((group, index) => (
                    <button
                      key={`${group.name}-${index}`}
                      className={cn(
                        'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors',
                        isSelected('group', group.name)
                          ? 'bg-primary/10 text-primary'
                          : 'hover:bg-muted/50'
                      )}
                      onClick={() => onSelect({ type: 'group', id: group.name })}
                    >
                      <Lock className="h-3 w-3 text-muted-foreground" />
                      <span className="truncate flex-1 text-left">{group.name}/</span>
                      <Badge variant="outline" className="text-[10px]">
                        {group.widgets_count}w
                      </Badge>
                    </button>
                  ))
                )}
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </ScrollArea>
    </div>
  )
}

// =============================================================================
// MAIN SITE BUILDER COMPONENT
// =============================================================================

interface SiteBuilderProps {
  initialSection?: 'general' | 'appearance' | 'navigation' | 'pages'
}

export function SiteBuilder({ initialSection = 'pages' }: SiteBuilderProps) {
  const { t } = useTranslation(['site', 'common'])
  const state = useSiteBuilderState(initialSection)

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

  // Render editor based on selection
  const renderEditor = () => {
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
                  onChange={state.setEditedNavigation}
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
            navigation={state.editedNavigation}
            onUpdateNavigation={state.setEditedNavigation}
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
        {/* Left Panel - Tree */}
        <ResizablePanel id="tree" order={0} defaultSize={15} minSize={12} maxSize={25}>
          <ScrollArea className="h-full">
            <SiteTree
              navigation={state.editedNavigation}
              footerNavigation={state.editedFooterNavigation}
              pages={state.editedPages}
              groups={state.groups}
              groupsLoading={state.groupsLoading}
              selection={state.selection}
              onSelect={state.setSelection}
              onAddPage={state.handleAddPage}
            />
          </ScrollArea>
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
