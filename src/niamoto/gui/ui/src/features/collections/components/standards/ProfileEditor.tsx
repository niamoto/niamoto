import { useMemo, useRef, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Sparkles } from 'lucide-react'

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
  useAutoConfigureStandardProfile,
  useCreateStandardProfile,
  useStandardProfileSourceFields,
  useUpdateStandardProfile,
} from '@/features/collections/hooks/useStandardProfiles'

interface ProfileEditorProps {
  profile?: StandardProfileConfig
  catalog?: CollectionCatalog
  currentCollectionName?: string
  initialStandard?: StandardProfileType
  initialTargetGrain?: string
  onSaved?: (profile: StandardProfileConfig) => void
}

interface SourceOption {
  type: StandardProfileSourceType
  name: string
  label: string
  hidden?: boolean
}

interface AutoConfigSummary {
  mappedCount: number
  columnsInspected: number
  unresolved: string[]
  notes: string[]
}

const STANDARD_OPTIONS: StandardProfileType[] = [
  'darwin_core_occurrence',
  'humboldt_event',
]

const OUTPUT_TYPES_BY_STANDARD: Record<StandardProfileType, StandardProfileOutputType[]> = {
  darwin_core_occurrence: ['api_json', 'dwc_archive'],
  humboldt_event: ['api_json', 'standard_files'],
}

const STANDARD_GENERATORS_BY_STANDARD: Record<StandardProfileType, string[]> = {
  darwin_core_occurrence: [
    'unique_occurrence_id',
    'constant',
    'current_date',
    'extract_geometry_coordinate',
    'format_measurements',
    'dynamic_properties',
  ],
  humboldt_event: ['constant', 'current_date'],
}

export function ProfileEditor({
  profile,
  catalog,
  currentCollectionName,
  initialStandard,
  initialTargetGrain,
  onSaved,
}: ProfileEditorProps) {
  const { t } = useTranslation(['sources'])
  const sourceOptions = useSourceOptions(catalog)
  const defaultSource =
    sourceOptions.find(
      (source) => source.type === 'collection' && source.name === currentCollectionName,
    ) ?? sourceOptions[0]
  const autoConfigureProfile = useAutoConfigureStandardProfile()
  const createProfile = useCreateStandardProfile()
  const updateProfile = useUpdateStandardProfile(profile?.name ?? '')
  const defaultStandard = profile?.standard ?? initialStandard ?? 'darwin_core_occurrence'
  const [name, setName] = useState(profile?.name ?? '')
  const [standard, setStandard] = useState<StandardProfileType>(defaultStandard)
  const [targetGrain, setTargetGrain] = useState(
    profile?.target_grain ?? initialTargetGrain ?? defaultTargetGrain(defaultStandard),
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
  const [autoConfigSummary, setAutoConfigSummary] =
    useState<AutoConfigSummary | null>(null)
  const editRevisionRef = useRef(0)
  const autoConfigRequestRef = useRef(0)
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
  const selectedProfileSource = useMemo<StandardProfileSource | null>(
    () =>
      selectedSource
        ? {
            type: selectedSource.type,
            name: selectedSource.name,
          }
        : null,
    [selectedSource],
  )
  const sourceFieldsRequest = useMemo(
    () =>
      selectedProfileSource
        ? {
            standard,
            target_grain: targetGrain.trim() || undefined,
            source: selectedProfileSource,
          }
        : null,
    [selectedProfileSource, standard, targetGrain],
  )
  const sourceFieldsQuery = useStandardProfileSourceFields(
    sourceFieldsRequest,
    Boolean(selectedProfileSource),
  )
  const sourceFields = useMemo(
    () => sourceFieldsQuery.data?.fields.map((field) => field.name) ?? [],
    [sourceFieldsQuery.data],
  )
  const outputTypes = OUTPUT_TYPES_BY_STANDARD[standard]
  const isSaving = createProfile.isPending || updateProfile.isPending
  const isBusy = isSaving || autoConfigureProfile.isPending

  const markEdited = () => {
    editRevisionRef.current += 1
    setAutoConfigSummary(null)
  }

  const toggleOutput = (outputType: StandardProfileOutputType) => {
    markEdited()
    setEnabledOutputs((current) => {
      if (current.includes(outputType)) {
        return current.filter((item) => item !== outputType)
      }
      return [...current, outputType]
    })
  }

  const handleStandardChange = (nextStandard: StandardProfileType) => {
    markEdited()
    setStandard(nextStandard)
    setTargetGrain(defaultTargetGrain(nextStandard))
    setMappings(defaultMappings(nextStandard))
    setEnabledOutputs(OUTPUT_TYPES_BY_STANDARD[nextStandard])
  }

  const handleAutoConfigure = async () => {
    if (!selectedProfileSource) {
      return
    }

    const source = selectedProfileSource
    const requestId = autoConfigRequestRef.current + 1
    autoConfigRequestRef.current = requestId
    const requestRevision = editRevisionRef.current

    setError(null)
    setAutoConfigSummary(null)
    try {
      const result = await autoConfigureProfile.mutateAsync({
        name: name.trim() || undefined,
        standard,
        target_grain: targetGrain.trim() || undefined,
        source,
      })
      if (
        requestId !== autoConfigRequestRef.current ||
        requestRevision !== editRevisionRef.current
      ) {
        return
      }
      const proposedProfile = result.profile
      setName((current) => current || proposedProfile.name)
      setStandard(proposedProfile.standard)
      setTargetGrain(proposedProfile.target_grain)
      setSourceValue(sourceValueFromSource(proposedProfile.source))
      setMappings(proposedProfile.mappings)
      setEnabledOutputs(
        proposedProfile.outputs
          .filter((output) => output.enabled)
          .map((output) => output.type),
      )
      setAutoConfigSummary({
        mappedCount: result.terms.filter((term) => term.status === 'mapped').length,
        columnsInspected: result.columns_inspected,
        unresolved: result.unresolved,
        notes: result.notes,
      })
    } catch (autoConfigError) {
      if (
        requestId !== autoConfigRequestRef.current ||
        requestRevision !== editRevisionRef.current
      ) {
        return
      }
      setError(
        autoConfigError instanceof Error
          ? autoConfigError.message
          : t('collections.standards.autoConfigFailed'),
      )
    }
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!selectedProfileSource) {
      return
    }

    const payload: StandardProfileCreate = {
      name: name.trim(),
      enabled: true,
      standard,
      target_grain: targetGrain.trim(),
      source: selectedProfileSource,
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
      <CardHeader className="gap-3 pb-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h3 className="text-sm font-semibold">
            {profile
              ? t('collections.standards.editProfile')
              : t('collections.standards.newProfile')}
          </h3>
          <p className="text-xs text-muted-foreground">
            {t('collections.standards.profileEditorHelp')}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleAutoConfigure}
          disabled={!selectedProfileSource || isBusy}
          title={t('collections.standards.autoConfigureHelp')}
        >
          {autoConfigureProfile.isPending ? (
            <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Sparkles className="mr-2 h-3.5 w-3.5" />
          )}
          {t('collections.standards.autoConfigure')}
        </Button>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {autoConfigSummary && (
            <div className="space-y-2 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-950">
              <p>
                {t('collections.standards.autoConfigured', {
                  count: autoConfigSummary.mappedCount,
                  columns: autoConfigSummary.columnsInspected,
                })}
              </p>
              {autoConfigSummary.notes.length > 0 && (
                <ul className="list-disc space-y-1 pl-5 text-xs">
                  {autoConfigSummary.notes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                </ul>
              )}
              {autoConfigSummary.unresolved.length > 0 && (
                <p className="text-xs">
                  {t('collections.standards.autoConfigUnresolved', {
                    terms: autoConfigSummary.unresolved.join(', '),
                  })}
                </p>
              )}
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
                onChange={(event) => {
                  markEdited()
                  setName(event.target.value)
                }}
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
                onChange={(event) => {
                  markEdited()
                  setSourceValue(event.target.value)
                }}
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
                onChange={(event) => {
                  markEdited()
                  setTargetGrain(event.target.value)
                }}
                required
              />
            </div>
          </div>

          <DwcMappingEditor
            value={mappings}
            title={t('collections.standards.mappingTitle')}
            description={t('collections.standards.mappingHelp')}
            referenceHelp={t('collections.standards.mappingReferenceHelp')}
            sourceFields={sourceFields}
            generatorOptions={STANDARD_GENERATORS_BY_STANDARD[standard]}
            dialect="standard_profile"
            onChange={(nextMappings) => {
              markEdited()
              setMappings(nextMappings)
            }}
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
            <Button type="submit" disabled={isBusy || !name.trim()}>
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
