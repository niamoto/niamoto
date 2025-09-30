import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Eye, ExternalLink, RefreshCw, Smartphone, Tablet, Monitor, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

type ViewportSize = 'mobile' | 'tablet' | 'desktop'

export function LivePreview() {
  const { t } = useTranslation()
  const [viewportSize, setViewportSize] = useState<ViewportSize>('desktop')
  const [iframeKey, setIframeKey] = useState(0)
  const [siteExists, setSiteExists] = useState(true)

  const handleRefresh = () => {
    setIframeKey(prev => prev + 1)
  }

  const handleOpenNewTab = () => {
    window.open('/preview/index.html', '_blank')
  }

  const getIframeWidth = () => {
    switch (viewportSize) {
      case 'mobile':
        return '375px'
      case 'tablet':
        return '768px'
      case 'desktop':
        return '100%'
    }
  }

  const handleIframeError = () => {
    setSiteExists(false)
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {t('live_preview.title', 'Aperçu du site')}
          </h1>
          <p className="text-muted-foreground">
            {t('live_preview.description', 'Prévisualisation en temps réel de votre site exporté')}
          </p>
        </div>
      </div>

      {/* Preview Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              <CardTitle>{t('live_preview.preview_panel', 'Panneau d\'aperçu')}</CardTitle>
            </div>
            <div className="flex gap-2">
              <Button
                variant={viewportSize === 'mobile' ? 'default' : 'ghost'}
                size="icon"
                onClick={() => setViewportSize('mobile')}
                title="Mobile (375px)"
              >
                <Smartphone className="h-4 w-4" />
              </Button>
              <Button
                variant={viewportSize === 'tablet' ? 'default' : 'ghost'}
                size="icon"
                onClick={() => setViewportSize('tablet')}
                title="Tablet (768px)"
              >
                <Tablet className="h-4 w-4" />
              </Button>
              <Button
                variant={viewportSize === 'desktop' ? 'default' : 'ghost'}
                size="icon"
                onClick={() => setViewportSize('desktop')}
                title="Desktop (100%)"
              >
                <Monitor className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={handleRefresh}>
                <RefreshCw className="mr-2 h-4 w-4" />
                {t('common.refresh', 'Actualiser')}
              </Button>
              <Button variant="outline" size="sm" onClick={handleOpenNewTab}>
                <ExternalLink className="mr-2 h-4 w-4" />
                {t('live_preview.open_new', 'Ouvrir dans un nouvel onglet')}
              </Button>
            </div>
          </div>
          <CardDescription>
            {t('live_preview.preview_description', 'Aperçu en temps réel de votre site statique exporté')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!siteExists ? (
            <div className="aspect-video rounded-lg border bg-muted flex items-center justify-center">
              <div className="text-center space-y-4">
                <AlertCircle className="h-16 w-16 text-muted-foreground mx-auto" />
                <div>
                  <p className="text-lg font-medium">
                    {t('live_preview.not_available', 'Aperçu non disponible')}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    {t('live_preview.export_first', 'Exportez votre site d\'abord pour voir un aperçu')}
                  </p>
                </div>
                <Button onClick={() => window.location.href = '/showcase'}>
                  {t('live_preview.go_to_export', 'Aller à la section Export')}
                </Button>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border overflow-hidden bg-muted/50 flex justify-center">
              <div style={{ width: getIframeWidth(), transition: 'width 0.3s ease' }}>
                <iframe
                  key={iframeKey}
                  src="/preview/index.html"
                  className="w-full h-[700px] border-0 bg-white"
                  title="Site exporté"
                  sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
                  onError={handleIframeError}
                />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              <RefreshCw className="h-4 w-4 inline mr-2" />
              {t('live_preview.auto_refresh', 'Actualisation')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {t('live_preview.auto_refresh_desc', 'Utilisez le bouton actualiser pour recharger l\'aperçu après un nouvel export')}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              <Smartphone className="h-4 w-4 inline mr-2" />
              {t('live_preview.responsive', 'Test responsive')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {t('live_preview.responsive_desc', 'Testez votre site sur différentes tailles d\'écran (mobile, tablette, desktop)')}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              <ExternalLink className="h-4 w-4 inline mr-2" />
              {t('live_preview.external', 'Ouverture externe')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {t('live_preview.external_desc', 'Ouvrez le site dans un nouvel onglet pour une navigation complète')}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
