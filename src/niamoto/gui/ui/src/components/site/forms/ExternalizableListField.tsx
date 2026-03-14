/**
 * ExternalizableListField - Reusable component for managing lists that can be externalized to JSON files
 *
 * This component allows switching between:
 * - Inline mode: data stored directly in YAML configuration
 * - External mode: data stored in a separate JSON file
 *
 * Features:
 * - Auto-detection of current storage mode
 * - Switch between inline/external storage
 * - Auto-externalization suggestion when list exceeds threshold
 * - Export/import functionality
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Database,
  FileJson,
  FileSpreadsheet,
  Download,
  Upload,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  ExternalLink,
} from 'lucide-react'
import { toast } from 'sonner'
import { useDataContent, useUpdateDataContent, useImportCsv } from '@/hooks/useSiteConfig'

type StorageMode = 'inline' | 'external'

// Threshold for suggesting externalization
const EXTERNALIZATION_THRESHOLD = 50

interface ExternalizableListFieldProps<T> {
  /** Page name (used for default file path) */
  pageName: string
  /** List name (e.g., "references", "resources", "team") */
  listName: string
  /** Current data source path from context (null = inline mode) */
  dataSource?: string | null
  /** Callback when data source changes */
  onDataSourceChange: (source: string | null) => void
  /** Current inline data */
  inlineData: T[]
  /** Callback when inline data changes */
  onInlineDataChange: (data: T[]) => void
  /** Optional label */
  label?: string
  /** Optional description */
  description?: string
}

export function ExternalizableListField<T>({
  pageName,
  listName,
  dataSource,
  onDataSourceChange,
  inlineData,
  onInlineDataChange,
  label,
  description,
}: ExternalizableListFieldProps<T>) {
  const { t } = useTranslation(['site', 'common'])

  // Determine current mode
  const [storageMode, setStorageMode] = useState<StorageMode>(() =>
    dataSource ? 'external' : 'inline'
  )

  // Dialog states
  const [showExternalizeDialog, setShowExternalizeDialog] = useState(false)
  const [showInlineDialog, setShowInlineDialog] = useState(false)
  const [isSwitching, setIsSwitching] = useState(false)

  // Generate default file path
  const getDefaultFilePath = useCallback(() => {
    return `data/${pageName}-${listName}.json`
  }, [pageName, listName])

  // Current file path for external mode
  const externalFilePath = storageMode === 'external' ? (dataSource || getDefaultFilePath()) : null

  // Fetch external data
  const { data: externalData, isLoading: externalLoading, refetch: refetchExternal } = useDataContent(externalFilePath)
  const updateDataMutation = useUpdateDataContent()
  const importCsvMutation = useImportCsv()

  // File input refs
  const jsonInputRef = useRef<HTMLInputElement>(null)
  const csvInputRef = useRef<HTMLInputElement>(null)

  // Sync mode when dataSource changes
  useEffect(() => {
    setStorageMode(dataSource ? 'external' : 'inline')
  }, [dataSource])

  // Check if we should suggest externalization
  const shouldSuggestExternalization =
    storageMode === 'inline' && inlineData.length >= EXTERNALIZATION_THRESHOLD

  // Handle switch to external mode
  const handleExternalize = async () => {
    setIsSwitching(true)
    const filePath = getDefaultFilePath()

    try {
      // Save current inline data to JSON file
      await updateDataMutation.mutateAsync({
        path: filePath,
        data: inlineData,
      })

      // Update the data source in config
      onDataSourceChange(filePath)

      // Clear inline data (it's now in the file)
      onInlineDataChange([])

      setStorageMode('external')
      setShowExternalizeDialog(false)

      toast.success(t('site:forms.common.externalizedSuccess'), {
        description: filePath,
      })
    } catch (error) {
      toast.error(t('site:forms.common.externalizeError'), {
        description: String(error),
      })
    } finally {
      setIsSwitching(false)
    }
  }

  // Handle switch to inline mode
  const handleInline = async () => {
    setIsSwitching(true)

    try {
      // Load data from external file
      const response = await refetchExternal()
      const externalItems = (response.data?.data || []) as T[]

      // Set inline data
      onInlineDataChange(externalItems)

      // Clear data source
      onDataSourceChange(null)

      setStorageMode('inline')
      setShowInlineDialog(false)

      toast.success(t('site:forms.common.inlinedSuccess'), {
        description: `${externalItems.length} ${t('site:forms.common.itemsLoaded')}`,
      })
    } catch (error) {
      toast.error(t('site:forms.common.inlineError'), {
        description: String(error),
      })
    } finally {
      setIsSwitching(false)
    }
  }

  // Export data to file download
  const handleExport = () => {
    const dataToExport = storageMode === 'external' ? externalData?.data : inlineData
    if (!dataToExport || dataToExport.length === 0) {
      toast.error(t('site:forms.common.noDataToExport'))
      return
    }

    const json = JSON.stringify(dataToExport, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${pageName}-${listName}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast.success(t('site:forms.common.exportSuccess'))
  }

  // Import JSON data from file
  const handleJsonImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        const content = e.target?.result as string
        const importedData = JSON.parse(content) as T[]

        if (!Array.isArray(importedData)) {
          throw new Error(t('site:forms.common.importNotArray'))
        }

        if (storageMode === 'external' && externalFilePath) {
          // Save directly to external file
          await updateDataMutation.mutateAsync({
            path: externalFilePath,
            data: importedData,
          })
          await refetchExternal()
        } else {
          // Update inline data
          onInlineDataChange(importedData)
        }

        toast.success(t('site:forms.common.importSuccess'), {
          description: `${importedData.length} ${t('site:forms.common.itemsImported')}`,
        })
      } catch (error) {
        toast.error(t('site:forms.common.importError'), {
          description: String(error),
        })
      }
    }
    reader.readAsText(file)

    // Reset input
    event.target.value = ''
  }

  // Import CSV data from file
  const handleCsvImport = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0]
      if (!file) return

      try {
        const result = await importCsvMutation.mutateAsync({ file })

        if (result.success && result.data.length > 0) {
          const importedData = result.data as T[]

          if (storageMode === 'external' && externalFilePath) {
            // Merge with existing data in external file
            const existingData = externalData?.data || []
            const newData = [...existingData, ...importedData] as T[]
            await updateDataMutation.mutateAsync({
              path: externalFilePath,
              data: newData,
            })
            await refetchExternal()
          } else {
            // Merge with existing inline data
            const newData = [...inlineData, ...importedData]
            onInlineDataChange(newData)
          }

          toast.success(t('site:forms.common.importCsvSuccess'), {
            description: t('site:forms.common.itemsImported', { count: result.count }),
          })

          if (result.errors.length > 0) {
            toast.warning(t('site:forms.common.importWarnings', { count: result.errors.length }), {
              description: result.errors.slice(0, 3).join('\n'),
            })
          }
        } else {
          toast.error(t('site:forms.common.importCsvError'), {
            description: result.errors[0] || 'No data found',
          })
        }
      } catch (error) {
        toast.error(t('site:forms.common.importCsvError'), {
          description: String(error),
        })
      }

      // Reset input
      event.target.value = ''
    },
    [
      importCsvMutation,
      storageMode,
      externalFilePath,
      externalData,
      updateDataMutation,
      refetchExternal,
      inlineData,
      onInlineDataChange,
      t,
    ]
  )

  // Get current item count
  const itemCount = storageMode === 'external' ? (externalData?.count || 0) : inlineData.length

  return (
    <div className="space-y-3">
      {/* Header with info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {label && <span className="text-sm font-medium">{label}</span>}
          <Badge variant={storageMode === 'external' ? 'default' : 'secondary'} className="text-xs">
            {storageMode === 'external' ? (
              <>
                <FileJson className="h-3 w-3 mr-1" />
                {t('site:forms.common.externalFile')}
              </>
            ) : (
              <>
                <Database className="h-3 w-3 mr-1" />
                {t('site:forms.common.inlineYaml')}
              </>
            )}
          </Badge>
          <Badge variant="outline" className="text-xs">
            {itemCount} {t('site:forms.common.items')}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          {/* Export button */}
          <Button variant="ghost" size="sm" onClick={handleExport} title={t('site:forms.common.export')}>
            <Download className="h-4 w-4" />
          </Button>

          {/* Import dropdown */}
          <input
            ref={jsonInputRef}
            type="file"
            accept=".json"
            onChange={handleJsonImport}
            className="hidden"
          />
          <input
            ref={csvInputRef}
            type="file"
            accept=".csv,.tsv"
            onChange={handleCsvImport}
            className="hidden"
          />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                title={t('site:forms.common.import')}
                disabled={importCsvMutation.isPending}
              >
                {importCsvMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => jsonInputRef.current?.click()}>
                <FileJson className="h-4 w-4 mr-2" />
                {t('site:forms.common.importJson')}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => csvInputRef.current?.click()}>
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                {t('site:forms.common.importCsv')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Switch mode button */}
          {storageMode === 'inline' ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowExternalizeDialog(true)}
              disabled={inlineData.length === 0}
            >
              <ExternalLink className="h-4 w-4 mr-1" />
              {t('site:forms.common.externalize')}
            </Button>
          ) : (
            <Button variant="outline" size="sm" onClick={() => setShowInlineDialog(true)}>
              <Database className="h-4 w-4 mr-1" />
              {t('site:forms.common.bringInline')}
            </Button>
          )}
        </div>
      </div>

      {/* Description */}
      {description && <p className="text-xs text-muted-foreground">{description}</p>}

      {/* File path indicator for external mode */}
      {storageMode === 'external' && externalFilePath && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/30 rounded px-3 py-2">
          <FileJson className="h-3 w-3" />
          <span className="font-mono">{externalFilePath}</span>
          {externalLoading && <Loader2 className="h-3 w-3 animate-spin" />}
          {!externalLoading && externalData && (
            <CheckCircle2 className="h-3 w-3 text-green-600" />
          )}
        </div>
      )}

      {/* Warning for large inline lists */}
      {shouldSuggestExternalization && (
        <div className="flex items-start gap-2 text-xs bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200 rounded px-3 py-2 border border-amber-200 dark:border-amber-800">
          <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">{t('site:forms.common.largeListWarning')}</p>
            <p className="mt-1 text-amber-700 dark:text-amber-300">
              {t('site:forms.common.largeListSuggestion', { count: inlineData.length })}
            </p>
          </div>
        </div>
      )}

      {/* Externalize Dialog */}
      <AlertDialog open={showExternalizeDialog} onOpenChange={setShowExternalizeDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('site:forms.common.externalizeTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('site:forms.common.externalizeDesc', {
                count: inlineData.length,
                path: getDefaultFilePath(),
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isSwitching}>{t('common:cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleExternalize} disabled={isSwitching}>
              {isSwitching && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {t('site:forms.common.externalize')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Inline Dialog */}
      <AlertDialog open={showInlineDialog} onOpenChange={setShowInlineDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('site:forms.common.inlineTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('site:forms.common.inlineDesc', {
                count: externalData?.count || 0,
              })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isSwitching}>{t('common:cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleInline} disabled={isSwitching}>
              {isSwitching && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {t('site:forms.common.bringInline')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default ExternalizableListField
