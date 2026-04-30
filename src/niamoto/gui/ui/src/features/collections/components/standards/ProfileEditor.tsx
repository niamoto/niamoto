import { useMemo, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DwcMappingEditor } from '@/features/collections/components/api/DwcMappingEditor'
import type { CollectionCatalog } from '@/features/collections/hooks/useCollectionsCatalog'
import {
  type StandardProfileConfig,
  type StandardProfileCreate,
  type StandardProfileOutputType,
  type StandardProfileSource,
  type StandardProfileSourceType,
  type StandardProfileType,
  useCreateStandardProfile,
  useUpdateStandardProfile,
} from '@/features/collections/hooks/useStandardProfiles'

interface ProfileEditorProps {
  profile?: StandardProfileConfig
  catalog?: CollectionCatalog
  currentCollectionName?: string
  onSaved?: (profile: StandardProfileConfig) => void
}

interface SourceOption {
  type: StandardProfileSourceType
  name: string
  label: string
  hidden?: boolean
}

const STANDARD_OPTIONS: StandardProfileType[] = [
  'darwin_core_occurrence',
  'humboldt_event',
]

const OUTPUT_TYPES_BY_STANDARD: Record<StandardProfileType, StandardProfileOutputType[]> = {
  darwin_core_occurrence: ['api_json', 'dwc_archive'],
  humboldt_event: ['api_json', 'standard_files'],
}

export function ProfileEditor({
  profile,
  catalog,
  currentCollectionName,
  onSaved,
}: ProfileEditorProps) {
  const { t } = useTranslation(['sources'])
  const sourceOptions = useSourceOptions(catalog)
  const defaultSource =
    sourceOptions.find(
      (source) => source.type === 'collection' && source.name === currentCollectionName,
    ) ?? sourceOptions[0]
  const createProfile = useCreateStandardProfile()
  const updateProfile = useUpdateStandardProfile(profile?.name ?? '')
  const [name, setName] = useState(profile?.name ?? '')
  const [standard, setStandard] = useState<StandardProfileType>(
    profile?.standard ?? 'darwin_core_occurrence',
  )
  const [targetGrain, setTargetGrain] = useState(
    profile?.target_grain ?? defaultTargetGrain(standard),
  )
  const [sourceValue, setSourceValue] = useState(
    profile ? sourceValueFromSource(profile.source) : sourceValueFromOption(defaultSource),
  )
  const [mappings, setMappings] = useState<Record<string, unknown>>(
    profile?.mappings ?? defaultMappings(standard),
  )
  const [enabledOutputs, setEnabledOutputs] = useState<StandardProfileOutputType[]>(
    profile?.outputs.filter((output) => output.enabled).map((output) => output.type) ??
      OUTPUT_TYPES_BY_STANDARD[standard],
  )
  const [error, setError] = useState<string | null>(null)
  const effectiveSourceValue =
    sourceValue ||
    (profile ? sourceValueFromSource(profile.source) : sourceValueFromOption(defaultSource))

  const selectedSource = useMemo(
    () =>
      sourceOptions.find(
        (source) => sourceValueFromOption(source) === effectiveSourceValue,
      ),
    [effectiveSourceValue, sourceOptions],
  )
  const outputTypes = OUTPUT_TYPES_BY_STANDARD[standard]
  const isPending = createProfile.isPending || updateProfile.isPending

  const toggleOutput = (outputType: StandardProfileOutputType) => {
    setEnabledOutputs((current) => {
      if (current.includes(outputType)) {
        return current.filter((item) => item !== outputType)
      }
      return [...current, outputType]
    })
  }

  const handleStandardChange = (nextStandard: StandardProfileType) => {
    setStandard(nextStandard)
    setTargetGrain(defaultTargetGrain(nextStandard))
    setMappings((current) =>
      Object.keys(current).length > 0 ? current : defaultMappings(nextStandard),
    )
    setEnabledOutputs((current) => {
      const allowed = OUTPUT_TYPES_BY_STANDARD[nextStandard]
      const retained = current.filter((outputType) => allowed.includes(outputType))
      return retained.length > 0 ? retained : allowed
    })
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!selectedSource) {
      return
    }

    const source: StandardProfileSource = {
      type: selectedSource.type,
      name: selectedSource.name,
    }
    const payload: StandardProfileCreate = {
      name: name.trim(),
      enabled: true,
      standard,
      target_grain: targetGrain.trim(),
      source,
      mappings,
      outputs: buildProfileOutputs(profile, outputTypes, enabledOutputs, name.trim()),
    }

    setError(null)
    try {
      const result = profile
        ? await updateProfile.mutateAsync({
            standard: payload.standard,
            target_grain: payload.target_grain,
            source: payload.source,
            mappings: payload.mappings,
            outputs: payload.outputs,
          })
        : await createProfile.mutateAsync(payload)
      onSaved?.(result.profile)
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : t('collections.standards.saveFailed'),
      )
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <h3 className="text-sm font-semibold">
          {profile
            ? t('collections.standards.editProfile')
            : t('collections.standards.newProfile')}
        </h3>
        <p className="text-xs text-muted-foreground">
          {t('collections.standards.profileEditorHelp')}
        </p>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="standard-profile-name">
                {t('collections.standards.profileName')}
              </Label>
              <Input
                id="standard-profile-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                disabled={Boolean(profile)}
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="standard-profile-standard">
                {t('collections.standards.standard')}
              </Label>
              <select
                id="standard-profile-standard"
                value={standard}
                onChange={(event) =>
                  handleStandardChange(event.target.value as StandardProfileType)
                }
                className="h-8 w-full rounded-theme-sm border border-input bg-background px-3 text-sm outline-none transition-theme-fast focus-visible:ring-2 focus-visible:ring-ring"
              >
                {STANDARD_OPTIONS.map((item) => (
                  <option key={item} value={item}>
                    {t(`collections.standards.standardTypes.${item}`)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-[1fr_160px]">
            <div className="space-y-1.5">
              <Label htmlFor="standard-profile-source">
                {t('collections.standards.source')}
              </Label>
              <select
                id="standard-profile-source"
                value={effectiveSourceValue}
                onChange={(event) => setSourceValue(event.target.value)}
                className="h-8 w-full rounded-theme-sm border border-input bg-background px-3 text-sm outline-none transition-theme-fast focus-visible:ring-2 focus-visible:ring-ring"
                required
              >
                {sourceOptions.map((source) => (
                  <option key={sourceValueFromOption(source)} value={sourceValueFromOption(source)}>
                    {source.label}
                    {source.hidden ? ` · ${t('collections.standards.hiddenSource')}` : ''}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="standard-profile-grain">
                {t('collections.standards.targetGrain')}
              </Label>
              <Input
                id="standard-profile-grain"
                value={targetGrain}
                onChange={(event) => setTargetGrain(event.target.value)}
                required
              />
            </div>
          </div>

          <DwcMappingEditor
            value={mappings}
            onChange={setMappings}
            title={t('collections.standards.mappingTitle')}
            description={t('collections.standards.mappingHelp')}
            referenceHelp={t('collections.standards.mappingReferenceHelp')}
          />

          <div className="space-y-2">
            <Label>{t('collections.standards.outputs')}</Label>
            <div className="grid gap-2 md:grid-cols-2">
              {outputTypes.map((outputType) => (
                <label
                  key={outputType}
                  className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={enabledOutputs.includes(outputType)}
                    onChange={() => toggleOutput(outputType)}
                    className="h-4 w-4"
                  />
                  {t(`collections.standards.outputTypes.${outputType}`)}
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-end">
            <Button type="submit" disabled={isPending || !name.trim()}>
              {t('collections.standards.saveProfile')}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

function useSourceOptions(catalog?: CollectionCatalog): SourceOption[] {
  return useMemo(() => {
    if (!catalog) {
      return []
    }

    const collectionSources: SourceOption[] = catalog.collections.map((collection) => ({
      type: 'collection',
      name: collection.name,
      label: `${collection.label} · collection`,
      hidden: !collection.visible || collection.roles.includes('technical'),
    }))
    const rawSources: SourceOption[] = catalog.sources.map((source) => ({
      type: source.type,
      name: source.name,
      label: `${source.label} · ${source.type}`,
    }))
    return [...collectionSources, ...rawSources]
  }, [catalog])
}

function sourceValueFromSource(source: StandardProfileSource) {
  return `${source.type}:${source.name}`
}

function sourceValueFromOption(source?: SourceOption) {
  return source ? `${source.type}:${source.name}` : ''
}

function defaultTargetGrain(standard: StandardProfileType) {
  return standard === 'darwin_core_occurrence' ? 'occurrence' : 'event'
}

function defaultMappings(standard: StandardProfileType): Record<string, unknown> {
  if (standard === 'darwin_core_occurrence') {
    return { occurrenceID: { source: 'id' } }
  }
  return { eventID: { source: 'id' } }
}

function defaultOutputParams(
  profileName: string,
  outputType: StandardProfileOutputType,
): Record<string, unknown> {
  const outputDir = `exports/profiles/${profileName || 'standard_profile'}`
  if (outputType === 'dwc_archive') {
    return {
      output_dir: outputDir,
      archive_name: `${profileName || 'standard_profile'}-dwc.zip`,
    }
  }
  return { output_dir: outputDir }
}

function buildProfileOutputs(
  profile: StandardProfileConfig | undefined,
  outputTypes: StandardProfileOutputType[],
  enabledOutputs: StandardProfileOutputType[],
  profileName: string,
) {
  return outputTypes.map((outputType) => {
    const existingOutput = profile?.outputs.find(
      (output) => output.type === outputType,
    )
    return {
      type: outputType,
      enabled: enabledOutputs.includes(outputType),
      params: existingOutput?.params ?? defaultOutputParams(profileName, outputType),
    }
  })
}
