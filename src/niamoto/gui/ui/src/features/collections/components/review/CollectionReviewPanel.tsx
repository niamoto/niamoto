import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Check,
  Eye,
  EyeOff,
  Loader2,
  Pause,
  Plus,
} from 'lucide-react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import {
  type CollectionCatalogEntry,
  type CollectionRole,
  useCollectionsCatalog,
  useUpdateCollection,
} from '@/features/collections/hooks/useCollectionsCatalog'

import { AddCollectionDialog } from './AddCollectionDialog'
import { CollectionEvidenceBadge } from './CollectionEvidenceBadge'

const ROLE_OPTIONS: CollectionRole[] = ['site', 'api', 'standard', 'technical']

export function CollectionReviewPanel() {
  const { t } = useTranslation(['sources', 'common'])
  const { data: catalog, isLoading, error } = useCollectionsCatalog()
  const updateCollection = useUpdateCollection()
  const [addOpen, setAddOpen] = useState(false)

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
        {error instanceof Error ? error.message : t('collections.review.loadFailed')}
      </div>
    )
  }

  const collections = catalog?.collections ?? []
  const pendingCount = collections.filter(
    (collection) => collection.review_status === 'pending',
  ).length

  const patchCollection = async (
    collection: CollectionCatalogEntry,
    update: Parameters<typeof updateCollection.mutateAsync>[0]['update'],
  ) => {
    try {
      await updateCollection.mutateAsync({
        collectionName: collection.name,
        update,
      })
    } catch (updateError) {
      toast.error(
        updateError instanceof Error
          ? updateError.message
          : t('collections.review.saveFailed'),
      )
    }
  }

  return (
    <div className="min-w-0 space-y-4 p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-xl font-semibold">
            {t('collections.review.title')}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t('collections.review.description', { count: pendingCount })}
          </p>
        </div>
        <Button
          variant="outline"
          className="shrink-0"
          onClick={() => setAddOpen(true)}
        >
          <Plus className="mr-2 h-4 w-4" />
          {t('collections.review.addCollection')}
        </Button>
      </div>

      {pendingCount > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200">
          {t('collections.review.pendingCallout', { count: pendingCount })}
        </div>
      )}

      <div className="grid min-w-0 gap-3">
        {collections.map((collection) => (
          <ReviewCard
            key={collection.name}
            collection={collection}
            pending={updateCollection.isPending}
            onPatch={(update) => patchCollection(collection, update)}
          />
        ))}
      </div>

      <AddCollectionDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        sources={catalog?.sources ?? []}
      />
    </div>
  )
}

interface ReviewCardProps {
  collection: CollectionCatalogEntry
  pending: boolean
  onPatch: (update: {
    label?: string
    roles?: CollectionRole[]
    visible?: boolean
    review_status?: CollectionCatalogEntry['review_status']
  }) => void
}

function ReviewCard({ collection, pending, onPatch }: ReviewCardProps) {
  const { t } = useTranslation(['sources'])
  const [label, setLabel] = useState(collection.label)

  const toggleRole = (role: CollectionRole) => {
    const nextRoles = collection.roles.includes(role)
      ? collection.roles.filter((item) => item !== role)
      : [...collection.roles, role]
    if (nextRoles.length > 0) {
      onPatch({ roles: nextRoles })
    }
  }

  return (
    <Card className="overflow-hidden">
      <CardHeader className="space-y-3 pb-3">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
              <h2 className="truncate text-base font-semibold">
                {collection.name}
              </h2>
              <Badge variant={collection.review_status === 'accepted' ? 'success' : 'outline'}>
                {t(`collections.review.status.${collection.review_status}`)}
              </Badge>
              <Badge variant="secondary">
                {t(`collections.review.grains.${collection.grain}`, collection.grain)}
              </Badge>
              <Badge variant="outline">
                {collection.visible
                  ? t('collections.review.visible')
                  : t('collections.review.hidden')}
              </Badge>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {t(`collections.review.sourceTypes.${collection.source_type}`)} ·{' '}
              {collection.source_name}
            </p>
          </div>

          <div className="flex shrink-0 flex-wrap gap-2">
            <Button
              size="sm"
              disabled={pending}
              onClick={() => onPatch({ review_status: 'accepted' })}
            >
              <Check className="h-3.5 w-3.5" />
              {t('collections.review.accept')}
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={pending}
              onClick={() => onPatch({ review_status: 'deferred' })}
            >
              <Pause className="h-3.5 w-3.5" />
              {t('collections.review.defer')}
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={pending}
              onClick={() => onPatch({ visible: !collection.visible })}
            >
              {collection.visible ? (
                <EyeOff className="h-3.5 w-3.5" />
              ) : (
                <Eye className="h-3.5 w-3.5" />
              )}
              {collection.visible
                ? t('collections.review.hide')
                : t('collections.review.show')}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="grid gap-2 md:grid-cols-[1fr_auto]">
          <Input
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            aria-label={t('collections.review.label')}
          />
          <Button
            variant="outline"
            disabled={pending || label.trim() === collection.label}
            onClick={() => onPatch({ label: label.trim() })}
          >
            {t('collections.review.saveLabel')}
          </Button>
        </div>

        <div className="flex flex-wrap gap-2">
          {ROLE_OPTIONS.map((role) => {
            const active = collection.roles.includes(role)
            return (
              <button
                key={role}
                type="button"
                className={cn(
                  'rounded-md border px-2 py-1 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  active
                    ? 'border-primary/30 bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-muted/50',
                )}
                disabled={pending}
                onClick={() => toggleRole(role)}
              >
                {t(`collections.review.rolesList.${role}`)}
              </button>
            )
          })}
        </div>

        {collection.evidence.length > 0 && (
          <div className="flex min-w-0 flex-wrap gap-1.5">
            {collection.evidence.map((evidence) => (
              <CollectionEvidenceBadge
                key={`${collection.name}-${evidence.kind}-${evidence.message}`}
                evidence={evidence}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
