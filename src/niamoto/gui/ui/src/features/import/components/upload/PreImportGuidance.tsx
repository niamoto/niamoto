import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  CheckCircle2,
  Download,
  FileText,
  GitBranch,
  Leaf,
  ListChecks,
  Map,
  SlidersHorizontal,
  Table2,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  downloadClassObjectTemplate,
  downloadCsvTemplate,
  type CsvTemplateId,
} from './classObjectTemplate'
import { cn } from '@/lib/utils'

type AssistantSection = 'overview' | 'files' | 'checks' | 'advanced'
type PreImportGuidanceVariant = 'full' | 'compact'

interface PreImportGuidanceProps {
  variant?: PreImportGuidanceVariant
}

function FormatPill({ children }: { children: string }) {
  return (
    <span className="rounded-full bg-background/80 px-2 py-0.5 font-mono text-[11px] text-muted-foreground ring-1 ring-border">
      {children}
    </span>
  )
}

function RequiredColumn({ children }: { children: string }) {
  return (
    <code className="break-all rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
      {children}
    </code>
  )
}

function TemplateButton({
  templateId,
  label,
}: {
  templateId: CsvTemplateId
  label: string
}) {
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={() => void downloadCsvTemplate(templateId)}
      className="h-auto w-full justify-start whitespace-normal py-2 text-left"
    >
      <Download className="mr-2 h-4 w-4" />
      {label}
    </Button>
  )
}

const navigationItems = [
  {
    key: 'overview',
    icon: Leaf,
  },
  {
    key: 'files',
    icon: FileText,
  },
  {
    key: 'checks',
    icon: ListChecks,
  },
  {
    key: 'advanced',
    icon: SlidersHorizontal,
  },
] as const

const acceptedFormats = ['.csv', '.gpkg', '.geojson', '.tif', '.tiff']
const occurrenceColumns = ['id', 'id_taxonref', 'family', 'genus', 'species', 'geo_pt']
const siteColumns = ['id_plot', 'plot', 'locality', 'geo_pt']
const classObjectColumns = ['class_object', 'class_name', 'class_value']
const checkKeys = ['headers', 'identifiers', 'matchingValues', 'spatial'] as const

export function PreImportGuidance({ variant = 'full' }: PreImportGuidanceProps) {
  const { t } = useTranslation(['sources'])
  const [section, setSection] = useState<AssistantSection>('overview')
  const isCompact = variant === 'compact'
  const activeNavigationItem =
    navigationItems.find((item) => item.key === section) || navigationItems[0]
  const ActiveIcon = activeNavigationItem.icon

  const renderMainPanel = () => {
    switch (section) {
      case 'files':
        return (
          <div className="space-y-3">
            <div>
              <h4 className="text-sm font-semibold">{t('preImport.assistant.files.title')}</h4>
              <p className="mt-1 text-sm text-muted-foreground">
                {t('preImport.assistant.files.description')}
              </p>
            </div>
            <div className={cn('grid gap-3', isCompact ? 'grid-cols-1' : 'xl:grid-cols-2')}>
              <div className="rounded-md border bg-muted/30 p-3">
                <div className="flex items-start gap-2">
                  <Table2 className="mt-0.5 h-4 w-4 text-blue-600 dark:text-blue-400" />
                  <div className="min-w-0 space-y-2">
                    <div>
                      <div className="text-sm font-medium">
                        {t('preImport.assistant.files.occurrences.title')}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {t('preImport.assistant.files.occurrences.description')}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {occurrenceColumns.map((column) => (
                        <RequiredColumn key={column}>{column}</RequiredColumn>
                      ))}
                    </div>
                    <TemplateButton
                      templateId="occurrences"
                      label={t('preImport.assistant.files.occurrences.download')}
                    />
                  </div>
                </div>
              </div>
              <div className="rounded-md border bg-muted/30 p-3">
                <div className="flex items-start gap-2">
                  <Map className="mt-0.5 h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                  <div className="min-w-0 space-y-2">
                    <div>
                      <div className="text-sm font-medium">
                        {t('preImport.assistant.files.sites.title')}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {t('preImport.assistant.files.sites.description')}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {siteColumns.map((column) => (
                        <RequiredColumn key={column}>{column}</RequiredColumn>
                      ))}
                    </div>
                    <TemplateButton
                      templateId="siteReference"
                      label={t('preImport.assistant.files.sites.download')}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )
      case 'checks':
        return (
          <div className="space-y-3">
            <div>
              <h4 className="text-sm font-semibold">{t('preImport.assistant.checks.title')}</h4>
              <p className="mt-1 text-sm text-muted-foreground">
                {t('preImport.assistant.checks.description')}
              </p>
            </div>
            <div className="space-y-2">
              {checkKeys.map((key) => (
                <div
                  key={key}
                  className={cn(
                    'flex gap-3 rounded-md border bg-muted/30 p-3',
                    isCompact
                      ? 'flex-col items-start'
                      : 'items-start justify-between'
                  )}
                >
                  <div className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                    <div>
                      <div className="text-sm font-medium">
                        {t(`preImport.assistant.checks.items.${key}.title`)}
                      </div>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {t(`preImport.assistant.checks.items.${key}.description`)}
                      </p>
                    </div>
                  </div>
                  <Badge variant={key === 'spatial' ? 'outline' : 'secondary'} className="shrink-0 text-[10px]">
                    {t(`preImport.assistant.checks.items.${key}.status`)}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )
      case 'advanced':
        return (
          <div className="space-y-3">
            <div>
              <h4 className="text-sm font-semibold">{t('preImport.assistant.advanced.title')}</h4>
              <p className="mt-1 text-sm text-muted-foreground">
                {t('preImport.assistant.advanced.description')}
              </p>
            </div>
            <div className={cn('grid gap-3', isCompact ? 'grid-cols-1' : 'xl:grid-cols-2')}>
              <div className="rounded-md border bg-muted/30 p-3">
                <div className="flex items-start gap-2">
                  <GitBranch className="mt-0.5 h-4 w-4 text-primary" />
                  <div className="min-w-0">
                    <div className="text-sm font-medium">
                      {t('preImport.assistant.advanced.hierarchy.title')}
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {t('preImport.assistant.advanced.hierarchy.description')}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      <RequiredColumn>family</RequiredColumn>
                      <RequiredColumn>genus</RequiredColumn>
                      <RequiredColumn>species</RequiredColumn>
                      <RequiredColumn>locality</RequiredColumn>
                      <RequiredColumn>plot</RequiredColumn>
                    </div>
                  </div>
                </div>
              </div>
              <div className="rounded-md border bg-muted/30 p-3">
                <div className="flex items-start gap-2">
                  <FileText className="mt-0.5 h-4 w-4 text-amber-600 dark:text-amber-400" />
                  <div className="min-w-0 space-y-2">
                    <div>
                      <div className="text-sm font-medium">
                        {t('preImport.assistant.advanced.classObject.title')}
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {t('preImport.assistant.advanced.classObject.description')}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {classObjectColumns.map((column) => (
                        <RequiredColumn key={column}>{column}</RequiredColumn>
                      ))}
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => void downloadClassObjectTemplate()}
                      className="h-auto w-full justify-start whitespace-normal py-2 text-left"
                    >
                      <Download className="mr-2 h-4 w-4" />
                      {t('preImport.assistant.advanced.classObject.download')}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )
      case 'overview':
      default:
        return (
          <div className="space-y-3">
            <div className="rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="flex items-start gap-2">
                <Leaf className="mt-0.5 h-4 w-4 text-emerald-700 dark:text-emerald-300" />
                <div>
                  <h4 className="text-sm font-semibold">{t('preImport.assistant.overview.title')}</h4>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {t('preImport.assistant.overview.description')}
                  </p>
                </div>
              </div>
            </div>
            <div className={cn('grid gap-2', isCompact ? 'grid-cols-1' : 'sm:grid-cols-3')}>
              {['read', 'derive', 'review'].map((key) => (
                <div key={key} className="rounded-md border bg-muted/30 p-3">
                  <div className="text-sm font-medium">
                    {t(`preImport.assistant.overview.steps.${key}.title`)}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t(`preImport.assistant.overview.steps.${key}.description`)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )
    }
  }

  return (
    <div
      className={cn(
        'min-w-0 max-w-full overflow-hidden',
        isCompact ? 'space-y-3' : 'rounded-lg border bg-muted/20 p-3 sm:p-4'
      )}
    >
      <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold">{t('preImport.title')}</h3>
            <Badge variant="secondary" className="text-[11px]">
              {t('preImport.badge')}
            </Badge>
          </div>
          <p className={cn('text-muted-foreground', isCompact ? 'text-xs' : 'max-w-3xl text-sm')}>
            {t('preImport.description')}
          </p>
        </div>
      </div>

      <div className={cn('mt-3 grid min-w-0 gap-3', isCompact ? 'grid-cols-1' : 'xl:grid-cols-[210px_minmax(0,1fr)_220px]')}>
        <div className="min-w-0 rounded-md border bg-background/75 p-2">
          <div className={cn(isCompact ? 'grid grid-cols-2 gap-1.5' : 'space-y-1')}>
            {navigationItems.map((item) => {
              const Icon = item.icon
              const isSelected = item.key === section

              return (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => setSection(item.key)}
                  className={`flex w-full items-start gap-2 rounded-md px-2 py-2 text-left transition-colors ${
                    isSelected
                      ? 'bg-primary/10 text-foreground ring-1 ring-primary/20'
                      : 'text-muted-foreground hover:bg-muted/70 hover:text-foreground'
                  }`}
                  aria-pressed={isSelected}
                >
                  <Icon className="mt-0.5 h-4 w-4 shrink-0" />
                  <span className="min-w-0">
                    <span className="block text-sm font-medium">
                      {t(`preImport.assistant.nav.${item.key}.title`)}
                    </span>
                    <span className={cn('mt-0.5 text-[11px]', isCompact ? 'hidden' : 'block')}>
                      {t(`preImport.assistant.nav.${item.key}.description`)}
                    </span>
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        <div className="min-w-0 rounded-md border bg-background/75 p-3">
          <div className="mb-3 flex min-w-0 items-center gap-2 border-b pb-3">
            <ActiveIcon className="h-4 w-4 text-primary" />
            <div className="min-w-0">
              <div className="text-sm font-semibold">
                {t(`preImport.assistant.nav.${section}.title`)}
              </div>
              <div className={cn('text-xs text-muted-foreground', isCompact && 'hidden')}>
                {t(`preImport.assistant.nav.${section}.description`)}
              </div>
            </div>
          </div>
          {renderMainPanel()}
        </div>

        {isCompact ? (
          <aside className="min-w-0 rounded-md border bg-background/75 p-3">
            <div className="text-xs font-medium text-muted-foreground">
              {t('preImport.acceptedFormatsTitle')}
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {acceptedFormats.map((format) => (
                <FormatPill key={format}>{format}</FormatPill>
              ))}
            </div>
          </aside>
        ) : (
          <aside className="min-w-0 rounded-md border bg-background/75 p-3">
            <div className="text-sm font-medium">{t('preImport.assistant.resources.title')}</div>
            <p className="mt-1 text-xs text-muted-foreground">
              {t('preImport.assistant.resources.description')}
            </p>
            <div className="mt-3 grid gap-2">
              <TemplateButton
                templateId="occurrences"
                label={t('preImport.assistant.files.occurrences.download')}
              />
              <TemplateButton
                templateId="siteReference"
                label={t('preImport.assistant.files.sites.download')}
              />
            </div>
            <div className="my-3 border-t" />
            <div className="text-xs font-medium text-muted-foreground">
              {t('preImport.acceptedFormatsTitle')}
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {acceptedFormats.map((format) => (
                <FormatPill key={format}>{format}</FormatPill>
              ))}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {t('preImport.shapefileNote')}
            </p>
          </aside>
        )}
      </div>
    </div>
  )
}
