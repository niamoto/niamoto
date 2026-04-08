/**
 * PagesOverview - Dashboard view showing all static pages and collections
 * Displayed when no selection is active in SiteBuilder.
 */

import { useTranslation } from 'react-i18next'
import {
  FileText,
  Folder,
  Plus,
  MoreHorizontal,
  Trash2,
  Copy,
  Link2,
  Home,
  BookOpen,
  Users,
  Mail,
  Download,
  List,
  Newspaper,
  ScrollText,
  Eye,
  type LucideIcon,
} from 'lucide-react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type {
  NavigationItem,
  FooterSection,
  StaticPage,
  GroupInfo,
} from '@/shared/hooks/useSiteConfig'

// =============================================================================
// TEMPLATE ICONS CONFIGURATION
// =============================================================================

export const TEMPLATE_ICONS: Record<string, LucideIcon> = {
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

export function getTemplateIcon(template?: string): LucideIcon {
  return template ? TEMPLATE_ICONS[template] || FileText : FileText
}

// Check if a page is linked in navigation (recursive for submenus)
export function isPageInNavigation(pageUrl: string, items: NavigationItem[]): 'direct' | 'parent' | null {
  for (const item of items) {
    if (item.url === pageUrl) return 'direct'
    if (item.children && item.children.length > 0) {
      if (!item.url && item.children.some(child => child.url === pageUrl)) {
        return 'parent'
      }
      const childResult = isPageInNavigation(pageUrl, item.children)
      if (childResult) return childResult
    }
  }
  return null
}

// =============================================================================
// PAGES OVERVIEW COMPONENT
// =============================================================================

export interface PagesOverviewProps {
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
  onPreview?: () => void
}

export function PagesOverview({
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
  onPreview,
}: PagesOverviewProps) {
  const { t } = useTranslation(['site', 'common'])

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
          <div className="flex items-center gap-2">
            {onPreview && (
              <Button variant="outline" onClick={onPreview}>
                <Eye className="h-4 w-4 mr-2" />
                {t('preview.title')}
              </Button>
            )}
            <Button onClick={onAddPage}>
              <Plus className="h-4 w-4 mr-2" />
              {t('pages.newPage')}
            </Button>
          </div>
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
              <h3 className="font-medium">{t('collections.title')}</h3>
              <Badge variant="secondary" className="text-xs">
                {groups.length}
              </Badge>
            </div>
          </div>

          {groups.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="flex flex-col items-center justify-center py-8">
                <Folder className="h-10 w-10 text-muted-foreground/50 mb-3" />
                <p className="text-sm text-muted-foreground">
                  {t('collections.noCollectionsConfigured')}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {t('collections.collectionsDefinedInExport')}
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
                            {group.widgets_count} {t('collections.widgets')}
                          </Badge>
                          {hasIndex ? (
                            <span className="flex items-center gap-1 text-xs text-green-600">
                              <div className="h-2 w-2 rounded-full bg-green-500" />
                              {t('collections.index')}
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-xs text-muted-foreground">
                              <div className="h-2 w-2 rounded-full bg-muted-foreground/30" />
                              {t('collections.noIndex')}
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
