/**
 * ValueValidationView - Numeric column validation with outlier detection
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
  Download,
  Copy,
  ArrowUp,
  ArrowDown,
  Check,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
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

interface HistogramBin {
  bin_start: number
  bin_end: number
  count: number
  is_outlier_zone: boolean
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
  // Enhanced outlier data
  lower_bound: number | null
  upper_bound: number | null
  outliers_low_count: number
  outliers_high_count: number
  histogram: HistogramBin[] | null
}

interface EntityValidation {
  entity: string
  columns: ColumnValidation[]
}

interface ValueValidationViewProps {
  entities: EntityInfo[]
}

// Copy button component
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleCopy}
      className="h-8 w-8 p-0 shrink-0"
    >
      {copied ? (
        <Check className="h-3 w-3 text-green-500" />
      ) : (
        <Copy className="h-3 w-3" />
      )}
    </Button>
  )
}

// Method keys for translation lookup
const METHOD_KEYS = ['iqr', 'zscore', 'percentile'] as const

// Default thresholds per method
const DEFAULT_THRESHOLDS: Record<string, number> = {
  iqr: 1.5,      // 1.5 × IQR (moderate), 3 = extreme
  zscore: 3,     // 3 standard deviations (99.7% of data)
  percentile: 5, // Exclude bottom 5% and top 5%
}

// Threshold config per method
const THRESHOLD_CONFIG: Record<string, { min: number; max: number; step: number; unit: string }> = {
  iqr: { min: 1, max: 5, step: 0.5, unit: '×' },
  zscore: { min: 1, max: 5, step: 0.5, unit: 'σ' },
  percentile: { min: 1, max: 25, step: 1, unit: '%' },
}

export function ValueValidationView({ entities }: ValueValidationViewProps) {
  const { t } = useTranslation(['sources', 'common'])
  const [selectedEntity, setSelectedEntity] = useState<string>(
    entities[0]?.name || ''
  )
  const [validation, setValidation] = useState<EntityValidation | null>(null)
  const [loading, setLoading] = useState(false)
  const [method, setMethod] = useState<'iqr' | 'zscore' | 'percentile'>('iqr')
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLDS.iqr)
  const [expandedColumn, setExpandedColumn] = useState<string | null>(null)
  const [showHelp, setShowHelp] = useState(false)

  // Update threshold when method changes
  const handleMethodChange = (newMethod: 'iqr' | 'zscore' | 'percentile') => {
    setMethod(newMethod)
    setThreshold(DEFAULT_THRESHOLDS[newMethod])
  }

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

  return (
    <TooltipProvider>
      <div className="space-y-4">
        {/* Help Card - What are outliers? */}
        <Collapsible open={showHelp} onOpenChange={setShowHelp}>
          <CollapsibleTrigger asChild>
            <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
              <HelpCircle className="h-4 w-4" />
              <span>{showHelp ? t('validation.hideHelp') : t('validation.whatIsOutlier')}</span>
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
                      {t('validation.outlierTitle')}
                    </h4>
                    <p
                      className="text-muted-foreground mt-1"
                      dangerouslySetInnerHTML={{ __html: t('validation.outlierDescription') }}
                    />
                  </div>

                  <div className="grid md:grid-cols-3 gap-3 mt-4">
                    {METHOD_KEYS.map((key) => (
                      <div
                        key={key}
                        className={`p-3 rounded-lg border ${
                          method === key ? 'border-blue-400 bg-blue-100/50' : 'border-gray-200 bg-white'
                        }`}
                      >
                        <h5 className="font-medium text-xs">{t(`validation.methods.${key}.name`)}</h5>
                        <p className="text-xs text-muted-foreground mt-1">{t(`validation.methods.${key}.description`)}</p>
                        <div className="mt-2 text-xs">
                          <span className="font-mono bg-muted px-1 rounded">{t(`validation.methods.${key}.formula`)}</span>
                        </div>
                        <p className="text-xs text-blue-600 mt-2">{t(`validation.methods.${key}.sensitivity`)}</p>
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
              <SelectValue placeholder={t('common:placeholders.selectOption')} />
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
            <Select value={method} onValueChange={(v) => handleMethodChange(v as 'iqr' | 'zscore' | 'percentile')}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder={t('common:labels.type')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="iqr">IQR</SelectItem>
                <SelectItem value="zscore">Z-Score</SelectItem>
                <SelectItem value="percentile">Percentile</SelectItem>
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
                  <p className="font-medium">{t(`validation.methods.${method}.name`)}</p>
                  <p className="mt-1">{t(`validation.methods.${method}.details`)}</p>
                  <p className="mt-1 text-blue-400">{t(`validation.methods.${method}.bestFor`)}</p>
                </div>
              </TooltipContent>
            </Tooltip>
          </div>

          {/* Threshold control */}
          <div className="flex items-center gap-2">
            <Label htmlFor="threshold" className="text-sm text-muted-foreground whitespace-nowrap">
              {t('validation.threshold')}:
            </Label>
            <div className="flex items-center gap-1">
              <Input
                id="threshold"
                type="number"
                value={threshold}
                onChange={(e) => {
                  const val = parseFloat(e.target.value)
                  if (!isNaN(val)) {
                    const config = THRESHOLD_CONFIG[method]
                    setThreshold(Math.min(Math.max(val, config.min), config.max))
                  }
                }}
                min={THRESHOLD_CONFIG[method].min}
                max={THRESHOLD_CONFIG[method].max}
                step={THRESHOLD_CONFIG[method].step}
                className="w-20 h-8 text-sm"
              />
              <span className="text-sm text-muted-foreground">
                {THRESHOLD_CONFIG[method].unit}
              </span>
            </div>
            <Tooltip>
              <TooltipTrigger asChild>
                <button className="p-1 hover:bg-accent rounded">
                  <Info className="h-4 w-4 text-muted-foreground" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="max-w-xs">
                <div className="text-xs">
                  {method === 'iqr' && (
                    <p>{t('validation.thresholdHints.iqr')}</p>
                  )}
                  {method === 'zscore' && (
                    <p>{t('validation.thresholdHints.zscore')}</p>
                  )}
                  {method === 'percentile' && (
                    <p>{t('validation.thresholdHints.percentile')}</p>
                  )}
                </div>
              </TooltipContent>
            </Tooltip>
          </div>

          {totalOutliers > 0 ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge variant="outline" className="text-yellow-700 border-yellow-300 cursor-help">
                  <AlertTriangle className="mr-1 h-3 w-3" />
                  {t('validation.outliersDetected', { count: totalOutliers })}
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p className="text-xs">{t('validation.valuesOutOfBounds', { method: t(`validation.methods.${method}.shortName`) })}</p>
              </TooltipContent>
            </Tooltip>
          ) : (
            validation && (
              <Badge variant="outline" className="text-green-700 border-green-300">
                <CheckCircle2 className="mr-1 h-3 w-3" />
                {t('validation.noOutlier')}
              </Badge>
            )
          )}
        </div>

        {/* Current method summary */}
        <div className="text-xs bg-muted/50 rounded-lg p-3 flex items-start gap-2">
          <Info className="h-4 w-4 text-blue-500 mt-0.5 shrink-0" />
          <div>
            <span className="font-medium">{t(`validation.methods.${method}.name`)} :</span>{' '}
            <span className="text-muted-foreground">{t(`validation.methods.${method}.description`)}</span>
            <span className="block mt-1 font-mono text-blue-600">{t(`validation.methods.${method}.formula`)}</span>
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
                  <CardContent className="pt-0 space-y-4">
                    {/* Stats grid */}
                    <div className="grid grid-cols-5 gap-4 text-sm">
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

                    {/* Outlier bounds and distribution */}
                    {col.outlier_count > 0 && col.lower_bound !== null && col.upper_bound !== null && (
                      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 space-y-3">
                        {/* Bounds info */}
                        <div className="flex items-center justify-between">
                          <div className="text-sm">
                            <span className="text-muted-foreground">{t('validation.outlierBounds')}:</span>
                            <span className="ml-2 font-mono">
                              &lt; <span className="text-red-600 font-semibold">{formatNumber(col.lower_bound)}</span>
                              {' '}{t('common:labels.or')}{' '}
                              &gt; <span className="text-red-600 font-semibold">{formatNumber(col.upper_bound)}</span>
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-sm">
                            <span className="flex items-center gap-1 text-blue-600">
                              <ArrowDown className="h-3 w-3" />
                              {col.outliers_low_count} {t('validation.tooLow')}
                            </span>
                            <span className="flex items-center gap-1 text-red-600">
                              <ArrowUp className="h-3 w-3" />
                              {col.outliers_high_count} {t('validation.tooHigh')}
                            </span>
                          </div>
                        </div>

                        {/* Mini histogram */}
                        {col.histogram && col.histogram.length > 0 && (
                          <div className="space-y-1">
                            <p className="text-xs text-muted-foreground">{t('validation.distribution')}</p>
                            <div className="flex items-end gap-px h-12">
                              {col.histogram.map((bin, idx) => {
                                const maxCount = Math.max(...col.histogram!.map(b => b.count))
                                const height = maxCount > 0 ? (bin.count / maxCount) * 100 : 0
                                return (
                                  <Tooltip key={idx}>
                                    <TooltipTrigger asChild>
                                      <div
                                        className={`flex-1 rounded-t cursor-help transition-colors ${
                                          bin.is_outlier_zone
                                            ? 'bg-red-400 hover:bg-red-500'
                                            : 'bg-blue-400 hover:bg-blue-500'
                                        }`}
                                        style={{ height: `${Math.max(2, height)}%` }}
                                      />
                                    </TooltipTrigger>
                                    <TooltipContent>
                                      <p className="text-xs">
                                        {formatNumber(bin.bin_start)} - {formatNumber(bin.bin_end)}: {bin.count}
                                        {bin.is_outlier_zone && <span className="text-red-400 ml-1">(outlier)</span>}
                                      </p>
                                    </TooltipContent>
                                  </Tooltip>
                                )
                              })}
                            </div>
                            <div className="flex justify-between text-xs text-muted-foreground">
                              <span>{formatNumber(col.min_value)}</span>
                              <span>{formatNumber(col.max_value)}</span>
                            </div>
                          </div>
                        )}

                        {/* SQL query */}
                        <div className="space-y-1">
                          <p className="text-xs text-muted-foreground">{t('validation.sqlQuery')}</p>
                          <div className="flex items-center gap-2">
                            <code className="flex-1 text-xs bg-gray-800 text-green-400 p-2 rounded font-mono overflow-x-auto">
                              SELECT * FROM {selectedEntity} WHERE {col.column} &lt; {formatNumber(col.lower_bound)} OR {col.column} &gt; {formatNumber(col.upper_bound)}
                            </code>
                            <CopyButton
                              text={`SELECT * FROM ${selectedEntity} WHERE ${col.column} < ${col.lower_bound} OR ${col.column} > ${col.upper_bound}`}
                            />
                          </div>
                        </div>

                        {/* Action buttons */}
                        <div className="flex items-center gap-2 pt-1">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              const url = `/api/stats/value-validation/${selectedEntity}/export-outliers?column=${col.column}&method=${method}&threshold=${threshold}`
                              window.open(url, '_blank')
                            }}
                          >
                            <Download className="h-3 w-3 mr-1" />
                            {t('validation.exportCsv')} ({col.outlier_count})
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Outliers table */}
                    {col.outliers.length > 0 && (
                      <div>
                        <p className="text-xs font-medium mb-2">{t('validation.sampleOutliers')}:</p>
                        <Table>
                          <TableHeader>
                            <TableRow>
                              {Object.keys(col.outliers[0]).slice(0, 6).map((key, idx) => (
                                <TableHead
                                  key={key}
                                  className={`text-xs ${idx === 0 ? 'bg-yellow-100 font-semibold' : ''}`}
                                >
                                  {key}
                                  {idx === 0 && <span className="ml-1 text-yellow-600">★</span>}
                                </TableHead>
                              ))}
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {col.outliers.slice(0, 5).map((outlier, idx) => {
                              const value = outlier[col.column]
                              const isHigh = col.upper_bound !== null && value > col.upper_bound
                              return (
                                <TableRow key={idx}>
                                  {Object.entries(outlier).slice(0, 6).map(([key, val], colIdx) => (
                                    <TableCell
                                      key={key}
                                      className={`text-xs font-mono ${colIdx === 0 ? 'bg-yellow-50 font-semibold' : ''}`}
                                    >
                                      {colIdx === 0 ? (
                                        <span className="flex items-center gap-1">
                                          {isHigh ? (
                                            <ArrowUp className="h-3 w-3 text-red-500" />
                                          ) : (
                                            <ArrowDown className="h-3 w-3 text-blue-500" />
                                          )}
                                          <span className={isHigh ? 'text-red-600' : 'text-blue-600'}>
                                            {formatNumber(val as number)}
                                          </span>
                                        </span>
                                      ) : (
                                        typeof val === 'number'
                                          ? formatNumber(val)
                                          : val === null
                                            ? <span className="text-muted-foreground">null</span>
                                            : String(val).slice(0, 25)
                                      )}
                                    </TableCell>
                                  ))}
                                </TableRow>
                              )
                            })}
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
