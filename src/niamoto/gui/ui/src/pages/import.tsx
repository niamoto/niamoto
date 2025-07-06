import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import {
  Upload,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ChevronRight,
  RefreshCw,
  FileSpreadsheet,
  Trees,
  MapPin,
  Map,
  PlayCircle,
  Info
} from 'lucide-react'
import { ImportWizard, type ImportConfig, type ImportType } from '@/components/import-wizard/ImportWizard'
import { useImportStatus } from '@/hooks/useImportStatus'
import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface ImportTypeInfo {
  type: ImportType
  title: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  fileHint: string
}

const importTypes: ImportTypeInfo[] = [
  {
    type: 'taxonomy',
    title: 'Taxonomy',
    description: 'Import species classification data',
    icon: Trees,
    fileHint: 'CSV file with taxon hierarchy'
  },
  {
    type: 'occurrences',
    title: 'Occurrences',
    description: 'Import species occurrence records',
    icon: MapPin,
    fileHint: 'CSV file with occurrence data'
  },
  {
    type: 'plots',
    title: 'Plots',
    description: 'Import plot and survey data',
    icon: Map,
    fileHint: 'GeoPackage or CSV file'
  },
  {
    type: 'shapes',
    title: 'Shapes',
    description: 'Import geographic boundaries',
    icon: FileSpreadsheet,
    fileHint: 'Shapefile or GeoJSON - Multiple shape types can be imported'
  }
]

export function ImportPage() {
  const [selectedType, setSelectedType] = useState<ImportType | null>(null)
  const [showWizard, setShowWizard] = useState(false)
  const { status, loading, error, refetch } = useImportStatus()

  const handleImportClick = (type: ImportType) => {
    // Check dependencies
    if (status) {
      const typeStatus = status[type]
      if (!typeStatus.dependencies_met) {
        return // Disabled due to missing dependencies
      }
    }

    setSelectedType(type)
    setShowWizard(true)
  }

  const handleImportComplete = async (config: ImportConfig) => {
    console.log('Import completed:', config)
    setShowWizard(false)
    setSelectedType(null)
    // Refresh status after import
    setTimeout(refetch, 2000)
    // Also refresh again after a bit more time in case the import is still processing
    setTimeout(refetch, 5000)
  }

  const handleImportCancel = () => {
    setShowWizard(false)
    setSelectedType(null)
  }

  const getStatusBadge = (type: ImportType) => {
    if (!status) return null

    const typeStatus = status[type]

    if (typeStatus.is_imported) {
      const label = type === 'shapes'
        ? `${typeStatus.row_count.toLocaleString()} shapes`
        : `${typeStatus.row_count.toLocaleString()} records`

      return (
        <Badge variant="success" className="gap-1">
          <CheckCircle2 className="h-3 w-3" />
          {label}
        </Badge>
      )
    }

    if (!typeStatus.dependencies_met) {
      return (
        <Badge variant="destructive" className="gap-1">
          <XCircle className="h-3 w-3" />
          Requires {typeStatus.missing_dependencies.join(', ')}
        </Badge>
      )
    }

    return (
      <Badge variant="secondary" className="gap-1">
        <AlertCircle className="h-3 w-3" />
        Not imported
      </Badge>
    )
  }

  const canImport = (type: ImportType): boolean => {
    if (!status) return false
    return status[type].dependencies_met
  }

  const showImportOrder = status && !status.taxonomy.is_imported

  if (showWizard && selectedType) {
    return (
      <div className="h-full">
        <ImportWizard
          initialType={selectedType}
          onComplete={handleImportComplete}
          onCancel={handleImportCancel}
        />
      </div>
    )
  }

  return (
    <div className="container max-w-6xl py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight mb-2">Import Data</h1>
        <p className="text-muted-foreground">
          Import your ecological data into Niamoto. Follow the recommended order for best results.
        </p>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {showImportOrder && (
        <Alert className="mb-6">
          <Info className="h-4 w-4" />
          <AlertTitle>Import Order</AlertTitle>
          <AlertDescription>
            For best results, import data in this order: Taxonomy → Occurrences → Plots → Shapes.
            Some imports depend on others being completed first.
          </AlertDescription>
        </Alert>
      )}

      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">Import Types</h2>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={refetch}
            disabled={loading}
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", loading && "animate-spin")} />
            Refresh Status
          </Button>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="default"
                  size="sm"
                  disabled={!status || status.taxonomy.is_imported}
                >
                  <PlayCircle className="h-4 w-4 mr-2" />
                  Import All
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Import all data in the correct order automatically</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {importTypes.map((importType, index) => {
          const Icon = importType.icon
          const isDisabled = !canImport(importType.type)
          const typeStatus = status?.[importType.type]

          return (
            <Card
              key={importType.type}
              className={cn(
                "relative overflow-hidden transition-all",
                isDisabled && "opacity-60"
              )}
            >
              {index === 0 && showImportOrder && (
                <div className="absolute top-2 right-2">
                  <Badge variant="outline" className="text-xs">Start here</Badge>
                </div>
              )}

              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "p-2 rounded-lg",
                      typeStatus?.is_imported ? "bg-green-100 text-green-600" : "bg-muted"
                    )}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">{importType.title}</CardTitle>
                      <CardDescription className="mt-1">
                        {importType.description}
                      </CardDescription>
                    </div>
                  </div>
                  <div className="ml-4">
                    {getStatusBadge(importType.type)}
                  </div>
                </div>
              </CardHeader>

              <CardContent>
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    {importType.fileHint}
                  </p>

                  {typeStatus && !typeStatus.dependencies_met && (
                    <Alert variant="destructive" className="py-2">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription className="ml-2">
                        Import {typeStatus.missing_dependencies.join(' and ')} first
                      </AlertDescription>
                    </Alert>
                  )}

                  <Button
                    className="w-full"
                    variant={typeStatus?.is_imported ? "secondary" : "default"}
                    disabled={isDisabled || loading}
                    onClick={() => handleImportClick(importType.type)}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    {typeStatus?.is_imported
                      ? (importType.type === 'shapes' ? 'Add more' : 'Re-import')
                      : 'Import'} {importType.title}
                    {!isDisabled && <ChevronRight className="h-4 w-4 ml-auto" />}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Separator className="my-8" />

      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Import Progress</h3>
        <div className="space-y-3">
          {importTypes.map((importType) => {
            const typeStatus = status?.[importType.type]
            const progress = typeStatus?.is_imported ? 100 : 0

            return (
              <div key={importType.type} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{importType.title}</span>
                  <span className="text-muted-foreground">
                    {typeStatus?.is_imported ? 'Complete' : 'Pending'}
                  </span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
