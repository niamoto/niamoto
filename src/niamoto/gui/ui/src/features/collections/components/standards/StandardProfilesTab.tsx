import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, FileBadge2, Loader2, Plus } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { useCollectionsCatalog } from '@/features/collections/hooks/useCollectionsCatalog'
import {
  type LegacyStandardProfileHint,
  type StandardProfileConfig,
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
  const { data, isLoading, error } = useStandardProfiles()
  const { data: catalog } = useCollectionsCatalog()
  const profiles = data?.profiles ?? EMPTY_PROFILES
  const legacyHints = data?.legacy_hints ?? EMPTY_LEGACY_HINTS
  const [selectedName, setSelectedName] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const selectedProfile = useMemo(() => {
    if (creating) {
      return undefined
    }
    if (selectedName) {
      return profiles.find((profile) => profile.name === selectedName)
    }
    return (
      profiles.find((profile) => profile.source.name === collectionName) ??
      profiles[0]
    )
  }, [collectionName, creating, profiles, selectedName])

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
              }}
              title={t('collections.standards.newProfile')}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="space-y-2 p-3">
          {profiles.length === 0 && (
            <Card>
              <CardContent className="p-3 text-xs text-muted-foreground">
                {t('collections.standards.empty')}
              </CardContent>
            </Card>
          )}
          {profiles.map((profile) => (
            <ProfileListButton
              key={profile.name}
              profile={profile}
              selected={!creating && selectedProfile?.name === profile.name}
              contextual={profile.source.name === collectionName}
              onClick={() => {
                setCreating(false)
                setSelectedName(profile.name)
              }}
            />
          ))}
          {legacyHints.length > 0 && (
            <div className={cn('space-y-2', profiles.length > 0 && 'border-t pt-3')}>
              <p className="px-1 text-xs font-medium text-muted-foreground">
                {t('collections.standards.legacyHintsTitle')}
              </p>
              {legacyHints.map((hint) => (
                <LegacyHintCard key={hint.export_name} hint={hint} />
              ))}
            </div>
          )}
        </div>
      </aside>

      <main className="min-h-0 overflow-auto p-4">
        {creating || !selectedProfile ? (
          <ProfileEditor
            key="new-profile"
            catalog={catalog}
            currentCollectionName={collectionName}
            onSaved={(profile) => {
              setCreating(false)
              setSelectedName(profile.name)
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
              </div>

              <ProfileEditor
                key={selectedProfile.name}
                profile={selectedProfile}
                catalog={catalog}
                currentCollectionName={collectionName}
                onSaved={(profile) => setSelectedName(profile.name)}
              />
            </div>

            <div className="space-y-4">
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
              <ProfileOutputsPanel
                profile={selectedProfile}
                validation={validation.data}
              />
            </div>
          </div>
        )}
      </main>
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
