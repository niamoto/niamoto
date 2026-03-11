/**
 * SiteBuilder - Unified site configuration interface
 *
 * Split Preview layout with:
 * - Left panel: Tree navigation (Params, Navigation, Pages, Groups)
 * - Center panel: Contextual editor
 * - Right panel: Live preview (toggleable)
 */

import { useState, useEffect, useMemo } from 'react'
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
  Plus,
  ExternalLink as ExternalLinkIcon,
  Home,
  BookOpen,
  Users,
  Mail,
  Download,
  List,
  Newspaper,
  ScrollText,
  Link2,
  MoreHorizontal,
  Trash2,
  Copy,
  type LucideIcon,
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
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { PreviewFrame, type DeviceSize } from '@/components/ui/preview-frame'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
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
  useSiteConfig,
  useUpdateSiteConfig,
  useGroups,
  useTemplates,
  useTemplatePreview,
  useGroupIndexPreview,
  useFileContent,
  type SiteSettings,
  type NavigationItem,
  type FooterSection,
  type StaticPage,
  type SiteConfigUpdate,
  type GroupInfo,
  DEFAULT_SITE_SETTINGS,
  DEFAULT_STATIC_PAGE,
} from '@/hooks/useSiteConfig'
import { SiteConfigForm } from './SiteConfigForm'
import { ThemeConfigForm } from './ThemeConfigForm'
import { NavigationBuilder } from './NavigationBuilder'
import { FooterSectionsEditor } from './FooterSectionsEditor'
import { StaticPageEditor } from './StaticPageEditor'
import { TemplateList } from './TemplateList'
import { GroupPageViewer } from './GroupPageViewer'
import { LanguageProvider } from '@/contexts/LanguageContext'

// =============================================================================
// TYPES
// =============================================================================

type SelectionType = 'general' | 'appearance' | 'navigation' | 'footer' | 'page' | 'group' | 'new-page'

interface Selection {
  type: SelectionType
  id?: string
}

// =============================================================================
// TEMPLATE ICONS CONFIGURATION
// =============================================================================

const TEMPLATE_ICONS: Record<string, LucideIcon> = {
  'index.html': Home,
  'page.html': FileText,
  'article.html': Newspaper,
  'documentation.html': ScrollText,
  'team.html': Users,
  'contact.html': Mail,
  'resources.html': Download,
  'bibliography.html': BookOpen,
  'glossary.html': List,
}

function getTemplateIcon(template?: string): LucideIcon {
  return template ? TEMPLATE_ICONS[template] || FileText : FileText
}

// Check if a page is linked in navigation (recursive for submenus)
function isPageInNavigation(pageUrl: string, items: NavigationItem[]): 'direct' | 'parent' | null {
  for (const item of items) {
    if (item.url === pageUrl) return 'direct'
    if (item.children && item.children.length > 0) {
      // Check if this is a parent menu (has children but no direct URL)
      if (!item.url && item.children.some(child => child.url === pageUrl)) {
        return 'parent'
      }
      // Check children recursively
      const childResult = isPageInNavigation(pageUrl, item.children)
      if (childResult) return childResult
    }
  }
  return null
}

// =============================================================================
// SITE TREE COMPONENT
// =============================================================================

interface SiteTreeProps {
  navigation: NavigationItem[]
  footerNavigation: FooterSection[]
  pages: StaticPage[]
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
          defaultValue={['pages', 'navigation', 'settings', 'groups']}
          className="px-2 py-2"
        >
          {/* Pages Section - EN PREMIER */}
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

          {/* Groups Section */}
          <AccordionItem value="groups" className="border-none">
            <AccordionTrigger className="py-2 text-sm hover:no-underline">
              <span className="flex items-center gap-2">
                <Folder className="h-4 w-4 text-amber-600" />
                {t('tree.groups')}
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
                    {t('tree.noGroups')}
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
// PAGES OVERVIEW COMPONENT
// =============================================================================

interface PagesOverviewProps {
  staticPages: StaticPage[]
  groups: GroupInfo[]
  navigation: NavigationItem[]
  footerNavigation: FooterSection[]
  onSelectPage: (pageName: string) => void
  onSelectGroup: (groupName: string) => void
  onAddPage: () => void
  onDeletePage: (pageName: string) => void
  onDuplicatePage: (page: StaticPage) => void
  onAddToNavigation: (page: StaticPage) => void
}

function PagesOverview({
  staticPages,
  groups,
  navigation,
  footerNavigation,
  onSelectPage,
  onSelectGroup,
  onAddPage,
  onDeletePage,
  onDuplicatePage,
  onAddToNavigation,
}: PagesOverviewProps) {
  const { t } = useTranslation(['site', 'common'])

  // Helper to get template name without extension
  const getTemplateName = (template?: string) => {
    if (!template) return null
    return template.replace('.html', '')
  }
  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">{t('pages.title')}</h2>
            <p className="text-sm text-muted-foreground">
              {t('pages.subtitle')}
            </p>
          </div>
          <Button onClick={onAddPage}>
            <Plus className="h-4 w-4 mr-2" />
            {t('pages.newPage')}
          </Button>
        </div>

        {/* Static Pages Section */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <h3 className="font-medium">{t('pages.staticPages')}</h3>
            <Badge variant="secondary" className="text-xs">
              {staticPages.length}
            </Badge>
          </div>

          {staticPages.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-8">
                <FileText className="h-10 w-10 text-muted-foreground/50 mb-3" />
                <p className="text-sm text-muted-foreground mb-3">
                  {t('pages.noStaticPages')}
                </p>
                <Button variant="outline" size="sm" onClick={onAddPage}>
                  <Plus className="h-4 w-4 mr-2" />
                  {t('pages.createPage')}
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {staticPages.map((page, index) => {
                const hasContent = page.context?.content_markdown || page.context?.content_source
                const Icon = getTemplateIcon(page.template)
                const pageUrl = `/${page.output_file}`
                const inMainNav = isPageInNavigation(pageUrl, navigation)
                const inFooterNav = footerNavigation.some(s => s.links.some(l => l.url === pageUrl))
                const isLinked = inMainNav || inFooterNav
                const templateName = getTemplateName(page.template)

                return (
                  <Card
                    key={`${page.name}-${index}`}
                    className="group cursor-pointer hover:border-primary/50 transition-colors"
                    onClick={() => onSelectPage(page.name)}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between">
                        <CardTitle className="text-sm flex items-center gap-2">
                          <Icon className="h-4 w-4 shrink-0" />
                          <span className="truncate">{page.name}</span>
                        </CardTitle>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                            <DropdownMenuItem onClick={() => onSelectPage(page.name)}>
                              <FileText className="h-4 w-4 mr-2" />
                              {t('pages.edit')}
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => onDuplicatePage(page)}>
                              <Copy className="h-4 w-4 mr-2" />
                              {t('common:actions.duplicate')}
                            </DropdownMenuItem>
                            {!isLinked && (
                              <DropdownMenuItem onClick={() => onAddToNavigation(page)}>
                                <Link2 className="h-4 w-4 mr-2" />
                                {t('navigation.addToMenu')}
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                              className="text-destructive focus:text-destructive"
                              onClick={() => onDeletePage(page.name)}
                            >
                              <Trash2 className="h-4 w-4 mr-2" />
                              {t('common:actions.delete')}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                      <CardDescription className="text-xs font-mono flex items-center gap-2">
                        <span className="truncate">{page.output_file}</span>
                        {isLinked && (
                          <span className="flex items-center gap-0.5 text-primary shrink-0" title={inMainNav ? t('navigation.inMainMenu') : t('navigation.inFooterMenu')}>
                            <Link2 className="h-3 w-3" />
                          </span>
                        )}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {/* Content status */}
                          <div className="flex items-center gap-1.5">
                            {hasContent ? (
                              <>
                                <div className="h-2 w-2 rounded-full bg-green-500" />
                                <span className="text-xs text-muted-foreground">{t('pages.contentMd')}</span>
                              </>
                            ) : (
                              <>
                                <div className="h-2 w-2 rounded-full bg-muted-foreground/30" />
                                <span className="text-xs text-muted-foreground">{t('pages.empty')}</span>
                              </>
                            )}
                          </div>
                        </div>
                        {/* Template badge */}
                        {templateName && (
                          <Badge variant="outline" className="text-[10px] h-5 font-normal">
                            {templateName}
                          </Badge>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </div>

        {/* Groups Section */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Folder className="h-4 w-4 text-amber-600" />
              <h3 className="font-medium">{t('groups.title')}</h3>
              <Badge variant="secondary" className="text-xs">
                {groups.length}
              </Badge>
            </div>
            <Button variant="link" size="sm" className="text-xs" asChild>
              <a href="/flow?tab=export">
                {t('groups.configureInExport')}
                <ExternalLinkIcon className="h-3 w-3 ml-1" />
              </a>
            </Button>
          </div>

          {groups.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-8">
                <Folder className="h-10 w-10 text-muted-foreground/50 mb-3" />
                <p className="text-sm text-muted-foreground">
                  {t('groups.noGroupsConfigured')}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {t('groups.groupsDefinedInExport')}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {groups.map((group, index) => {
                const hasIndex = group.index_generator?.enabled
                return (
                  <Card
                    key={`${group.name}-${index}`}
                    className="cursor-pointer hover:border-primary/50 transition-colors"
                    onClick={() => onSelectGroup(group.name)}
                  >
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Folder className="h-4 w-4 text-amber-600" />
                        {group.name}/
                      </CardTitle>
                      <CardDescription className="text-xs font-mono">
                        {group.output_pattern}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Badge variant="outline" className="text-xs">
                            {group.widgets_count} {t('groups.widgets')}
                          </Badge>
                          {hasIndex ? (
                            <span className="flex items-center gap-1 text-xs text-green-600">
                              <div className="h-2 w-2 rounded-full bg-green-500" />
                              {t('groups.index')}
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-xs text-muted-foreground">
                              <div className="h-2 w-2 rounded-full bg-muted-foreground/30" />
                              {t('groups.noIndex')}
                            </span>
                          )}
                        </div>
                        <Button variant="ghost" size="sm" className="h-7 text-xs">
                          {t('pages.view')}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </ScrollArea>
  )
}

// =============================================================================
// SITE PREVIEW COMPONENT
// =============================================================================

interface SitePreviewProps {
  page: StaticPage | null
  site: SiteSettings
  navigation: NavigationItem[]
  footerNavigation: FooterSection[]
  device: DeviceSize
  onDeviceChange: (device: DeviceSize) => void
  // For markdown content loaded from file
  fileContent?: string
  // Callback when a link is clicked in the preview
  onLinkClick?: (href: string) => void
  // Callback to close/hide the preview
  onClose?: () => void
}

function SitePreview({ page, site, navigation, footerNavigation, device, onDeviceChange, fileContent, onLinkClick, onClose }: SitePreviewProps) {
  const { t, i18n } = useTranslation(['site', 'common'])
  const previewMutation = useTemplatePreview()
  const [html, setHtml] = useState('')

  // Function to load preview
  const loadPreview = () => {
    if (page) {
      // Build context for template preview
      const context: Record<string, unknown> = { ...page.context }

      // If we have file content, use it as content_markdown
      if (fileContent && page.context?.content_source) {
        context.content_markdown = fileContent
        delete context.content_source // Don't load from file again
      }

      // Add title from context if present
      if (page.context?.title) {
        context.title = page.context.title
      }

      previewMutation.mutate({
        template: page.template || 'page.html',
        context,
        site: site as Record<string, unknown>,
        navigation: navigation.map(n => ({
          text: n.text,
          url: n.url,
          children: n.children,
        })),
        footer_navigation: footerNavigation.map(s => ({
          title: s.title,
          links: s.links,
        })),
        output_file: page.output_file,
        gui_lang: i18n.language?.split('-')[0] || 'fr',
      }, {
        onSuccess: (data) => setHtml(data.html),
        onError: (error) => {
          setHtml(`<div class="text-red-500 p-4">Erreur: ${error.message}</div>`)
        },
      })
    } else {
      setHtml('')
    }
  }

  // Load preview when dependencies change
  useEffect(() => {
    loadPreview()
  }, [page, site, navigation, footerNavigation, fileContent])

  return (
    <PreviewFrame
      html={html}
      isLoading={previewMutation.isPending}
      device={device}
      onDeviceChange={onDeviceChange}
      onRefresh={loadPreview}
      onClose={onClose}
      onLinkClick={onLinkClick}
      title={t('preview.title')}
      emptyMessage={t('preview.selectPageForPreview')}
    />
  )
}

// =============================================================================
// GROUP INDEX PREVIEW PANEL COMPONENT
// =============================================================================

interface GroupIndexPreviewPanelProps {
  html: string | null
  isLoading: boolean
  device: DeviceSize
  onDeviceChange: (device: DeviceSize) => void
  groupName: string
  onLinkClick?: (href: string) => void
  onRefresh?: () => void
}

function GroupIndexPreviewPanel({
  html,
  isLoading,
  device,
  onDeviceChange,
  groupName,
  onLinkClick,
  onRefresh,
}: GroupIndexPreviewPanelProps) {
  const { t } = useTranslation(['site', 'common'])

  return (
    <PreviewFrame
      html={html}
      isLoading={isLoading}
      device={device}
      onDeviceChange={onDeviceChange}
      onRefresh={onRefresh}
      onLinkClick={onLinkClick}
      title={`${t('preview.previewIndex')} - ${groupName}`}
    />
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
  // Data fetching
  const { data: siteConfig, isLoading, error, refetch } = useSiteConfig()
  const { data: groupsData, isLoading: groupsLoading } = useGroups()
  const { data: templatesData } = useTemplates()
  const updateMutation = useUpdateSiteConfig()

  // Local editing state
  const [editedSite, setEditedSite] = useState<SiteSettings>(DEFAULT_SITE_SETTINGS)
  const [editedNavigation, setEditedNavigation] = useState<NavigationItem[]>([])
  const [editedFooterNavigation, setEditedFooterNavigation] = useState<FooterSection[]>([])
  const [editedPages, setEditedPages] = useState<StaticPage[]>([])

  // Delete confirmation dialog state
  const [pageToDelete, setPageToDelete] = useState<string | null>(null)

  // UI state - initialize based on initialSection prop
  const mapSectionToSelection = (section: string): Selection | null => {
    switch (section) {
      case 'general':
      case 'identity': // backward compatibility
        return { type: 'general' }
      case 'appearance':
      case 'theme': // backward compatibility
        return { type: 'appearance' }
      case 'navigation':
        return { type: 'navigation' }
      case 'pages':
        // For pages, we don't select anything specific - just show the tree
        return null
      default:
        return { type: 'general' }
    }
  }
  const [selection, setSelection] = useState<Selection | null>(() => mapSectionToSelection(initialSection))

  // Update selection when initialSection changes (navigation between sub-menus)
  useEffect(() => {
    setSelection(mapSectionToSelection(initialSection))
  }, [initialSection])

  // Preview is available for static pages, appearance (if pages exist), and groups with index_generator
  const currentGroupForPreview = selection?.type === 'group'
    ? (groupsData?.groups ?? []).find((g) => g.name === selection.id)
    : null
  const groupHasIndex = currentGroupForPreview?.index_generator?.enabled ?? false
  const previewAvailable = selection?.type === 'page'
    || (selection?.type === 'appearance' && editedPages.length > 0)
    || (selection?.type === 'group' && groupHasIndex)
  const [previewEnabled, setPreviewEnabled] = useState(false)
  const showPreview = previewAvailable && previewEnabled
  const [previewDevice, setPreviewDevice] = useState<DeviceSize>('desktop')

  // Group index preview
  const groupIndexPreviewMutation = useGroupIndexPreview()
  const [groupIndexHtml, setGroupIndexHtml] = useState<string | null>(null)

  // Load file content for preview when content_source is used
  // For appearance preview, use the first available page
  const previewPageForAppearance = selection?.type === 'appearance' ? editedPages[0] : null
  const previewFilePath = selection?.type === 'page'
    ? editedPages.find((p) => p.name === selection.id)?.context?.content_source
    : previewPageForAppearance?.context?.content_source ?? null
  const { data: previewFileData } = useFileContent(previewFilePath)

  // Function to load/refresh group index preview
  const loadGroupIndexPreview = () => {
    if (selection?.type === 'group' && groupHasIndex && selection.id) {
      groupIndexPreviewMutation.mutate(
        { groupName: selection.id },
        {
          onSuccess: (data) => setGroupIndexHtml(data.html),
          onError: (error) => {
            setGroupIndexHtml(`<div style="padding: 20px; color: #ef4444;">Erreur: ${error.message}</div>`)
          },
        }
      )
    }
  }

  // Load group index preview when group is selected and preview is enabled
  useEffect(() => {
    if (selection?.type === 'group' && groupHasIndex && previewEnabled && selection.id) {
      loadGroupIndexPreview()
    } else if (selection?.type !== 'group') {
      setGroupIndexHtml(null)
    }
  }, [selection?.type, selection?.id, groupHasIndex, previewEnabled])

  // Groups from API (read-only)
  const groups = groupsData?.groups ?? []

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
    // Generate unique page name based on template
    const baseName = templateName.replace('.html', '')
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
      output_file: `${pageName}.html`,
      template: templateName,
    }
    setEditedPages([...editedPages, newPage])
    setSelection({ type: 'page', id: newPage.name })

    // Propose to add to navigation
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
    // Ensure unique page name
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
      output_file: `${finalName}.html`,
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
    setEditedPages((pages) =>
      pages.map((p) => (p.name === oldName ? updatedPage : p))
    )
    // Update selection if name changed
    if (oldName && updatedPage.name !== oldName) {
      setSelection({ type: 'page', id: updatedPage.name })
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

    // Calculate new state
    const newPages = editedPages.filter((p) => p.name !== pageToDelete)
    const pageUrl = `/${pageObj.output_file}`
    const newNavigation = editedNavigation.filter((item) => item.url !== pageUrl)
    const newFooterNavigation = editedFooterNavigation.map((section) => ({
      ...section,
      links: section.links.filter((link) => link.url !== pageUrl),
    }))

    // Close dialog and clear selection
    setPageToDelete(null)
    setSelection(null)

    // Update local state immediately for responsive UI
    setEditedPages(newPages)
    setEditedNavigation(newNavigation)
    setEditedFooterNavigation(newFooterNavigation)

    // Persist to backend
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
      // Revert on error
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

  // Get current page for preview
  // For appearance preview, use the first available page
  const currentPage = selection?.type === 'page'
    ? editedPages.find((p) => p.name === selection.id)
    : selection?.type === 'appearance' && editedPages.length > 0
      ? editedPages[0]
      : null

  // File content for preview (loaded separately when content_source is used)
  const previewFileContent = previewFileData?.content

  // Get current group for viewer
  const currentGroup = selection?.type === 'group'
    ? groups.find((g) => g.name === selection.id)
    : null

  // Loading state
  if (isLoading) {
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
  if (error) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {t('messages.loadError', { error: error instanceof Error ? error.message : t('common:messages.unknownError') })}
          </AlertDescription>
        </Alert>
        <Button onClick={() => refetch()} className="mt-4">
          {t('messages.retry')}
        </Button>
      </div>
    )
  }

  // Render editor based on selection
  const renderEditor = () => {
    // When no selection, show PagesOverview dashboard
    if (!selection) {
      return (
        <PagesOverview
          staticPages={editedPages}
          groups={groups}
          navigation={editedNavigation}
          footerNavigation={editedFooterNavigation}
          onSelectPage={(name) => setSelection({ type: 'page', id: name })}
          onSelectGroup={(name) => setSelection({ type: 'group', id: name })}
          onAddPage={handleAddPage}
          onDeletePage={handleDeletePage}
          onDuplicatePage={handleDuplicatePage}
          onAddToNavigation={handleAddPageToNavigation}
        />
      )
    }

    switch (selection.type) {
      case 'general':
        return (
          <ScrollArea className="h-full">
            <div className="p-6">
              <SiteConfigForm config={editedSite} onChange={setEditedSite} />
            </div>
          </ScrollArea>
        )

      case 'appearance':
        return (
          <ScrollArea className="h-full">
            <div className="p-6">
              <ThemeConfigForm config={editedSite} onChange={setEditedSite} />
            </div>
          </ScrollArea>
        )

      case 'navigation':
        return (
          <ScrollArea className="h-full">
            <div className="p-6">
              <NavigationBuilder
                items={editedNavigation}
                onChange={setEditedNavigation}
                staticPages={editedPages}
                groups={groups}
                templates={templatesData?.templates ?? []}
                onCreatePage={handleCreatePageFromNavigation}
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
                sections={editedFooterNavigation}
                onChange={setEditedFooterNavigation}
                staticPages={editedPages}
                groups={groups}
              />
            </div>
          </ScrollArea>
        )

      case 'page':
        const pageIndex = editedPages.findIndex((p) => p.name === selection.id)
        const page = pageIndex >= 0 ? editedPages[pageIndex] : null
        if (!page) {
          return (
            <div className="flex h-full items-center justify-center">
              <p className="text-muted-foreground">{t('common:messages.notFound')}</p>
            </div>
          )
        }
        return (
          <StaticPageEditor
            key={`page-${pageIndex}`} // Use index for stable key during name edits
            page={page}
            onChange={handleUpdatePage}
            onDelete={() => handleDeletePage(page.name)}
            onBack={() => setSelection(null)}
            navigation={editedNavigation}
            onUpdateNavigation={setEditedNavigation}
          />
        )

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
                onBack={() => setSelection(null)}
              />
            </div>
          </ScrollArea>
        )

      case 'new-page':
        return (
          <TemplateList
            templates={templatesData?.templates ?? []}
            onSelect={handleTemplateSelected}
            onBack={() => setSelection(null)}
          />
        )

      default:
        return null
    }
  }

  // Shared handler for link clicks in preview iframes
  const handlePreviewLinkClick = (href: string) => {
    const normalizedHref = href.replace(/^\//, '')
    const filename = normalizedHref.split('/').pop() || href

    // 1. Check if it's a group index page FIRST (e.g., "taxons/index.html")
    // This must be checked before static pages to avoid "index.html" matching root index
    const groupByIndex = groups.find(g => {
      const indexPattern = g.index_output_pattern || `${g.name}/index.html`
      return normalizedHref === indexPattern
    })
    if (groupByIndex) {
      setSelection({ type: 'group', id: groupByIndex.name })
      toast.info(t('common:messages.navigatingTo', { name: `${groupByIndex.name}/` }))
      return
    }

    // 2. Check if it's a group detail page (e.g., "taxons/123.html")
    const groupByPath = groups.find(g => {
      // Check if href starts with group name folder
      return normalizedHref.startsWith(`${g.name}/`) && normalizedHref !== `${g.name}/index.html`
    })
    if (groupByPath) {
      // Navigate to the group view - detail pages can't be previewed individually
      setSelection({ type: 'group', id: groupByPath.name })
      toast.info(t('preview.groupDetailPage', { group: groupByPath.name }), {
        description: t('preview.groupDetailPageDesc'),
      })
      return
    }

    // 3. Try to find in static pages (after group checks to avoid false matches)
    // Prioritize exact path match over filename-only match
    const targetPage = editedPages.find(p =>
      p.output_file === normalizedHref ||
      p.output_file === href
    ) || editedPages.find(p =>
      p.output_file === filename
    )
    if (targetPage) {
      setSelection({ type: 'page', id: targetPage.name })
      toast.info(t('common:messages.navigatingTo', { name: targetPage.name }))
      return
    }

    toast.warning(t('common:messages.pageNotFound', { href }))
  }

  return (
    <LanguageProvider
      languages={editedSite.languages || [editedSite.lang]}
      defaultLang={editedSite.lang}
    >
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b bg-muted/30 px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold">{editedSite.title || 'Site Builder'}</h1>
          <p className="text-xs text-muted-foreground">
            {t('description')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Preview button only shown for static pages */}
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
          {hasChanges && (
            <Button
              size="sm"
              onClick={handleSave}
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending ? (
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
      <ResizablePanelGroup direction="horizontal" className="flex-1">
        {/* Left Panel - Tree */}
        <ResizablePanel defaultSize={15} minSize={12} maxSize={25}>
          <SiteTree
            navigation={editedNavigation}
            footerNavigation={editedFooterNavigation}
            pages={editedPages}
            groups={groups}
            groupsLoading={groupsLoading}
            selection={selection}
            onSelect={setSelection}
            onAddPage={handleAddPage}
          />
        </ResizablePanel>

        <ResizableHandle withHandle />

        {/* Center Panel - Editor */}
        <ResizablePanel defaultSize={showPreview ? 45 : 85} minSize={30}>
          {renderEditor()}
        </ResizablePanel>

        {/* Right Panel - Preview (optional) */}
        {showPreview && (
          <>
            <ResizableHandle withHandle />
            <ResizablePanel defaultSize={35} minSize={20} maxSize={50}>
              {selection?.type === 'group' ? (
                <GroupIndexPreviewPanel
                  html={groupIndexHtml}
                  isLoading={groupIndexPreviewMutation.isPending}
                  device={previewDevice}
                  onDeviceChange={setPreviewDevice}
                  groupName={selection.id ?? ''}
                  onLinkClick={handlePreviewLinkClick}
                  onRefresh={loadGroupIndexPreview}
                />
              ) : (
                <SitePreview
                  page={currentPage ?? null}
                  site={editedSite}
                  navigation={editedNavigation}
                  footerNavigation={editedFooterNavigation}
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
      <AlertDialog open={!!pageToDelete} onOpenChange={(open) => !open && setPageToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t('common:dialogs.deleteConfirm', { item: pageToDelete })}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('common:dialogs.cannotUndo')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common:actions.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDeletePage}
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
