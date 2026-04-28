import { type FormEvent, type ReactNode, useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, GitBranch, Loader2, Search, Users } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { hierarchyInspectionInfiniteQueryOptions } from '@/features/import/queryUtils'
import { HierarchyTree } from './HierarchyTree'

interface HierarchyViewProps {
  referenceName: string
}

function MetricCard({
  icon,
  value,
  label,
}: {
  icon: ReactNode
  value: number
  label: string
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        {icon}
        <div>
          <div className="text-lg font-semibold">{value.toLocaleString()}</div>
          <div className="text-xs text-muted-foreground">{label}</div>
        </div>
      </CardContent>
    </Card>
  )
}

export function HierarchyView({ referenceName }: HierarchyViewProps) {
  const { t } = useTranslation('sources')
  const [searchInput, setSearchInput] = useState('')
  const [activeSearch, setActiveSearch] = useState('')
  const trimmedSearch = activeSearch.trim()
  const searchMode = trimmedSearch.length > 0

  const query = useInfiniteQuery({
    ...hierarchyInspectionInfiniteQueryOptions(
      referenceName,
      searchMode
        ? { mode: 'search', search: trimmedSearch }
        : { mode: 'roots' }
    ),
  })

  const pages = query.data?.pages ?? []
  const data = pages[0]
  const nodes = pages.flatMap((page) => page.nodes)

  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setActiveSearch(searchInput)
  }

  const clearSearch = () => {
    setSearchInput('')
    setActiveSearch('')
  }

  if (query.isLoading && !data) {
    return (
      <div className="space-y-4">
        <div className="grid gap-3 md:grid-cols-4">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (query.error) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          {t('hierarchy.loadError', 'Could not load hierarchy data.')}
        </AlertDescription>
      </Alert>
    )
  }

  if (!data || !data.metadata_available) {
    return (
      <Card>
        <CardContent className="py-10 text-center">
          <GitBranch className="mx-auto mb-3 h-10 w-10 text-muted-foreground opacity-60" />
          <div className="font-medium">
            {t('hierarchy.noMetadataTitle', 'No hierarchy structure detected')}
          </div>
          <p className="mx-auto mt-1 max-w-lg text-sm text-muted-foreground">
            {t(
              'hierarchy.noMetadataDescription',
              'This reference is marked as hierarchical, but the imported table does not expose recognizable hierarchy columns.'
            )}
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard
          icon={<Users className="h-6 w-6 text-primary" />}
          value={data.total_nodes}
          label={t('hierarchy.totalNodes', 'Nodes')}
        />
        <MetricCard
          icon={<GitBranch className="h-6 w-6 text-blue-500" />}
          value={data.root_count}
          label={t('hierarchy.roots', 'Roots')}
        />
        <MetricCard
          icon={<GitBranch className="h-6 w-6 text-emerald-600" />}
          value={data.levels.length}
          label={t('hierarchy.levels', 'Levels')}
        />
        <MetricCard
          icon={<AlertTriangle className="h-6 w-6 text-amber-500" />}
          value={data.orphan_count}
          label={t('hierarchy.orphans', 'Orphans')}
        />
      </div>

      <form onSubmit={submitSearch} className="flex gap-2">
        <div className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            className="pl-8"
            placeholder={t('hierarchy.searchPlaceholder', 'Search the hierarchy')}
          />
        </div>
        <Button type="submit" variant="outline">
          {t('hierarchy.search', 'Search')}
        </Button>
        {searchMode && (
          <Button type="button" variant="ghost" onClick={clearSearch}>
            {t('hierarchy.clearSearch', 'Clear')}
          </Button>
        )}
      </form>

      {data.levels.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {data.levels.map((level) => (
            <Badge key={level.level} variant="secondary">
              {level.level}: {level.count.toLocaleString()}
            </Badge>
          ))}
        </div>
      )}

      {query.isFetching && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          {t('hierarchy.refreshing', 'Refreshing hierarchy')}
        </div>
      )}

      {nodes.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            {searchMode
              ? t('hierarchy.noSearchResults', 'No matching nodes found.')
              : t('hierarchy.empty', 'No hierarchy nodes found.')}
          </CardContent>
        </Card>
      ) : (
        <HierarchyTree
          referenceName={referenceName}
          nodes={nodes}
          searchMode={searchMode}
        />
      )}

      {query.hasNextPage && (
        <div className="flex justify-center">
          <Button
            type="button"
            variant="outline"
            onClick={() => void query.fetchNextPage()}
            disabled={query.isFetchingNextPage}
          >
            {query.isFetchingNextPage && <Loader2 className="h-4 w-4 animate-spin" />}
            {query.isFetchingNextPage
              ? t('hierarchy.loadingMore', 'Loading more')
              : t('hierarchy.loadMore', 'Load more')}
          </Button>
        </div>
      )}
    </div>
  )
}
