/**
 * DataDashboard - Global data exploration and diagnostics dashboard
 *
 * Features:
 * - Summary statistics (entities, rows, exploration signals)
 * - Field availability heatmap
 * - Spatial distribution map
 * - Taxonomy consistency view
 * - Value validation (outliers, ranges)
 * - Geographic coverage analysis
 */

import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Upload, Database, ArrowRight } from 'lucide-react'
import { ImportDashboard } from '@/components/sources/dashboard'
import { useDatasets } from '@/hooks/useDatasets'
import { useReferences } from '@/hooks/useReferences'

export function DataDashboard() {
  const { t } = useTranslation(['sources', 'common'])
  const navigate = useNavigate()
  const { data: datasetsData } = useDatasets()
  const { data: referencesData } = useReferences()

  const datasets = datasetsData?.datasets ?? []
  const references = referencesData?.references ?? []
  const hasData = datasets.length > 0 || references.length > 0

  const handleExploreEntity = (name: string) => {
    navigate(`/sources/dataset/${name}`)
  }

  const handleEnrich = (refName: string) => {
    navigate(`/sources/reference/${encodeURIComponent(refName)}?tab=enrichment`)
  }

  const handleOpenGroup = (groupName: string) => {
    navigate(`/groups/${encodeURIComponent(groupName)}`)
  }

  const handleImport = () => {
    navigate('/sources/import')
  }

  // Empty state when no data
  if (!hasData) {
    return (
      <div className="flex items-center justify-center h-full p-6">
        <Card className="max-w-md text-center">
          <CardHeader>
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-muted">
              <Database className="h-8 w-8 text-muted-foreground" />
            </div>
            <CardTitle>{t('dashboard.noData')}</CardTitle>
            <CardDescription>
              {t('dashboard.noDataHint')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={handleImport} size="lg" className="gap-2">
              <Upload className="h-4 w-4" />
              {t('dashboard.importData')}
              <ArrowRight className="h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6">
      <ImportDashboard
        onExploreEntity={handleExploreEntity}
        onExploreReference={handleEnrich}
        onOpenGroup={handleOpenGroup}
        onEnrich={handleEnrich}
        onReimport={handleImport}
      />
    </div>
  )
}
