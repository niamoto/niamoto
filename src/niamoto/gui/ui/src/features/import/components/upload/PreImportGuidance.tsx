import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  CheckCircle2,
  ChevronDown,
  Download,
  FileText,
  GitBranch,
  Globe,
  Map,
  Table2,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  downloadClassObjectTemplate,
  downloadCsvTemplate,
  type CsvTemplateId,
} from './classObjectTemplate'

function FormatPill({ children }: { children: string }) {
  return (
    <span className="rounded-full bg-background/80 px-2 py-0.5 font-mono text-[11px] text-muted-foreground ring-1 ring-border">
      {children}
    </span>
  )
}

function RequiredColumn({ children }: { children: string }) {
  return (
    <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
      {children}
    </code>
  )
}

const supportedFormats = [
  {
    key: 'csv',
    icon: Table2,
    formats: ['.csv'],
    tone: 'text-blue-600 dark:text-blue-400',
  },
  {
    key: 'vector',
    icon: Map,
    formats: ['.gpkg', '.geojson'],
    tone: 'text-emerald-600 dark:text-emerald-400',
  },
  {
    key: 'raster',
    icon: Globe,
    formats: ['.tif', '.tiff'],
    tone: 'text-violet-600 dark:text-violet-400',
  },
] as const

const detectionTipKeys = ['headers', 'identifiers', 'matchingValues', 'spatial'] as const
const csvTemplateIds: CsvTemplateId[] = [
  'occurrences',
  'siteReference',
]

export function PreImportGuidance() {
  const { t } = useTranslation(['sources'])
  const [hierarchyOpen, setHierarchyOpen] = useState(false)
  const [classObjectOpen, setClassObjectOpen] = useState(false)

  return (
    <div className="rounded-lg border bg-muted/20 p-3 sm:p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold">{t('preImport.title')}</h3>
            <Badge variant="secondary" className="text-[11px]">
              {t('preImport.badge')}
            </Badge>
          </div>
          <p className="max-w-3xl text-sm text-muted-foreground">
            {t('preImport.description')}
          </p>
        </div>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        {supportedFormats.map((item) => {
          const Icon = item.icon

          return (
            <div key={item.key} className="rounded-md border bg-background/70 p-3">
              <div className="flex items-start gap-2">
                <Icon className={`mt-0.5 h-4 w-4 ${item.tone}`} />
                <div className="min-w-0 space-y-1">
                  <div className="text-sm font-medium">
                    {t(`preImport.formats.${item.key}.title`)}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {t(`preImport.formats.${item.key}.description`)}
                  </p>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {item.formats.map((format) => (
                      <FormatPill key={format}>{format}</FormatPill>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        {t('preImport.shapefileNote')}
      </p>

      <div className="mt-3 rounded-md border bg-background/75 p-3">
        <div className="text-sm font-medium">{t('preImport.detectionTips.title')}</div>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {detectionTipKeys.map((key) => (
            <div key={key} className="flex items-start gap-2 text-sm">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
              <span className="text-muted-foreground">
                {t(`preImport.detectionTips.items.${key}`)}
              </span>
            </div>
          ))}
        </div>
      </div>

      <Collapsible
        open={hierarchyOpen}
        onOpenChange={setHierarchyOpen}
        className="mt-3 rounded-md border bg-background/75"
      >
        <CollapsibleTrigger className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left hover:bg-accent/50">
          <div className="flex min-w-0 items-start gap-2">
            <GitBranch className="mt-0.5 h-4 w-4 text-primary" />
            <div className="min-w-0">
              <div className="text-sm font-medium">{t('preImport.hierarchy.title')}</div>
              <div className="text-xs text-muted-foreground">
                {t('preImport.hierarchy.summary')}
              </div>
            </div>
          </div>
          <ChevronDown
            className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${
              hierarchyOpen ? 'rotate-180' : ''
            }`}
          />
        </CollapsibleTrigger>

        <CollapsibleContent className="border-t px-3 py-3">
          <div className="space-y-3 text-sm">
            <div className="rounded-md bg-muted/50 p-3">
              <div className="font-medium">{t('preImport.hierarchy.meaningTitle')}</div>
              <p className="mt-1 text-muted-foreground">
                {t('preImport.hierarchy.meaningDescription')}
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-muted-foreground">
                <RequiredColumn>family</RequiredColumn>
                <span>-&gt;</span>
                <RequiredColumn>genus</RequiredColumn>
                <span>-&gt;</span>
                <RequiredColumn>species</RequiredColumn>
                <span className="mx-1">/</span>
                <RequiredColumn>country</RequiredColumn>
                <span>-&gt;</span>
                <RequiredColumn>region</RequiredColumn>
                <span>-&gt;</span>
                <RequiredColumn>locality</RequiredColumn>
                <span>-&gt;</span>
                <RequiredColumn>plot</RequiredColumn>
              </div>
            </div>
            <div className="rounded-md border border-primary/20 bg-primary/5 p-3">
              <div className="font-medium">{t('preImport.hierarchy.standardTaxonomyTitle')}</div>
              <p className="mt-1 text-muted-foreground">
                {t('preImport.hierarchy.standardTaxonomyDescription')}
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <div>
                  <div className="font-medium">{t('preImport.hierarchy.separateColumns')}</div>
                  <p className="mt-1 text-muted-foreground">
                    {t('preImport.hierarchy.separateColumnsDescription')}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <div>
                  <div className="font-medium">{t('preImport.hierarchy.clearNames')}</div>
                  <p className="mt-1 text-muted-foreground">
                    {t('preImport.hierarchy.clearNamesDescription')}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <div>
                  <div className="font-medium">{t('preImport.hierarchy.order')}</div>
                  <p className="mt-1 text-muted-foreground">
                    {t('preImport.hierarchy.orderDescription')}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <div>
                  <div className="font-medium">{t('preImport.hierarchy.identifier')}</div>
                  <p className="mt-1 text-muted-foreground">
                    {t('preImport.hierarchy.identifierDescription')}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>

      <Collapsible
        open={classObjectOpen}
        onOpenChange={setClassObjectOpen}
        className="mt-3 rounded-md border bg-background/75"
      >
        <CollapsibleTrigger className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left hover:bg-accent/50">
          <div className="flex min-w-0 items-start gap-2">
            <FileText className="mt-0.5 h-4 w-4 text-primary" />
            <div className="min-w-0">
              <div className="text-sm font-medium">{t('preImport.classObject.title')}</div>
              <div className="text-xs text-muted-foreground">
                {t('preImport.classObject.summary')}
              </div>
            </div>
          </div>
          <ChevronDown
            className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${
              classObjectOpen ? 'rotate-180' : ''
            }`}
          />
        </CollapsibleTrigger>

        <CollapsibleContent className="border-t px-3 py-3">
          <div className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-start">
            <div className="space-y-3 text-sm">
              <div className="rounded-md bg-muted/50 p-3">
                <div className="font-medium">{t('preImport.classObject.meaningTitle')}</div>
                <p className="mt-1 text-muted-foreground">
                  {t('preImport.classObject.meaningDescription')}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {t('preImport.classObject.example')}
                </p>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <div>
                  <div className="font-medium">{t('preImport.classObject.requiredColumns')}</div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    <RequiredColumn>class_object</RequiredColumn>
                    <RequiredColumn>class_name</RequiredColumn>
                    <RequiredColumn>class_value</RequiredColumn>
                  </div>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <div>
                  <div className="font-medium">{t('preImport.classObject.identifier')}</div>
                  <p className="mt-1 text-muted-foreground">
                    {t('preImport.classObject.identifierDescription')}
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                <div>
                  <div className="font-medium">{t('preImport.classObject.numericValues')}</div>
                  <p className="mt-1 text-muted-foreground">
                    {t('preImport.classObject.numericValuesDescription')}
                  </p>
                </div>
              </div>
            </div>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void downloadClassObjectTemplate()}
              className="justify-self-start lg:justify-self-end"
            >
              <Download className="mr-2 h-4 w-4" />
              {t('preImport.classObject.downloadTemplate')}
            </Button>
          </div>
        </CollapsibleContent>
      </Collapsible>

      <div className="mt-3 rounded-md border bg-background/75 p-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-medium">{t('preImport.templates.title')}</div>
            <p className="text-xs text-muted-foreground">
              {t('preImport.templates.description')}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {csvTemplateIds.map((templateId) => (
              <Button
                key={templateId}
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void downloadCsvTemplate(templateId)}
              >
                <Download className="mr-2 h-4 w-4" />
                {t(`preImport.templates.${templateId}`)}
              </Button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
