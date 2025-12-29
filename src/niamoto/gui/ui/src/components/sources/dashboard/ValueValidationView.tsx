/**
 * ValueValidationView - Numeric column validation with outlier detection
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  AlertTriangle,
  BarChart3,
  ChevronDown,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  HelpCircle,
  Info,
} from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface EntityInfo {
  name: string
  entity_type: string
  row_count: number
  column_count: number
  columns: string[]
  quality_score: number
}

interface ColumnValidation {
  column: string
  min_value: number | null
  max_value: number | null
  mean_value: number | null
  median_value: number | null
  std_dev: number | null
  outlier_count: number
  outliers: Array<Record<string, any>>
}

interface EntityValidation {
  entity: string
  columns: ColumnValidation[]
}

interface ValueValidationViewProps {
  entities: EntityInfo[]
}

// Method explanations for documentation
const METHOD_INFO = {
  iqr: {
    name: 'IQR (Interquartile Range)',
    shortName: 'IQR (1.5x)',
    formula: 'Q1 - 1.5×IQR à Q3 + 1.5×IQR',
    description: 'Méthode robuste basée sur les quartiles. Identifie les valeurs en dehors de la zone "normale" définie par l\'écart interquartile.',
    details: 'Q1 = 25e percentile, Q3 = 75e percentile, IQR = Q3 - Q1. Une valeur est considérée outlier si elle est < Q1 - 1.5×IQR ou > Q3 + 1.5×IQR.',
    bestFor: 'Données asymétriques ou avec des distributions non-normales. Standard en statistiques exploratoires.',
    sensitivity: 'Modérée - détecte les valeurs vraiment extrêmes',
  },
  zscore: {
    name: 'Z-Score (Écart-type)',
    shortName: 'Z-Score (3σ)',
    formula: 'μ ± 3σ',
    description: 'Mesure à combien d\'écarts-types une valeur se trouve de la moyenne. Suppose une distribution normale.',
    details: 'Z = (valeur - moyenne) / écart-type. Une valeur avec |Z| > 3 est considérée outlier (> 3 écarts-types de la moyenne).',
    bestFor: 'Données suivant une distribution normale (gaussienne). Mesures physiques, tailles, poids.',
    sensitivity: 'Faible - ne détecte que les valeurs très extrêmes',
  },
  percentile: {
    name: 'Percentile (1% - 99%)',
    shortName: 'Percentile',
    formula: '< P1 ou > P99',
    description: 'Identifie simplement les 1% de valeurs les plus basses et les 1% les plus hautes.',
    details: 'Toute valeur en dessous du 1er percentile ou au-dessus du 99e percentile est un outlier. Simple et intuitif.',
    bestFor: 'Quand vous voulez identifier un pourcentage fixe de valeurs extrêmes, quelle que soit la distribution.',
    sensitivity: 'Fixe - détecte toujours exactement 2% des données (si elles existent)',
  },
}

export function ValueValidationView({ entities }: ValueValidationViewProps) {
  const [selectedEntity, setSelectedEntity] = useState<string>(
    entities[0]?.name || ''
  )
  const [validation, setValidation] = useState<EntityValidation | null>(null)
  const [loading, setLoading] = useState(false)
  const [method, setMethod] = useState<'iqr' | 'zscore' | 'percentile'>('iqr')
  const [threshold] = useState(1.5)
  const [expandedColumn, setExpandedColumn] = useState<string | null>(null)
  const [showHelp, setShowHelp] = useState(false)

  useEffect(() => {
    if (!selectedEntity) return

    const fetchValidation = async () => {
      setLoading(true)
      try {
        const params = new URLSearchParams({
          method,
          threshold: threshold.toString(),
        })
        const response = await fetch(
          `/api/stats/value-validation/${selectedEntity}?${params}`
        )
        if (response.ok) {
          const data = await response.json()
          setValidation(data)
        }
      } catch (err) {
        console.error('Failed to fetch validation:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchValidation()
  }, [selectedEntity, method, threshold])

  const totalOutliers = validation?.columns.reduce(
    (sum, col) => sum + col.outlier_count,
    0
  ) || 0

  const formatNumber = (value: number | null) => {
    if (value === null) return '-'
    if (Math.abs(value) < 0.01 || Math.abs(value) >= 10000) {
      return value.toExponential(2)
    }
    return value.toFixed(2)
  }

  const currentMethodInfo = METHOD_INFO[method]

  return (
    <TooltipProvider>
      <div className="space-y-4">
        {/* Help Card - What are outliers? */}
        <Collapsible open={showHelp} onOpenChange={setShowHelp}>
          <CollapsibleTrigger asChild>
            <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
              <HelpCircle className="h-4 w-4" />
              <span>{showHelp ? 'Masquer l\'aide' : 'Qu\'est-ce qu\'un outlier ?'}</span>
              <ChevronDown className={`h-4 w-4 transition-transform ${showHelp ? 'rotate-180' : ''}`} />
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <Card className="mt-2 bg-blue-50/50 border-blue-200">
              <CardContent className="pt-4">
                <div className="space-y-3 text-sm">
                  <div>
                    <h4 className="font-medium flex items-center gap-2">
                      <Info className="h-4 w-4 text-blue-600" />
                      Qu'est-ce qu'un outlier (valeur aberrante) ?
                    </h4>
                    <p className="text-muted-foreground mt-1">
                      Un <strong>outlier</strong> est une valeur qui s'écarte significativement des autres observations.
                      Ces valeurs peuvent indiquer des erreurs de saisie, des cas exceptionnels intéressants,
                      ou des problèmes dans les données.
                    </p>
                  </div>

                  <div className="grid md:grid-cols-3 gap-3 mt-4">
                    {Object.entries(METHOD_INFO).map(([key, info]) => (
                      <div
                        key={key}
                        className={`p-3 rounded-lg border ${
                          method === key ? 'border-blue-400 bg-blue-100/50' : 'border-gray-200 bg-white'
                        }`}
                      >
                        <h5 className="font-medium text-xs">{info.name}</h5>
                        <p className="text-xs text-muted-foreground mt-1">{info.description}</p>
                        <div className="mt-2 text-xs">
                          <span className="font-mono bg-muted px-1 rounded">{info.formula}</span>
                        </div>
                        <p className="text-xs text-blue-600 mt-2">{info.sensitivity}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </CollapsibleContent>
        </Collapsible>

        {/* Controls */}
        <div className="flex items-center gap-4 flex-wrap">
          <Select value={selectedEntity} onValueChange={setSelectedEntity}>
            <SelectTrigger className="w-64">
              <SelectValue placeholder="Sélectionner une entité" />
            </SelectTrigger>
            <SelectContent>
              {entities.map((e) => (
                <SelectItem key={e.name} value={e.name}>
                  {e.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="flex items-center gap-1">
            <Select value={method} onValueChange={(v) => setMethod(v as 'iqr' | 'zscore' | 'percentile')}>
              <SelectTrigger className="w-44">
                <SelectValue placeholder="Méthode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="iqr">
                  <span className="flex items-center gap-2">
                    IQR (1.5x)
                  </span>
                </SelectItem>
                <SelectItem value="zscore">
                  <span className="flex items-center gap-2">
                    Z-Score (3σ)
                  </span>
                </SelectItem>
                <SelectItem value="percentile">
                  <span className="flex items-center gap-2">
                    Percentile
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>

            <Tooltip>
              <TooltipTrigger asChild>
                <button className="p-1 hover:bg-accent rounded">
                  <HelpCircle className="h-4 w-4 text-muted-foreground" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-xs">
                <div className="text-xs">
                  <p className="font-medium">{currentMethodInfo.name}</p>
                  <p className="mt-1">{currentMethodInfo.details}</p>
                  <p className="mt-1 text-blue-400">{currentMethodInfo.bestFor}</p>
                </div>
              </TooltipContent>
            </Tooltip>
          </div>

          {totalOutliers > 0 ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge variant="outline" className="text-yellow-700 border-yellow-300 cursor-help">
                  <AlertTriangle className="mr-1 h-3 w-3" />
                  {totalOutliers} outliers détectés
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-xs">Valeurs hors limites selon la méthode {currentMethodInfo.shortName}</p>
              </TooltipContent>
            </Tooltip>
          ) : (
            validation && (
              <Badge variant="outline" className="text-green-700 border-green-300">
                <CheckCircle2 className="mr-1 h-3 w-3" />
                Aucun outlier
              </Badge>
            )
          )}
        </div>

        {/* Current method summary */}
        <div className="text-xs bg-muted/50 rounded-lg p-3 flex items-start gap-2">
          <Info className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
          <div>
            <span className="font-medium">{currentMethodInfo.name} :</span>{' '}
            <span className="text-muted-foreground">{currentMethodInfo.description}</span>
            <span className="block mt-1 font-mono text-blue-600">{currentMethodInfo.formula}</span>
          </div>
        </div>

      {/* Validation results */}
      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : validation && validation.columns.length > 0 ? (
        <div className="space-y-3">
          {validation.columns.map((col) => (
            <Card key={col.column} className={col.outlier_count > 0 ? 'border-yellow-300' : ''}>
              <Collapsible
                open={expandedColumn === col.column}
                onOpenChange={(open) => setExpandedColumn(open ? col.column : null)}
              >
                <CardHeader className="py-3">
                  <CollapsibleTrigger asChild>
                    <div className="flex items-center justify-between cursor-pointer hover:bg-accent/50 -mx-4 -my-2 px-4 py-2 rounded">
                      <div className="flex items-center gap-3">
                        <BarChart3 className="h-4 w-4 text-blue-500" />
                        <CardTitle className="text-sm font-medium">
                          {col.column}
                        </CardTitle>
                        {col.outlier_count > 0 && (
                          <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                            {col.outlier_count} outliers
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-xs text-muted-foreground flex gap-4">
                          <span className="flex items-center gap-1">
                            <TrendingDown className="h-3 w-3" />
                            {formatNumber(col.min_value)}
                          </span>
                          <span>~{formatNumber(col.median_value)}</span>
                          <span className="flex items-center gap-1">
                            <TrendingUp className="h-3 w-3" />
                            {formatNumber(col.max_value)}
                          </span>
                        </div>
                        <ChevronDown
                          className={`h-4 w-4 transition-transform ${
                            expandedColumn === col.column ? 'rotate-180' : ''
                          }`}
                        />
                      </div>
                    </div>
                  </CollapsibleTrigger>
                </CardHeader>

                <CollapsibleContent>
                  <CardContent className="pt-0">
                    {/* Stats grid */}
                    <div className="grid grid-cols-5 gap-4 mb-4 text-sm">
                      <div className="text-center p-2 bg-muted rounded">
                        <p className="text-xs text-muted-foreground">Min</p>
                        <p className="font-mono font-medium">{formatNumber(col.min_value)}</p>
                      </div>
                      <div className="text-center p-2 bg-muted rounded">
                        <p className="text-xs text-muted-foreground">Max</p>
                        <p className="font-mono font-medium">{formatNumber(col.max_value)}</p>
                      </div>
                      <div className="text-center p-2 bg-muted rounded">
                        <p className="text-xs text-muted-foreground">Mean</p>
                        <p className="font-mono font-medium">{formatNumber(col.mean_value)}</p>
                      </div>
                      <div className="text-center p-2 bg-muted rounded">
                        <p className="text-xs text-muted-foreground">Median</p>
                        <p className="font-mono font-medium">{formatNumber(col.median_value)}</p>
                      </div>
                      <div className="text-center p-2 bg-muted rounded">
                        <p className="text-xs text-muted-foreground">Std Dev</p>
                        <p className="font-mono font-medium">{formatNumber(col.std_dev)}</p>
                      </div>
                    </div>

                    {/* Range visualization */}
                    <div className="mb-4">
                      <div className="h-4 bg-muted rounded-full overflow-hidden relative">
                        {col.min_value !== null && col.max_value !== null && col.median_value !== null && (
                          <>
                            {/* Range bar */}
                            <div className="absolute inset-0 bg-gradient-to-r from-blue-200 via-blue-400 to-blue-200" />
                            {/* Median marker */}
                            <div
                              className="absolute top-0 bottom-0 w-0.5 bg-blue-800"
                              style={{
                                left: `${((col.median_value - col.min_value) / (col.max_value - col.min_value)) * 100}%`,
                              }}
                            />
                          </>
                        )}
                      </div>
                    </div>

                    {/* Outliers table */}
                    {col.outliers.length > 0 && (
                      <div>
                        <p className="text-xs font-medium mb-2">Sample outliers:</p>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              {Object.keys(col.outliers[0]).slice(0, 5).map((key) => (
                                <TableHead key={key} className="text-xs">
                                  {key}
                                </TableHead>
                              ))}
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {col.outliers.slice(0, 3).map((outlier, idx) => (
                              <TableRow key={idx}>
                                {Object.entries(outlier).slice(0, 5).map(([key, value]) => (
                                  <TableCell key={key} className="text-xs font-mono">
                                    {typeof value === 'number'
                                      ? formatNumber(value)
                                      : String(value).slice(0, 20)}
                                  </TableCell>
                                ))}
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </div>
                    )}
                  </CardContent>
                </CollapsibleContent>
              </Collapsible>
            </Card>
          ))}
        </div>
      ) : validation ? (
        <Alert>
          <BarChart3 className="h-4 w-4" />
          <AlertDescription>
            No numeric columns found in this entity for validation.
          </AlertDescription>
        </Alert>
      ) : null}
      </div>
    </TooltipProvider>
  )
}
