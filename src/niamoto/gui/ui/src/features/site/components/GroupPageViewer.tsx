/**
 * GroupPageViewer - View and edit a group configuration from the Site Builder
 *
 * Displays:
 * - Group name and output patterns
 * - Menu links pointing to the collection
 * - Index generator summary and editorial labels
 */

import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Folder,
  LayoutGrid,
  Filter,
  List,
  Eye,
  Settings2,
  Loader2,
  Menu,
  Plus,
  X,
  Save,
  RotateCcw,
  Link2,
  BadgeCheck,
} from 'lucide-react'
import { toast } from 'sonner'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { LocalizedInput, type LocalizedString } from '@/components/ui/localized-input'
import { resolveLocalizedString } from '@/components/ui/localized-string'
import { useLanguages } from '@/shared/contexts/useLanguages'
import { useUpdateGroupIndexConfig, type GroupIndexConfig, type GroupInfo } from '@/shared/hooks/useSiteConfig'

interface MenuRef {
  id: string
  label: LocalizedString
}

interface GroupPageViewerProps {
  group: GroupInfo
  onBack: () => void
  onEnableIndexPage?: () => void
  isEnablingIndexPage?: boolean
  menuRefs?: MenuRef[]
  onUpdateMenuLabel?: (itemId: string, label: LocalizedString) => void
  onRemoveMenuItem?: (itemId: string) => void
  onAddToMenu?: () => void
}

function cloneIndexConfig(config: GroupIndexConfig): GroupIndexConfig {
  return JSON.parse(JSON.stringify(config)) as GroupIndexConfig
}

function humanizeFieldName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, letter => letter.toUpperCase())
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
  const { t, i18n } = useTranslation(['site', 'common'])
  const { defaultLang } = useLanguages()
  const updateGroupIndexMutation = useUpdateGroupIndexConfig()
  const hasIndex = group.index_generator?.enabled
  const indexConfig = group.index_generator
  const [draftIndexConfig, setDraftIndexConfig] = useState<GroupIndexConfig | null>(
    indexConfig ? cloneIndexConfig(indexConfig) : null
  )

  const editableIndexConfig = draftIndexConfig ?? indexConfig ?? null

  const isIndexDirty = useMemo(
    () => JSON.stringify(draftIndexConfig ?? null) !== JSON.stringify(indexConfig ?? null),
    [draftIndexConfig, indexConfig]
  )

  const resolveLabel = (value: LocalizedString | undefined, fallback = '') =>
    resolveLocalizedString(value, i18n.language, defaultLang) || fallback

  const updatePageConfig = (updates: Partial<GroupIndexConfig['page_config']>) => {
    setDraftIndexConfig(prev =>
      prev
        ? {
            ...prev,
            page_config: {
              ...prev.page_config,
              ...updates,
            },
          }
        : prev
    )
  }

  const updateDisplayField = (
    fieldIndex: number,
    updates: Partial<GroupIndexConfig['display_fields'][number]>
  ) => {
    setDraftIndexConfig(prev =>
      prev
        ? {
            ...prev,
            display_fields: prev.display_fields.map((field, index) =>
              index === fieldIndex ? { ...field, ...updates } : field
            ),
          }
        : prev
    )
  }

  const handleResetIndexConfig = () => {
    setDraftIndexConfig(indexConfig ? cloneIndexConfig(indexConfig) : null)
  }

  const handleSaveIndexConfig = async () => {
    if (!draftIndexConfig) return

    try {
      await updateGroupIndexMutation.mutateAsync({
        groupName: group.name,
        config: draftIndexConfig,
      })
      toast.success(t('collectionViewer.indexLabelsSaved'), {
        description: t('collectionViewer.indexLabelsSavedDesc'),
      })
    } catch (error) {
      toast.error(t('common:status.error'), {
        description:
          error instanceof Error ? error.message : t('messages.saveFailed'),
      })
    }
  }

  return (
    <div className="space-y-4">
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
                      onChange={(value) => onUpdateMenuLabel?.(ref.id, value ?? '')}
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

      {hasIndex && editableIndexConfig && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <LayoutGrid className="h-4 w-4" />
                  <CardTitle className="text-sm">{t('collectionViewer.indexGenerator')}</CardTitle>
                </div>
                <CardDescription className="mt-2">
                  {t('collectionViewer.indexPageDesc')}
                </CardDescription>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="default" className="bg-green-500/10 text-green-600">
                  {t('collectionViewer.enabled')}
                </Badge>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleResetIndexConfig}
                  disabled={!isIndexDirty || updateGroupIndexMutation.isPending}
                >
                  <RotateCcw className="mr-2 h-4 w-4" />
                  {t('collectionViewer.resetLabels')}
                </Button>
                <Button
                  size="sm"
                  onClick={handleSaveIndexConfig}
                  disabled={!isIndexDirty || updateGroupIndexMutation.isPending}
                >
                  {updateGroupIndexMutation.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 h-4 w-4" />
                  )}
                  {updateGroupIndexMutation.isPending
                    ? t('collectionViewer.savingLabels')
                    : t('collectionViewer.saveLabels')}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-4">
              <LocalizedInput
                label={t('collectionViewer.titleLabel')}
                value={editableIndexConfig.page_config?.title}
                onChange={(value) => updatePageConfig({ title: value || group.name })}
                placeholder={group.name}
              />
              <LocalizedInput
                label={t('collectionViewer.descriptionLabel')}
                value={editableIndexConfig.page_config?.description}
                onChange={(value) => updatePageConfig({ description: value || undefined })}
                placeholder={t('collectionViewer.descriptionPlaceholder')}
                multiline
                rows={2}
              />
              <div className="grid gap-3 text-sm md:grid-cols-2">
                <div className="flex items-center justify-between rounded-md border px-3 py-2">
                  <span className="text-muted-foreground">{t('collectionViewer.itemsPerPage')}</span>
                  <Badge variant="outline">{editableIndexConfig.page_config?.items_per_page || 24}</Badge>
                </div>
                <div className="flex items-center justify-between rounded-md border px-3 py-2">
                  <span className="text-muted-foreground">{t('collectionViewer.template')}</span>
                  <code className="rounded bg-muted px-2 py-0.5 text-xs font-mono">
                    {editableIndexConfig.template}
                  </code>
                </div>
              </div>
            </div>

            <Separator />

            <div>
              <div className="mb-2 flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{t('collectionViewer.filters')}</span>
                <Badge variant="secondary" className="text-xs">
                  {editableIndexConfig.filters?.length || 0}
                </Badge>
              </div>
              {editableIndexConfig.filters && editableIndexConfig.filters.length > 0 ? (
                <div className="space-y-1.5">
                  {editableIndexConfig.filters.map((filter, index) => (
                    <div
                      key={`${filter.field}-${index}`}
                      className="flex items-center gap-2 rounded-md bg-muted/50 px-2 py-1.5 text-xs"
                    >
                      <code className="text-muted-foreground">{filter.field}</code>
                      <span className="text-muted-foreground">{filter.operator}</span>
                      <div className="flex flex-wrap gap-1">
                        {filter.values?.slice(0, 3).map((value, valueIndex) => (
                          <Badge key={valueIndex} variant="outline" className="text-[10px]">
                            {String(value)}
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
                <p className="text-xs italic text-muted-foreground">{t('collectionViewer.noFilter')}</p>
              )}
            </div>

            <Separator />

            <div>
              <div className="mb-2 flex items-center gap-2">
                <List className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{t('collectionViewer.displayFields')}</span>
                <Badge variant="secondary" className="text-xs">
                  {editableIndexConfig.display_fields?.length || 0}
                </Badge>
              </div>
              {editableIndexConfig.display_fields && editableIndexConfig.display_fields.length > 0 ? (
                <Accordion type="multiple" className="space-y-2">
                  {editableIndexConfig.display_fields.map((field, index) => {
                    const resolvedFieldLabel = resolveLabel(
                      field.label,
                      humanizeFieldName(field.name) || field.name
                    )

                    return (
                      <AccordionItem
                        key={`${field.name}-${index}`}
                        value={`${field.name}-${index}`}
                        className="rounded-lg border"
                      >
                        <AccordionTrigger className="px-4 py-3 hover:no-underline">
                          <div className="min-w-0 flex-1 text-left">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="truncate font-medium">{resolvedFieldLabel}</span>
                              <Badge variant="outline" className="text-[10px]">
                                {field.name}
                              </Badge>
                              <Badge variant="secondary" className="text-[10px]">
                                {field.type}
                              </Badge>
                              {field.searchable && (
                                <Badge variant="outline" className="text-[10px]">
                                  {t('collectionViewer.search')}
                                </Badge>
                              )}
                              {field.display === 'link' && (
                                <Badge variant="outline" className="text-[10px]">
                                  <Link2 className="mr-1 h-3 w-3" />
                                  {t('collectionViewer.linkMode')}
                                </Badge>
                              )}
                              {field.type === 'boolean' && (
                                <Badge variant="outline" className="text-[10px]">
                                  <BadgeCheck className="mr-1 h-3 w-3" />
                                  {t('collectionViewer.badgeLabels')}
                                </Badge>
                              )}
                            </div>
                            <p className="mt-1 truncate font-mono text-xs text-muted-foreground">
                              {field.source}
                            </p>
                          </div>
                        </AccordionTrigger>
                        <AccordionContent className="space-y-4 px-4 pb-4">
                          <LocalizedInput
                            label={t('collectionViewer.fieldLabel')}
                            value={field.label}
                            onChange={(value) =>
                              updateDisplayField(index, { label: value || undefined })
                            }
                            placeholder={humanizeFieldName(field.name)}
                          />

                          {field.display === 'link' && (
                            <div className="grid gap-4 md:grid-cols-2">
                              <LocalizedInput
                                label={t('collectionViewer.linkLabel')}
                                value={field.link_label}
                                onChange={(value) =>
                                  updateDisplayField(index, { link_label: value || undefined })
                                }
                                placeholder={resolvedFieldLabel}
                              />
                              <LocalizedInput
                                label={t('collectionViewer.linkTitle')}
                                value={field.link_title}
                                onChange={(value) =>
                                  updateDisplayField(index, { link_title: value || undefined })
                                }
                                placeholder={t('collectionViewer.linkTitlePlaceholder', {
                                  label: resolvedFieldLabel,
                                })}
                              />
                            </div>
                          )}

                          {field.type === 'boolean' && (
                            <div className="grid gap-4 md:grid-cols-2">
                              <LocalizedInput
                                label={t('collectionViewer.trueLabel')}
                                value={field.true_label}
                                onChange={(value) =>
                                  updateDisplayField(index, { true_label: value || undefined })
                                }
                                placeholder={t('collectionViewer.booleanTrueDefault')}
                              />
                              <LocalizedInput
                                label={t('collectionViewer.falseLabel')}
                                value={field.false_label}
                                onChange={(value) =>
                                  updateDisplayField(index, { false_label: value || undefined })
                                }
                                placeholder={t('collectionViewer.booleanFalseDefault')}
                              />
                            </div>
                          )}
                        </AccordionContent>
                      </AccordionItem>
                    )
                  })}
                </Accordion>
              ) : (
                <p className="text-xs italic text-muted-foreground">{t('collectionViewer.noField')}</p>
              )}
            </div>

            <Separator />

            <div>
              <div className="mb-2 flex items-center gap-2">
                <Eye className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{t('collectionViewer.displayModes')}</span>
              </div>
              <div className="flex gap-2">
                {editableIndexConfig.views?.map((view, index) => (
                  <Badge
                    key={`${view.type}-${index}`}
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
