/**
 * LayoutSidebar - Navigation widget preview in sidebar
 *
 * Shows a preview of the hierarchical navigation widget
 * that will appear in the sidebar of the exported page.
 */
import { useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, RefreshCw, Navigation, List } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { NavigationWidgetInfo } from './types'

interface LayoutSidebarProps {
  groupBy: string
  navigationWidget: NavigationWidgetInfo
}

export function LayoutSidebar({ groupBy, navigationWidget }: LayoutSidebarProps) {
  const { t } = useTranslation('common')
  const [isLoading, setIsLoading] = useState(true)
  const [iframeKey, setIframeKey] = useState(0)

  // Handle iframe load
  const handleIframeLoad = useCallback(() => {
    setIsLoading(false)
  }, [])

  // Handle refresh
  const handleRefresh = useCallback(() => {
    setIsLoading(true)
    setIframeKey((k) => k + 1)
  }, [])

  // Get referential data from params
  const referential = navigationWidget.params?.referential_data as string || groupBy

  // Preview URL - uses the navigation widget preview endpoint
  const previewUrl = `/api/templates/preview/${referential}_hierarchical_nav_widget`

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
          disabled={isLoading}
        >
          <RefreshCw
            className={cn(
              'h-4 w-4 text-muted-foreground',
              isLoading && 'animate-spin'
            )}
          />
        </Button>
      </div>

      {/* Preview iframe */}
      <div className="relative flex-1 min-h-0 bg-background">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-10">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}
        <iframe
          key={iframeKey}
          src={previewUrl}
          className="w-full h-full border-0"
          onLoad={handleIframeLoad}
          title={navigationWidget.title}
        />
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
