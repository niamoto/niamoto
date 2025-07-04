import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  FileText,
  Database,
  Settings2,
  AlertCircle,
  CheckCircle2,
  Download,
  Eye,
  Loader2
} from 'lucide-react'
import axios from 'axios'
import type { ImportConfig } from './ImportWizard'

interface ReviewImportProps {
  config: ImportConfig
  onImport: () => void
}

interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
  summary: Record<string, any>
}

interface ImportJob {
  id: string
  status: string
  progress: number
  total_records: number
  processed_records: number
  errors: string[]
  warnings: string[]
}

export function ReviewImport({ config, onImport }: ReviewImportProps) {
  const [isValidating, setIsValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [isImporting, setIsImporting] = useState(false)
  const [importJobId, setImportJobId] = useState<string | null>(null)
  const [importJob, setImportJob] = useState<ImportJob | null>(null)
  const [importStatus, setImportStatus] = useState<'idle' | 'validating' | 'importing' | 'success' | 'error'>('idle')
  const [importMessage, setImportMessage] = useState('')

  const validateImport = useCallback(async () => {
    if (!config.file) return

    setIsValidating(true)
    setImportStatus('validating')

    try {
      const formData = new FormData()
      formData.append('file', config.file)
      formData.append('import_type', config.importType)
      formData.append('file_name', config.file.name)
      formData.append('field_mappings', JSON.stringify(config.fieldMappings || {}))
      formData.append('advanced_options', JSON.stringify(config.advancedOptions?.[config.importType] || {}))

      const response = await axios.post('/api/imports/validate', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      setValidationResult(response.data)
      setImportStatus('idle')
    } catch (error) {
      setImportStatus('error')
      setImportMessage('Validation failed')
      console.error('Validation error:', error)
    } finally {
      setIsValidating(false)
    }
  }, [config])

  // Validate on mount
  useEffect(() => {
    validateImport()
  }, [validateImport])

  // Poll import job status
  useEffect(() => {
    if (!importJobId || importStatus !== 'importing') return

    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`/api/imports/jobs/${importJobId}`)
        const job = response.data
        setImportJob(job)

        if (job.status === 'completed') {
          setImportStatus('success')
          setImportMessage(`Successfully imported ${job.processed_records} records`)
          clearInterval(interval)
          onImport()
        } else if (job.status === 'failed') {
          setImportStatus('error')
          setImportMessage(job.errors[0] || 'Import failed')
          clearInterval(interval)
        }
      } catch (error) {
        console.error('Failed to fetch job status:', error)
      }
    }, 1000)

    return () => clearInterval(interval)
  }, [importJobId, importStatus, onImport])

  const handleImport = async () => {
    if (!config.file) return

    setIsImporting(true)
    setImportStatus('importing')

    try {
      const formData = new FormData()
      formData.append('file', config.file)
      formData.append('import_type', config.importType)
      formData.append('file_name', config.file.name)
      formData.append('field_mappings', JSON.stringify(config.fieldMappings || {}))
      formData.append('advanced_options', JSON.stringify(config.advancedOptions?.[config.importType] || {}))
      formData.append('validate_only', 'false')

      const response = await axios.post('/api/imports/execute', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      setImportJobId(response.data.job_id)
      setImportMessage('Import job started...')
    } catch (error) {
      setImportStatus('error')
      setImportMessage('Failed to start import')
      console.error('Import error:', error)
      setIsImporting(false)
    }
  }

  const downloadConfig = () => {
    const configData = {
      type: 'niamoto-import-config',
      version: '1.0',
      importType: config.importType,
      fieldMappings: config.fieldMappings,
      advancedOptions: config.advancedOptions,
      created: new Date().toISOString()
    }

    const blob = new Blob([JSON.stringify(configData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `niamoto-${config.importType}-import-config.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const renderFileInfo = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          File Information
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex justify-between">
          <span className="text-sm text-muted-foreground">Filename:</span>
          <span className="text-sm font-medium">{config.file?.name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-muted-foreground">Size:</span>
          <span className="text-sm font-medium">
            {config.file ? `${(config.file.size / 1024).toFixed(2)} KB` : 'N/A'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-muted-foreground">Type:</span>
          <span className="text-sm font-medium">{config.fileAnalysis?.type || 'Unknown'}</span>
        </div>
        {config.fileAnalysis?.row_count && (
          <div className="flex justify-between">
            <span className="text-sm text-muted-foreground">Rows:</span>
            <span className="text-sm font-medium">{config.fileAnalysis.row_count}</span>
          </div>
        )}
        {config.fileAnalysis?.feature_count && (
          <div className="flex justify-between">
            <span className="text-sm text-muted-foreground">Features:</span>
            <span className="text-sm font-medium">{config.fileAnalysis.feature_count}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )

  const renderValidation = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          Validation Results
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isValidating ? (
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm">Validating configuration...</span>
          </div>
        ) : validationResult ? (
          <div className="space-y-4">
            {validationResult.valid ? (
              <Alert>
                <CheckCircle2 className="h-4 w-4" />
                <AlertTitle>Valid Configuration</AlertTitle>
                <AlertDescription>
                  Your import configuration is valid and ready to execute.
                </AlertDescription>
              </Alert>
            ) : (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Invalid Configuration</AlertTitle>
                <AlertDescription>
                  Please fix the errors below before importing.
                </AlertDescription>
              </Alert>
            )}

            {validationResult.errors.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-2">Errors:</h4>
                <ul className="list-disc list-inside space-y-1">
                  {validationResult.errors.map((error, idx) => (
                    <li key={idx} className="text-sm text-destructive">{error}</li>
                  ))}
                </ul>
              </div>
            )}

            {validationResult.warnings.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-2">Warnings:</h4>
                <ul className="list-disc list-inside space-y-1">
                  {validationResult.warnings.map((warning, idx) => (
                    <li key={idx} className="text-sm text-yellow-600">{warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : null}
      </CardContent>
    </Card>
  )

  const renderMappings = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          Field Mappings
        </CardTitle>
        <CardDescription>
          How your data will be mapped to the database
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[200px] pr-4">
          <div className="space-y-2">
            {Object.entries(config.fieldMappings || {}).map(([dbField, fileColumn]) => (
              <div key={dbField} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{dbField}:</span>
                  <span className="text-sm text-muted-foreground">←</span>
                </div>
                <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
                  {fileColumn}
                </span>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )

  const renderAdvancedOptions = () => {
    const options = config.advancedOptions?.[config.importType] || {}
    const hasOptions = Object.keys(options).length > 0

    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            Advanced Options
          </CardTitle>
          <CardDescription>
            Additional settings for your import
          </CardDescription>
        </CardHeader>
        <CardContent>
          {hasOptions ? (
            <ScrollArea className="h-[200px] pr-4">
              <div className="space-y-2">
                {Object.entries(options).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between py-2">
                    <span className="text-sm font-medium">
                      {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}:
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {typeof value === 'boolean' ? (value ? 'Yes' : 'No') : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          ) : (
            <p className="text-sm text-muted-foreground">No advanced options configured</p>
          )}
        </CardContent>
      </Card>
    )
  }

  const renderDataPreview = () => (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Eye className="h-5 w-5" />
          Data Preview
        </CardTitle>
        <CardDescription>
          First few rows of your data after mapping
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px]">
          {config.fileAnalysis?.sample_data ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    {Object.keys(config.fieldMappings || {}).map(field => (
                      <th key={field} className="px-2 py-1 text-left font-medium">
                        {field}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {config.fileAnalysis.sample_data.slice(0, 5).map((row: any, idx: number) => (
                    <tr key={idx} className="border-b">
                      {Object.entries(config.fieldMappings || {}).map(([field, column]) => (
                        <td key={field} className="px-2 py-1">
                          {row[column as string] || '-'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No preview data available</p>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  )

  const getImportTypeLabel = () => {
    const labels = {
      taxonomy: 'Taxonomy',
      plots: 'Plots',
      occurrences: 'Occurrences',
      shapes: 'Shapes'
    }
    return labels[config.importType] || config.importType
  }

  const renderImportStatus = () => {
    if (importStatus === 'idle' && !validationResult) return null

    if (importJob && importStatus === 'importing') {
      return (
        <Alert>
          <Loader2 className="h-4 w-4 animate-spin" />
          <AlertTitle>Importing...</AlertTitle>
          <AlertDescription>
            <div className="space-y-2">
              <p>{importMessage}</p>
              <div className="flex items-center gap-2">
                <Progress value={importJob.progress} className="flex-1" />
                <span className="text-sm font-medium">{importJob.progress}%</span>
              </div>
              <p className="text-xs text-muted-foreground">
                {importJob.processed_records} / {importJob.total_records} records processed
              </p>
            </div>
          </AlertDescription>
        </Alert>
      )
    }

    return (
      <Alert className={importStatus === 'error' ? 'border-destructive' : ''}>
        {importStatus === 'validating' && <Loader2 className="h-4 w-4 animate-spin" />}
        {importStatus === 'success' && <CheckCircle2 className="h-4 w-4 text-green-600" />}
        {importStatus === 'error' && <AlertCircle className="h-4 w-4 text-destructive" />}
        <AlertTitle>
          {importStatus === 'validating' && 'Validating...'}
          {importStatus === 'success' && 'Import Complete'}
          {importStatus === 'error' && 'Import Failed'}
        </AlertTitle>
        {importMessage && <AlertDescription>{importMessage}</AlertDescription>}
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Review Import Configuration</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Review your {getImportTypeLabel()} import settings before proceeding
        </p>
      </div>

      <Tabs defaultValue="summary" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="summary">Summary</TabsTrigger>
          <TabsTrigger value="mappings">Mappings</TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
        </TabsList>

        <TabsContent value="summary" className="space-y-4">
          {renderFileInfo()}
          {renderValidation()}
          {renderAdvancedOptions()}
        </TabsContent>

        <TabsContent value="mappings">
          {renderMappings()}
        </TabsContent>

        <TabsContent value="preview">
          {renderDataPreview()}
        </TabsContent>

        <TabsContent value="config" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Download className="h-5 w-5" />
                Export Configuration
              </CardTitle>
              <CardDescription>
                Save this configuration for future use
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm" onClick={downloadConfig}>
                <Download className="mr-2 h-4 w-4" />
                Download Configuration
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Raw Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[200px]">
                <pre className="text-xs">
                  {JSON.stringify(config, null, 2)}
                </pre>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {renderImportStatus()}

      <Separator />

      <div className="flex justify-between items-center">
        <div className="text-sm text-muted-foreground">
          {!isImporting && importStatus === 'idle' && validationResult?.valid && (
            <>Ready to import {config.fileAnalysis?.row_count || 'your'} records</>
          )}
        </div>
        <Button
          onClick={handleImport}
          disabled={isImporting || importStatus === 'success' || !validationResult?.valid}
          size="lg"
        >
          {isImporting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Importing...
            </>
          ) : importStatus === 'success' ? (
            <>
              <CheckCircle2 className="mr-2 h-4 w-4" />
              Import Complete
            </>
          ) : (
            'Start Import'
          )}
        </Button>
      </div>
    </div>
  )
}
