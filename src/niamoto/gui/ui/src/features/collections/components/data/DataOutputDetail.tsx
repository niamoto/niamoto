import { useMemo, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, FileBadge2, FileJson, History, Pencil } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ExportCard } from '@/features/collections/components/api/ExportCard'
import { ProfileCompatibilityPanel } from '@/features/collections/components/standards/ProfileCompatibilityPanel'
import { ProfileEditor } from '@/features/collections/components/standards/ProfileEditor'
import { ProfileOutputsPanel } from '@/features/collections/components/standards/ProfileOutputsPanel'
import { ProfileValidationReport } from '@/features/collections/components/standards/ProfileValidationReport'
import { useCollectionsCatalog } from '@/features/collections/hooks/useCollectionsCatalog'
import type { ApiExportTargetSummary } from '@/features/collections/hooks/useApiExportConfigs'
import type { CollectionDataConfiguredOutput } from '@/features/collections/hooks/useCollectionDataOptions'
import {
  useStandardProfileCompatibility,
  useStandardProfiles,
  useStandardProfileValidation,
} from '@/features/collections/hooks/useStandardProfiles'
import {
  configuredOutputSummary,
  outputStatusLabel,
  standardOutputLabel,
} from './dataOutputLabels'

interface DataOutputDetailProps {
  collectionName: string
  output: CollectionDataConfiguredOutput
}

export function DataOutputDetail({
  collectionName,
  output,
}: DataOutputDetailProps) {
  if (output.kind === 'api_json') {
    return <ApiOutputDetail collectionName={collectionName} output={output} />
  }

  if (output.kind === 'standard_profile') {
    return <StandardProfileOutputDetail collectionName={collectionName} output={output} />
  }

  return <LegacyOutputDetail output={output} />
}

function ApiOutputDetail({
  collectionName,
  output,
}: DataOutputDetailProps) {
  const { t } = useTranslation(['sources'])
  const exportTarget = useMemo<ApiExportTargetSummary>(
    () => ({
      name: output.name,
      enabled: output.enabled,
      exporter: 'json_api_exporter',
      group_names: [collectionName],
      groups: [{ group_by: collectionName, enabled: output.enabled }],
      params: {},
    }),
    [collectionName, output.enabled, output.name],
  )

  return (
    <div className="space-y-4">
      <DetailHeader
        icon={<FileJson className="h-4 w-4 text-muted-foreground" />}
        title={output.label}
        subtitle={configuredOutputSummary(output, t)}
        badges={[
          t('collectionPanel.data.family.simpleJson'),
          outputStatusLabel(output, t),
        ]}
      />
      <ExportCard exportTarget={exportTarget} groupBy={collectionName} />
    </div>
  )
}

function StandardProfileOutputDetail({
  collectionName,
  output,
}: DataOutputDetailProps) {
  const { t } = useTranslation(['sources', 'common'])
  const { data: profilesData, isLoading, error } = useStandardProfiles()
  const { data: catalog } = useCollectionsCatalog()
  const profile = profilesData?.profiles.find((item) => item.name === output.name)
  const compatibility = useStandardProfileCompatibility(profile?.name)
  const validation = useStandardProfileValidation(profile?.name)
  const [editing, setEditing] = useState(false)

  if (isLoading) {
    return (
      <div className="rounded-md border bg-background p-4 text-sm text-muted-foreground">
        {t('common:status.loading')}
      </div>
    )
  }

  if (error || !profile) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
        {error instanceof Error
          ? error.message
          : t('collectionPanel.data.profileMissing')}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <DetailHeader
        icon={<FileBadge2 className="h-4 w-4 text-muted-foreground" />}
        title={profile.name}
        subtitle={configuredOutputSummary(output, t)}
        badges={[
          standardOutputLabel(output, t),
          outputStatusLabel(output, t),
        ]}
        action={
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setEditing((current) => !current)}
          >
            {editing ? (
              t('common:actions.cancel')
            ) : (
              <>
                <Pencil className="h-3.5 w-3.5" />
                {t('collections.standards.editProfileAction')}
              </>
            )}
          </Button>
        }
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-4">
          {editing ? (
            <ProfileEditor
              key={profile.name}
              profile={profile}
              catalog={catalog}
              currentCollectionName={collectionName}
              onSaved={() => setEditing(false)}
            />
          ) : (
            <ProfileSummaryPanel profileName={profile.name} output={output} />
          )}
          <ProfileOutputsPanel
            profile={profile}
            validation={validation.data}
            draftMode
          />
        </div>

        <aside className="space-y-4">
          <ProfileCompatibilityPanel
            report={compatibility.data}
            isLoading={compatibility.isLoading}
            error={compatibility.error}
          />
          <ProfileValidationReport
            report={validation.data}
            isLoading={validation.isLoading}
            error={validation.error}
          />
        </aside>
      </div>
    </div>
  )
}

function LegacyOutputDetail({
  output,
}: {
  output: CollectionDataConfiguredOutput
}) {
  const { t } = useTranslation(['sources'])

  return (
    <div className="space-y-4">
      <DetailHeader
        icon={<History className="h-4 w-4 text-muted-foreground" />}
        title={output.label}
        subtitle={configuredOutputSummary(output, t)}
        badges={[
          t('collectionPanel.data.legacyBadge'),
          standardOutputLabel(output, t),
        ]}
      />
      <div className="rounded-md border bg-background p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-600" />
          <div>
            <h3 className="text-sm font-medium">
              {t('collectionPanel.data.legacyDetailTitle')}
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              {output.evidence[0]?.message
                ?? t('collectionPanel.data.legacyDetailDescription')}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function ProfileSummaryPanel({
  profileName,
  output,
}: {
  profileName: string
  output: CollectionDataConfiguredOutput
}) {
  const { t } = useTranslation(['sources'])

  return (
    <section className="rounded-md border bg-background p-4">
      <h3 className="text-sm font-semibold">
        {t('collectionPanel.data.selectedOutputTitle')}
      </h3>
      <p className="mt-1 text-sm text-muted-foreground">
        {t('collectionPanel.data.selectedOutputDescription')}
      </p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <SummaryTile
          label={t('collections.standards.profileName')}
          value={profileName}
        />
        <SummaryTile
          label={t('collections.standards.mappingTitle')}
          value={t('collections.standards.mappedTermsCount', {
            count: Number(output.summary.mapped_terms ?? 0),
          })}
        />
        <SummaryTile
          label={t('collections.standards.outputs')}
          value={t('collections.standards.enabledOutputsCount', {
            count: Number(output.summary.enabled_outputs ?? 0),
          })}
        />
      </div>
    </section>
  )
}

function DetailHeader({
  icon,
  title,
  subtitle,
  badges,
  action,
}: {
  icon: ReactNode
  title: string
  subtitle: string
  badges: string[]
  action?: ReactNode
}) {
  return (
    <header className="rounded-md border bg-background p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-1">{icon}</span>
          <div className="min-w-0">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <h2 className="truncate text-lg font-semibold">{title}</h2>
              {badges.map((badge) => (
                <Badge key={badge} variant="outline">
                  {badge}
                </Badge>
              ))}
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>
          </div>
        </div>
        {action}
      </div>
    </header>
  )
}

function SummaryTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-muted/20 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate text-sm font-medium" title={value}>
        {value}
      </p>
    </div>
  )
}
