import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  FileSpreadsheet,
  TreePine,
  MapPin,
  Map,
  ArrowRight,
  Database,
  BarChart3,
  CheckCircle
} from 'lucide-react'

import niamotoLogo from '@/assets/niamoto_logo.png'

export function Overview() {
  const { t } = useTranslation(['import', 'common'])
  return (
    <div className="space-y-8">
      {/* Welcome message */}
      <div className="text-center space-y-4">
        <img
          src={niamotoLogo}
          alt={t('common:app.logo')}
          className="w-32 h-32 mx-auto object-contain"
        />
        <h2 className="text-2xl font-bold">{t('overview.welcome')}</h2>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {t('overview.description')}
        </p>
      </div>

      {/* How it works */}
      <Card>
        <CardHeader>
          <CardTitle>{t('overview.howItWorks.title')}</CardTitle>
          <CardDescription>
            {t('overview.howItWorks.subtitle')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-5 gap-4 items-center">
            <div className="text-center space-y-2">
              <div className="bg-primary/10 w-20 h-20 rounded-full flex items-center justify-center mx-auto">
                <FileSpreadsheet className="w-10 h-10 text-primary" />
              </div>
              <div className="font-medium">{t('overview.howItWorks.occurrences')}</div>
              <div className="text-sm text-muted-foreground">{t('overview.howItWorks.occurrencesDesc')}</div>
            </div>

            <div className="hidden md:flex justify-center">
              <ArrowRight className="w-6 h-6 text-muted-foreground" />
            </div>

            <div className="text-center space-y-2">
              <div className="bg-green-100 dark:bg-green-900/20 w-20 h-20 rounded-full flex items-center justify-center mx-auto">
                <TreePine className="w-10 h-10 text-green-600" />
              </div>
              <div className="font-medium">{t('overview.howItWorks.taxonomy')}</div>
              <div className="text-sm text-muted-foreground">{t('overview.howItWorks.taxonomyDesc')}</div>
              <Badge variant="secondary" className="text-xs">{t('overview.howItWorks.automatic')}</Badge>
            </div>

            <div className="hidden md:flex justify-center">
              <ArrowRight className="w-6 h-6 text-muted-foreground" />
            </div>

            <div className="text-center space-y-2">
              <div className="bg-blue-100 dark:bg-blue-900/20 w-20 h-20 rounded-full flex items-center justify-center mx-auto">
                <MapPin className="w-10 h-10 text-blue-600" />
              </div>
              <div className="font-medium">{t('overview.howItWorks.aggregations')}</div>
              <div className="text-sm text-muted-foreground">{t('overview.howItWorks.aggregationsDesc')}</div>
            </div>
          </div>

          <Alert className="mt-6">
            <Database className="w-4 h-4" />
            <AlertDescription>
              <strong>{t('overview.keyPoint.title')}</strong> {t('overview.keyPoint.description')}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* Requirements */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              {t('overview.requirements.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-medium mb-2">{t('overview.requirements.occurrencesFile')}</h4>
              <ul className="space-y-1 text-sm text-muted-foreground ml-4">
                {t('overview.requirements.items', { returnObjects: true }).map((item: string, index: number) => (
                  <li key={index}>• {item}</li>
                ))}
              </ul>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-blue-600" />
              {t('overview.aggregationOptions.title')}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <MapPin className="w-4 h-4" />
                {t('overview.aggregationOptions.plots.title')}
              </h4>
              <p className="text-sm text-muted-foreground ml-5">
                {t('overview.aggregationOptions.plots.description')}
              </p>
            </div>
            <div>
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <Map className="w-4 h-4" />
                {t('overview.aggregationOptions.shapes.title')}
              </h4>
              <p className="text-sm text-muted-foreground ml-5">
                {t('overview.aggregationOptions.shapes.description')}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Process summary */}
      <Card className="border-primary/50">
        <CardHeader>
          <CardTitle>{t('overview.process.title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-none">
                <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-medium">
                  1
                </div>
              </div>
              <div className="flex-1">
                <h4 className="font-medium">{t('overview.process.step1.title')}</h4>
                <p className="text-sm text-muted-foreground">
                  {t('overview.process.step1.description')}
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-none">
                <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-medium">
                  2
                </div>
              </div>
              <div className="flex-1">
                <h4 className="font-medium">{t('overview.process.step2.title')}</h4>
                <p className="text-sm text-muted-foreground">
                  {t('overview.process.step2.description')}
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <div className="flex-none">
                <div className="w-8 h-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm font-medium">
                  3
                </div>
              </div>
              <div className="flex-1">
                <h4 className="font-medium">{t('overview.process.step3.title')}</h4>
                <p className="text-sm text-muted-foreground">
                  {t('overview.process.step3.description')}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
