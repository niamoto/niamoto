import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, FileBadge2, Loader2, Pencil, Plus } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import {
  type CollectionCatalogEntry,
  useCollectionsCatalog,
} from '@/features/collections/hooks/useCollectionsCatalog'
import {
  type LegacyStandardProfileHint,
  type StandardProfileConfig,
  type StandardProfileSource,
  type StandardProfileType,
  useStandardProfileCompatibility,
  useStandardProfiles,
  useStandardProfileValidation,
} from '@/features/collections/hooks/useStandardProfiles'

import { ProfileCompatibilityPanel } from './ProfileCompatibilityPanel'
import { ProfileEditor } from './ProfileEditor'
import { ProfileOutputsPanel } from './ProfileOutputsPanel'
import { ProfileValidationReport } from './ProfileValidationReport'

interface StandardProfilesTabProps {
  collectionName: string
}

const EMPTY_PROFILES: StandardProfileConfig[] = []
const EMPTY_LEGACY_HINTS: LegacyStandardProfileHint[] = []

export function StandardProfilesTab({ collectionName }: StandardProfilesTabProps) {
  const { t } = useTranslation(['sources', 'common'])
  const [searchParams] = useSearchParams()
  const { data, isLoading, error } = useStandardProfiles()
  const { data: catalog } = useCollectionsCatalog()
  const profiles = data?.profiles ?? EMPTY_PROFILES
  const legacyHints = data?.legacy_hints ?? EMPTY_LEGACY_HINTS
  const collectionMetadata = useMemo(
    () =>
      catalog?.collections.find((collection) => collection.name === collectionName),
    [catalog, collectionName],
  )
  const requestedCreate =
    searchParams.get('data_action') === 'create_standard_profile'
  const requestedStandard = parseStandardProfileType(searchParams.get('standard'))
  const requestedTargetGrain = searchParams.get('target_grain') ?? undefined
  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [creating, setCreating] = useState(requestedCreate)
  const [editingName, setEditingName] = useState<string | null>(null)

  useEffect(() => {
    if (!requestedCreate) {
      return
    }
    setCreating(true)
    setSelectedName(null)
    setEditingName(null)
  }, [requestedCreate, requestedStandard, requestedTargetGrain])

  const collectionProfiles = useMemo(
    () =>
      profiles.filter((profile) =>
        profileBelongsToCollection(profile, collectionName, collectionMetadata),
      ),
    [collectionMetadata, collectionName, profiles],
  )
  const collectionLegacyHints = useMemo(
    () =>
      legacyHints.filter((hint) =>
        sourceBelongsToCollection(hint.source, collectionName, collectionMetadata),
      ),
    [collectionMetadata, collectionName, legacyHints],
  )

  const selectedProfile = useMemo(() => {
    if (creating) {
      return undefined
    }
    if (selectedName) {
      const selected = collectionProfiles.find(
        (profile) => profile.name === selectedName,
      )
      if (selected) {
        return selected
      }
    }
    return collectionProfiles[0]
  }, [collectionProfiles, creating, selectedName])
  const showingCreateForm = creating || !selectedProfile
  const isEditingSelectedProfile =
    Boolean(selectedProfile) && editingName === selectedProfile?.name

  const compatibility = useStandardProfileCompatibility(selectedProfile?.name)
  const validation = useStandardProfileValidation(selectedProfile?.name)

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        {t('common:status.loading')}
      </div>
    )
  }

  if (error) {
    return (
      <div className="m-4 rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
        {error instanceof Error ? error.message : t('collections.standards.loadFailed')}
      </div>
    )
  }

  return (
    <div className="grid h-full min-h-0 grid-cols-[280px_1fr] overflow-hidden">
      <aside className="min-h-0 border-r bg-muted/20">
        <div className="border-b p-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold">
                {t('collections.standards.title')}
              </h2>
              <p className="mt-1 text-xs text-muted-foreground">
                {t('collections.standards.description')}
              </p>
            </div>
            <Button
              size="icon"
              variant="outline"
              onClick={() => {
                setCreating(true)
                setSelectedName(null)
                setEditingName(null)
              }}
              disabled={showingCreateForm}
              aria-label={t('collections.standards.newProfile')}
              title={t('collections.standards.newProfile')}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="space-y-2 p-3">
          {collectionProfiles.length === 0 && (
            <Card>
              <CardContent className="p-3 text-xs text-muted-foreground">
                {t('collections.standards.empty')}
              </CardContent>
            </Card>
          )}
          {collectionProfiles.map((profile) => (
            <ProfileListButton
              key={profile.name}
              profile={profile}
              selected={!creating && selectedProfile?.name === profile.name}
              contextual
              onClick={() => {
                setCreating(false)
                setSelectedName(profile.name)
                setEditingName(null)
              }}
            />
          ))}
          {collectionLegacyHints.length > 0 && (
            <div className={cn('space-y-2', collectionProfiles.length > 0 && 'border-t pt-3')}>
              <p className="px-1 text-xs font-medium text-muted-foreground">
                {t('collections.standards.legacyHintsTitle')}
              </p>
              {collectionLegacyHints.map((hint) => (
                <LegacyHintCard key={hint.export_name} hint={hint} />
              ))}
            </div>
          )}
        </div>
      </aside>

      <main className="min-h-0 overflow-auto p-4">
        {showingCreateForm ? (
          <ProfileEditor
            key="new-profile"
            catalog={catalog}
            currentCollectionName={collectionName}
            initialStandard={requestedStandard}
            initialTargetGrain={requestedTargetGrain}
            onSaved={(profile) => {
              setCreating(false)
              setSelectedName(profile.name)
              setEditingName(null)
            }}
          />
        ) : (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <FileBadge2 className="h-4 w-4 text-muted-foreground" />
                <h2 className="text-lg font-semibold">{selectedProfile.name}</h2>
                <Badge variant="secondary">
                  {t(`collections.standards.standardTypes.${selectedProfile.standard}`)}
                </Badge>
                <Badge variant="outline">
                  {t('collections.standards.sourceSummary', {
                    type: selectedProfile.source.type,
                    name: selectedProfile.source.name,
                  })}
                </Badge>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="ml-auto"
                  onClick={() =>
                    setEditingName(
                      isEditingSelectedProfile ? null : selectedProfile.name,
                    )
                  }
                >
                  {isEditingSelectedProfile ? (
                    t('common:actions.cancel')
                  ) : (
                    <>
                      <Pencil className="mr-2 h-3.5 w-3.5" />
                      {t('collections.standards.editProfileAction')}
                    </>
                  )}
                </Button>
              </div>

              {isEditingSelectedProfile ? (
                <ProfileEditor
                  key={selectedProfile.name}
                  profile={selectedProfile}
                  catalog={catalog}
                  currentCollectionName={collectionName}
                  onSaved={(profile) => {
                    setSelectedName(profile.name)
                    setEditingName(null)
                  }}
                />
              ) : (
                <ProfileOverviewCard profile={selectedProfile} />
              )}
              <ProfileOutputsPanel
                profile={selectedProfile}
                validation={validation.data}
              />
            </div>

            <aside className="space-y-4">
              <SelectedProfileStatusCard profile={selectedProfile} />
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
        )}
      </main>
    </div>
  )
}

function profileBelongsToCollection(
  profile: StandardProfileConfig,
  collectionName: string,
  collection?: CollectionCatalogEntry,
) {
  return sourceBelongsToCollection(profile.source, collectionName, collection)
}

function sourceBelongsToCollection(
  source: StandardProfileSource | null | undefined,
  collectionName: string,
  collection?: CollectionCatalogEntry,
) {
  if (!source) {
    return false
  }
  if (source.type === 'collection' && source.name === collectionName) {
    return true
  }
  return Boolean(
    collection &&
      source.type === collection.source_type &&
      source.name === collection.source_name,
  )
}

function parseStandardProfileType(
  value: string | null,
): StandardProfileType | undefined {
  if (value === 'darwin_core_occurrence' || value === 'humboldt_event') {
    return value
  }
  return undefined
}

interface SelectedProfileStatusCardProps {
  profile: StandardProfileConfig
}

function SelectedProfileStatusCard({ profile }: SelectedProfileStatusCardProps) {
  const { t } = useTranslation(['sources'])

  return (
    <Card>
      <CardHeader className="space-y-2 pb-3">
        <div className="flex items-center gap-2">
          <FileBadge2 className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">
            {t('collections.standards.selectedProfileStatus')}
          </h3>
        </div>
        <div className="min-w-0 space-y-2">
          <p className="truncate text-sm font-medium">{profile.name}</p>
          <div className="flex flex-wrap gap-1">
            <Badge variant="secondary" className="text-[10px]">
              {t(`collections.standards.standardTypes.${profile.standard}`)}
            </Badge>
            <Badge variant="outline" className="text-[10px]">
              {t('collections.standards.sourceSummary', {
                type: profile.source.type,
                name: profile.source.name,
              })}
            </Badge>
          </div>
        </div>
      </CardHeader>
    </Card>
  )
}

interface ProfileOverviewCardProps {
  profile: StandardProfileConfig
}

function ProfileOverviewCard({ profile }: ProfileOverviewCardProps) {
  const { t } = useTranslation(['sources'])
  const mappingCount = Object.keys(profile.mappings).length
  const enabledOutputCount = profile.outputs.filter((output) => output.enabled).length

  return (
    <Card>
      <CardHeader className="pb-3">
        <h3 className="text-sm font-semibold">
          {t('collections.standards.profileOverview')}
        </h3>
        <p className="text-xs text-muted-foreground">
          {t('collections.standards.profileOverviewHelp')}
        </p>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <ProfileOverviewMetric
          label={t('collections.standards.mappingTitle')}
          value={t('collections.standards.mappedTermsCount', {
            count: mappingCount,
          })}
        />
        <ProfileOverviewMetric
          label={t('collections.standards.outputs')}
          value={t('collections.standards.enabledOutputsCount', {
            count: enabledOutputCount,
          })}
        />
        <ProfileOverviewMetric
          label={t('collections.standards.source')}
          value={t('collections.standards.sourceSummary', {
            type: profile.source.type,
            name: profile.source.name,
          })}
        />
        <ProfileOverviewMetric
          label={t('collections.standards.targetGrain')}
          value={profile.target_grain}
        />
      </CardContent>
    </Card>
  )
}

interface ProfileOverviewMetricProps {
  label: string
  value: string
}

function ProfileOverviewMetric({ label, value }: ProfileOverviewMetricProps) {
  return (
    <div className="rounded-md border bg-muted/20 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 truncate text-sm font-medium">{value}</p>
    </div>
  )
}

interface LegacyHintCardProps {
  hint: LegacyStandardProfileHint
}

function LegacyHintCard({ hint }: LegacyHintCardProps) {
  const { t } = useTranslation(['sources'])
  const standardLabel = t(`collections.standards.standardTypes.${hint.standard}`)

  return (
    <Card>
      <CardContent className="space-y-2 p-3 text-xs">
        <div className="flex min-w-0 items-center gap-2">
          <FileBadge2 className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span className="truncate font-medium">{hint.export_name}</span>
        </div>
        <p className="text-muted-foreground">
          {t('collections.standards.legacyHintDescription', {
            exportName: hint.export_name,
            standard: standardLabel,
          })}
        </p>
      </CardContent>
    </Card>
  )
}

interface ProfileListButtonProps {
  profile: StandardProfileConfig
  selected: boolean
  contextual: boolean
  onClick: () => void
}

function ProfileListButton({
  profile,
  selected,
  contextual,
  onClick,
}: ProfileListButtonProps) {
  const { t } = useTranslation(['sources'])
  const hasDraftStatus = profile.validation_status !== 'conformant'

  return (
    <button
      type="button"
      className={cn(
        'w-full rounded-md border bg-background p-3 text-left text-sm transition-colors hover:border-primary/50',
        selected && 'border-primary bg-primary/5',
      )}
      onClick={onClick}
    >
      <div className="flex min-w-0 items-center justify-between gap-2">
        <span className="truncate font-medium">{profile.name}</span>
        {hasDraftStatus && <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />}
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        <Badge variant="secondary" className="text-[10px]">
          {t(`collections.standards.standardTypes.${profile.standard}`)}
        </Badge>
        <Badge variant="outline" className="text-[10px]">
          {t(`collections.standards.validationStatus.${profile.validation_status}`)}
        </Badge>
        {contextual && (
          <Badge variant="outline" className="text-[10px]">
            {t('collections.standards.currentCollection')}
          </Badge>
        )}
      </div>
    </button>
  )
}
