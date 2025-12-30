/**
 * DataDashboard - Global data quality and statistics dashboard
 *
 * Features:
 * - Summary statistics (entities, rows, quality score)
 * - Data completeness heatmap
 * - Spatial distribution map
 * - Taxonomy consistency view
 * - Value validation (outliers, ranges)
 * - Geographic coverage analysis
 */

import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Upload, Database, ArrowRight } from 'lucide-react'
import { ImportDashboard } from '@/components/sources/dashboard'
import { useDatasets } from '@/hooks/useDatasets'
import { useReferences } from '@/hooks/useReferences'

export function DataDashboard() {
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
    navigate(`/sources/reference/${refName}`)
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
            <CardTitle>Aucune donnee importee</CardTitle>
            <CardDescription>
              Commencez par importer vos fichiers de donnees pour voir les statistiques et la qualite.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={handleImport} size="lg" className="gap-2">
              <Upload className="h-4 w-4" />
              Importer des donnees
              <ArrowRight className="h-4 w-4" />
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard des donnees</h1>
          <p className="text-muted-foreground">
            Vue d'ensemble de la qualite et de la completude des donnees importees.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleImport}>
            <Upload className="mr-2 h-4 w-4" />
            Importer
          </Button>
        </div>
      </div>

      {/* Dashboard Content */}
      <ImportDashboard
        onExploreEntity={handleExploreEntity}
        onEnrich={handleEnrich}
        onReimport={handleImport}
      />
    </div>
  )
}
