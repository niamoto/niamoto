/**
 * LayoutSidebar - Navigation widget preview in sidebar
 *
 * Shows a preview of the hierarchical navigation widget
 * that will appear in the sidebar of the exported page.
 */
import { useMemo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Navigation, List } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { PreviewPane } from '@/components/preview'
import type { PreviewDescriptor } from '@/lib/preview/types'
import { invalidateAllPreviews } from '@/lib/preview/usePreviewFrame'
import type { NavigationWidgetInfo } from './types'

interface LayoutSidebarProps {
  groupBy: string
  navigationWidget: NavigationWidgetInfo
}

export function LayoutSidebar({ groupBy, navigationWidget }: LayoutSidebarProps) {
  const { t } = useTranslation('common')
  const queryClient = useQueryClient()

  // Get referential data from params
  const referential = navigationWidget.params?.referential_data as string || groupBy

  const descriptor: PreviewDescriptor = useMemo(() => ({
    templateId: `${referential}_hierarchical_nav_widget`,
    groupBy,
    mode: 'full' as const,
  }), [referential, groupBy])

  const handleRefresh = useCallback(() => {
    invalidateAllPreviews(queryClient)
  }, [queryClient])

  return (
    <div className="h-full flex flex-col rounded-lg border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 bg-muted/50 border-b shrink-0">
        {navigationWidget.is_hierarchical ? (
          <Navigation className="h-4 w-4 text-muted-foreground" />
        ) : (
          <List className="h-4 w-4 text-muted-foreground" />
        )}

        <span className="flex-1 font-medium text-sm truncate">
          {navigationWidget.title}
        </span>

        <Badge variant="outline" className="text-xs shrink-0">
          {navigationWidget.is_hierarchical ? t('display.hierarchical') : t('display.list')}
        </Badge>

        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={handleRefresh}
        >
          <RefreshCw className="h-4 w-4 text-muted-foreground" />
        </Button>
      </div>

      {/* Preview */}
      <div className="relative flex-1 min-h-0 bg-background">
        <PreviewPane descriptor={descriptor} className="w-full h-full" />
      </div>

      {/* Info footer */}
      <div className="px-3 py-2 border-t bg-muted/30 shrink-0">
        <p className="text-xs text-muted-foreground">
          Reference: <code className="font-mono">{referential}</code>
        </p>
      </div>
    </div>
  )
}
