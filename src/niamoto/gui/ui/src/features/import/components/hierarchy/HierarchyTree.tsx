import { useState } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, ChevronDown, ChevronRight, Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import type { HierarchyNode } from '@/features/import/api/hierarchy'
import { hierarchyInspectionInfiniteQueryOptions } from '@/features/import/queryUtils'

interface HierarchyTreeProps {
  referenceName: string
  nodes: HierarchyNode[]
  searchMode?: boolean
}

function nodeKey(node: HierarchyNode) {
  return String(node.id)
}

function SearchResultRow({ node }: { node: HierarchyNode }) {
  return (
    <div className="rounded-md border px-3 py-2 text-sm">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-medium">{node.label}</div>
          {node.path && (
            <div className="mt-0.5 truncate text-xs text-muted-foreground">{node.path}</div>
          )}
        </div>
        {node.rank && <Badge variant="outline">{node.rank}</Badge>}
      </div>
    </div>
  )
}

function HierarchyTreeNode({
  referenceName,
  node,
  depth = 0,
}: {
  referenceName: string
  node: HierarchyNode
  depth?: number
}) {
  const { t } = useTranslation('sources')
  const [open, setOpen] = useState(false)
  const childQuery = useInfiniteQuery({
    ...hierarchyInspectionInfiniteQueryOptions(referenceName, {
      mode: 'children',
      parentId: node.id,
    }),
    enabled: open && node.has_children,
  })

  const childNodes = childQuery.data?.pages.flatMap((page) => page.nodes) ?? []
  const loadingChildren = childQuery.isLoading || childQuery.isFetching
  const indent = Math.min(depth * 16, 96)

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <div
        className="group flex min-w-0 items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted/60"
        style={{ paddingLeft: `${8 + indent}px` }}
      >
        {node.has_children ? (
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="h-6 w-6 shrink-0 px-0">
              {open ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              <span className="sr-only">
                {open
                  ? t('hierarchy.collapseNode', 'Collapse node')
                  : t('hierarchy.expandNode', 'Expand node')}
              </span>
            </Button>
          </CollapsibleTrigger>
        ) : (
          <span className="h-6 w-6 shrink-0" />
        )}

        <div className="min-w-0 flex-1">
          <div className="truncate font-medium">{node.label}</div>
          {node.path && depth === 0 && (
            <div className="truncate text-xs text-muted-foreground">{node.path}</div>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {node.rank && <Badge variant="outline">{node.rank}</Badge>}
          {node.child_count > 0 && (
            <span className="text-xs text-muted-foreground">
              {t('hierarchy.childCount', '{{count}} children', {
                count: node.child_count,
              })}
            </span>
          )}
        </div>
      </div>

      <CollapsibleContent>
        {loadingChildren && (
          <div
            className="flex items-center gap-2 py-2 text-xs text-muted-foreground"
            style={{ paddingLeft: `${40 + indent}px` }}
          >
            <Loader2 className="h-3 w-3 animate-spin" />
            {t('hierarchy.loadingChildren', 'Loading children')}
          </div>
        )}
        {childQuery.error && (
          <div
            className="flex items-center gap-2 py-2 text-xs text-destructive"
            style={{ paddingLeft: `${40 + indent}px` }}
          >
            <AlertTriangle className="h-3 w-3" />
            {t('hierarchy.childrenError', 'Could not load children')}
          </div>
        )}
        {childNodes.map((child) => (
          <HierarchyTreeNode
            key={nodeKey(child)}
            referenceName={referenceName}
            node={child}
            depth={depth + 1}
          />
        ))}
        {childQuery.hasNextPage && (
          <div style={{ paddingLeft: `${40 + indent}px` }}>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mt-1"
              onClick={() => void childQuery.fetchNextPage()}
              disabled={childQuery.isFetchingNextPage}
            >
              {childQuery.isFetchingNextPage && (
                <Loader2 className="h-3 w-3 animate-spin" />
              )}
              {childQuery.isFetchingNextPage
                ? t('hierarchy.loadingMore', 'Loading more')
                : t('hierarchy.loadMoreChildren', 'Load more children')}
            </Button>
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}

export function HierarchyTree({
  referenceName,
  nodes,
  searchMode = false,
}: HierarchyTreeProps) {
  if (searchMode) {
    return (
      <div className="space-y-2">
        {nodes.map((node) => (
          <SearchResultRow key={nodeKey(node)} node={node} />
        ))}
      </div>
    )
  }

  return (
    <div className="rounded-md border py-1">
      {nodes.map((node) => (
        <HierarchyTreeNode
          key={nodeKey(node)}
          referenceName={referenceName}
          node={node}
        />
      ))}
    </div>
  )
}
