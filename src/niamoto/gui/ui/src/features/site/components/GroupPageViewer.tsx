/**
 * GroupPageViewer - Read-only view of a group configuration
 *
 * Displays:
 * - Group name and output patterns
 * - Index generator configuration (if enabled)
 * - Widget count
 * - Group summary and index configuration status
 */

import { useTranslation } from 'react-i18next'
import { Folder, LayoutGrid, Filter, List, Eye, Settings2, Loader2, Menu, Plus, X } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { LocalizedInput, type LocalizedString } from '@/components/ui/localized-input'
import type { GroupInfo } from '@/shared/hooks/useSiteConfig'

interface MenuRef {
  id: string
  label: LocalizedString
}

interface GroupPageViewerProps {
  group: GroupInfo
  onBack: () => void
  onEnableIndexPage?: () => void
  isEnablingIndexPage?: boolean
  // Menu linking
  menuRefs?: MenuRef[]
  onUpdateMenuLabel?: (itemId: string, label: LocalizedString) => void
  onRemoveMenuItem?: (itemId: string) => void
  onAddToMenu?: () => void
}

export function GroupPageViewer({
  group,
  onBack,
  onEnableIndexPage,
  isEnablingIndexPage = false,
  menuRefs = [],
  onUpdateMenuLabel,
  onRemoveMenuItem,
  onAddToMenu,
}: GroupPageViewerProps) {
  const { t } = useTranslation(['site', 'common'])
  const hasIndex = group.index_generator?.enabled
  const indexConfig = group.index_generator

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10">
            <Folder className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">{group.name}/</h2>
            <p className="text-sm text-muted-foreground">{t('collectionViewer.pageCollection')}</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={onBack}>
          {t('collectionViewer.back')}
        </Button>
      </div>

      {/* Output patterns */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Settings2 className="h-4 w-4" />
            {t('collectionViewer.configuration')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">{t('collectionViewer.outputPattern')}</span>
              <code className="rounded bg-muted px-2 py-0.5 text-xs font-mono">
                {group.output_pattern}
              </code>
            </div>
            {group.index_output_pattern && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">{t('collectionViewer.indexPage')}</span>
                <code className="rounded bg-muted px-2 py-0.5 text-xs font-mono">
                  {group.index_output_pattern}
                </code>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">{t('collectionViewer.configuredWidgets')}</span>
              <Badge variant="secondary">{group.widgets_count}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Menu linking (only for collections with index) */}
      {hasIndex && (onAddToMenu || menuRefs.length > 0) && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Menu className="h-4 w-4" />
              {t('navigation.menuLinks')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {menuRefs.length > 0 ? (
              <div className="space-y-2">
                {menuRefs.map(ref => (
                  <div key={ref.id} className="flex items-center gap-2">
                    <LocalizedInput
                      value={ref.label}
                      onChange={(val) => onUpdateMenuLabel?.(ref.id, val ?? '')}
                      placeholder={group.name}
                      className="flex-1"
                    />
                    {onRemoveMenuItem && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 shrink-0 hover:bg-destructive/10"
                        onClick={() => onRemoveMenuItem(ref.id)}
                      >
                        <X className="h-3.5 w-3.5 text-muted-foreground hover:text-destructive" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            ) : onAddToMenu ? (
              <Button
                variant="outline"
                size="sm"
                className="h-8 gap-1"
                onClick={onAddToMenu}
              >
                <Plus className="h-3 w-3" />
                {t('navigation.addToMainMenu')}
              </Button>
            ) : null}
          </CardContent>
        </Card>
      )}

      {/* Index generator */}
      {hasIndex && indexConfig && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-sm">
                <LayoutGrid className="h-4 w-4" />
                {t('collectionViewer.indexGenerator')}
              </CardTitle>
              <Badge variant="default" className="bg-green-500/10 text-green-600">
                {t('collectionViewer.enabled')}
              </Badge>
            </div>
            <CardDescription>
              {t('collectionViewer.indexPageDesc')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Page config */}
            <div className="grid gap-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">{t('collectionViewer.titleLabel')}</span>
                <span>{indexConfig.page_config?.title || '-'}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">{t('collectionViewer.itemsPerPage')}</span>
                <Badge variant="outline">{indexConfig.page_config?.items_per_page || 24}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">{t('collectionViewer.template')}</span>
                <code className="rounded bg-muted px-2 py-0.5 text-xs font-mono">
                  {indexConfig.template}
                </code>
              </div>
            </div>

            <Separator />

            {/* Filters */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{t('collectionViewer.filters')}</span>
                <Badge variant="secondary" className="text-xs">
                  {indexConfig.filters?.length || 0}
                </Badge>
              </div>
              {indexConfig.filters && indexConfig.filters.length > 0 ? (
                <div className="space-y-1.5">
                  {indexConfig.filters.map((filter, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 rounded-md bg-muted/50 px-2 py-1.5 text-xs"
                    >
                      <code className="text-muted-foreground">{filter.field}</code>
                      <span className="text-muted-foreground">{filter.operator}</span>
                      <div className="flex flex-wrap gap-1">
                        {filter.values?.slice(0, 3).map((v, i) => (
                          <Badge key={i} variant="outline" className="text-[10px]">
                            {String(v)}
                          </Badge>
                        ))}
                        {filter.values?.length > 3 && (
                          <Badge variant="outline" className="text-[10px]">
                            +{filter.values.length - 3}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground italic">{t('collectionViewer.noFilter')}</p>
              )}
            </div>

            <Separator />

            {/* Display fields */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <List className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{t('collectionViewer.displayFields')}</span>
                <Badge variant="secondary" className="text-xs">
                  {indexConfig.display_fields?.length || 0}
                </Badge>
              </div>
              {indexConfig.display_fields && indexConfig.display_fields.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {indexConfig.display_fields.map((field, idx) => (
                    <Badge
                      key={idx}
                      variant="outline"
                      className={field.searchable ? 'border-blue-200 bg-blue-50' : ''}
                    >
                      {field.label || field.name}
                      {field.searchable && (
                        <span className="ml-1 text-[10px] text-blue-500">{t('collectionViewer.search')}</span>
                      )}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground italic">{t('collectionViewer.noField')}</p>
              )}
            </div>

            <Separator />

            {/* Views */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <Eye className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{t('collectionViewer.displayModes')}</span>
              </div>
              <div className="flex gap-2">
                {indexConfig.views?.map((view, idx) => (
                  <Badge
                    key={idx}
                    variant={view.default ? 'default' : 'outline'}
                    className="capitalize"
                  >
                    {view.type}
                    {view.default && <span className="ml-1 text-[10px]">({t('collectionViewer.default')})</span>}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* No index generator */}
      {!hasIndex && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8 text-center">
            <LayoutGrid className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <h3 className="font-medium">{t('collectionViewer.noIndexPage')}</h3>
            <p className="mt-1 max-w-md text-sm text-muted-foreground">
              {t('collectionViewer.noIndexPageDesc')}
            </p>
            {onEnableIndexPage && (
              <Button
                className="mt-4"
                onClick={onEnableIndexPage}
                disabled={isEnablingIndexPage}
              >
                {isEnablingIndexPage ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('collectionViewer.activating')}
                  </>
                ) : (
                  t('collectionViewer.activatePage')
                )}
              </Button>
            )}
          </CardContent>
        </Card>
      )}

    </div>
  )
}
