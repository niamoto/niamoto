import { useMemo, useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  type CollectionRole,
  type CollectionSourceOption,
  useCreateCollection,
} from '@/features/collections/hooks/useCollectionsCatalog'

const ROLE_OPTIONS: CollectionRole[] = ['site', 'api', 'standard', 'technical']

interface AddCollectionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sources: CollectionSourceOption[]
}

export function AddCollectionDialog({
  open,
  onOpenChange,
  sources,
}: AddCollectionDialogProps) {
  const { t } = useTranslation(['sources', 'common'])
  const createCollection = useCreateCollection()
  const firstSource = sources[0]
  const [name, setName] = useState('')
  const [label, setLabel] = useState('')
  const [grain, setGrain] = useState('occurrence')
  const [sourceValue, setSourceValue] = useState('')
  const [roles, setRoles] = useState<CollectionRole[]>(['api', 'standard'])
  const [visible, setVisible] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const effectiveSourceValue = sourceValue || (firstSource ? sourceOptionValue(firstSource) : '')

  const selectedSource = useMemo(
    () =>
      sources.find((source) => sourceOptionValue(source) === effectiveSourceValue),
    [effectiveSourceValue, sources],
  )

  const toggleRole = (role: CollectionRole) => {
    setRoles((current) => {
      if (current.includes(role)) {
        return current.filter((item) => item !== role)
      }
      return [...current, role]
    })
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!selectedSource || roles.length === 0) {
      return
    }

    setError(null)
    try {
      await createCollection.mutateAsync({
        name: name.trim(),
        label: label.trim() || undefined,
        source_type: selectedSource.type,
        source_name: selectedSource.name,
        grain: grain.trim(),
        roles,
        visible,
      })
      setName('')
      setLabel('')
      setGrain('occurrence')
      setRoles(['api', 'standard'])
      setVisible(false)
      onOpenChange(false)
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : t('collections.review.addFailed'),
      )
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{t('collections.review.addTitle')}</DialogTitle>
            <DialogDescription>
              {t('collections.review.addDescription')}
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="collection-name">
                {t('collections.review.name')}
              </Label>
              <Input
                id="collection-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="occurrences_publication"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="collection-label">
                {t('collections.review.label')}
              </Label>
              <Input
                id="collection-label"
                value={label}
                onChange={(event) => setLabel(event.target.value)}
                placeholder={t('collections.review.labelPlaceholder')}
              />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-[1fr_160px]">
            <div className="space-y-1.5">
              <Label htmlFor="collection-source">
                {t('collections.review.source')}
              </Label>
              <select
                id="collection-source"
                value={effectiveSourceValue}
                onChange={(event) => setSourceValue(event.target.value)}
                className="h-8 w-full rounded-theme-sm border border-input bg-background px-3 text-sm outline-none transition-theme-fast focus-visible:ring-2 focus-visible:ring-ring"
                required
              >
                {sources.map((source) => (
                  <option key={sourceOptionValue(source)} value={sourceOptionValue(source)}>
                    {source.label} · {t(`collections.review.sourceTypes.${source.type}`)}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="collection-grain">
                {t('collections.review.grain')}
              </Label>
              <Input
                id="collection-grain"
                value={grain}
                onChange={(event) => setGrain(event.target.value)}
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>{t('collections.review.roles')}</Label>
            <div className="grid gap-2 sm:grid-cols-4">
              {ROLE_OPTIONS.map((role) => (
                <label
                  key={role}
                  className="flex min-w-0 items-center gap-2 rounded-md border px-2 py-2 text-sm"
                >
                  <input
                    type="checkbox"
                    checked={roles.includes(role)}
                    onChange={() => toggleRole(role)}
                    className="h-4 w-4"
                  />
                  <span className="truncate">
                    {t(`collections.review.rolesList.${role}`)}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <label className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
            <input
              type="checkbox"
              checked={visible}
              onChange={(event) => setVisible(event.target.checked)}
              className="h-4 w-4"
            />
            {t('collections.review.visiblePage')}
          </label>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              {t('common:actions.cancel')}
            </Button>
            <Button
              type="submit"
              disabled={
                createCollection.isPending ||
                !name.trim() ||
                !grain.trim() ||
                !selectedSource ||
                roles.length === 0
              }
            >
              {t('collections.review.create')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function sourceOptionValue(source: CollectionSourceOption) {
  return `${source.type}:${source.name}`
}
