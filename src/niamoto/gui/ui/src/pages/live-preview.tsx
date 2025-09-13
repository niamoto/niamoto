import { useTranslation } from 'react-i18next'
import { Eye, ExternalLink, RefreshCw, Smartphone, Tablet, Monitor } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export function LivePreview() {
  const { t } = useTranslation()

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {t('live_preview.title', 'Live Preview')}
          </h1>
          <p className="text-muted-foreground">
            {t('live_preview.description', 'Preview your exported site in real-time')}
          </p>
        </div>
        <Badge variant="secondary">
          {t('common.coming_soon', 'Coming Soon')}
        </Badge>
      </div>

      {/* Preview Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              <CardTitle>{t('live_preview.preview_panel', 'Preview Panel')}</CardTitle>
            </div>
            <div className="flex gap-2">
              <Button variant="ghost" size="icon">
                <Smartphone className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon">
                <Tablet className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon">
                <Monitor className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm">
                <RefreshCw className="mr-2 h-4 w-4" />
                {t('common.refresh', 'Refresh')}
              </Button>
              <Button variant="outline" size="sm">
                <ExternalLink className="mr-2 h-4 w-4" />
                {t('live_preview.open_new', 'Open in New Tab')}
              </Button>
            </div>
          </div>
          <CardDescription>
            {t('live_preview.preview_description', 'Real-time preview of your static site export')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="aspect-video rounded-lg border bg-muted flex items-center justify-center">
            <div className="text-center space-y-4">
              <Eye className="h-16 w-16 text-muted-foreground mx-auto" />
              <div>
                <p className="text-lg font-medium">
                  {t('live_preview.not_available', 'Preview Not Available')}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  {t('live_preview.export_first', 'Export your site first to see a live preview')}
                </p>
              </div>
              <Button>
                {t('live_preview.go_to_export', 'Go to Export')}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Info Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {t('live_preview.auto_refresh', 'Auto-Refresh')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {t('live_preview.auto_refresh_desc', 'Preview updates automatically when you make changes')}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {t('live_preview.responsive', 'Responsive Testing')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {t('live_preview.responsive_desc', 'Test your site on different device sizes')}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              {t('live_preview.hot_reload', 'Hot Reload')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {t('live_preview.hot_reload_desc', 'Changes apply instantly without page refresh')}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
