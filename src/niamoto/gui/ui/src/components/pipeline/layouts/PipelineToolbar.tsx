// React is imported globally from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Play, Save, RotateCcw, AlertCircle, CheckCircle2 } from 'lucide-react'
import { usePipelineStore } from '../store'

export function PipelineToolbar() {
  const { t } = useTranslation()
  const { nodes, isValid, errors, isRunning, setIsRunning } = usePipelineStore()

  const importCount = nodes.filter(n => n.data.nodeType === 'import').length
  const transformCount = nodes.filter(n => n.data.nodeType === 'transform').length
  const exportCount = nodes.filter(n => n.data.nodeType === 'export').length

  const handleRun = () => {
    if (isValid && !isRunning) {
      setIsRunning(true)
      // TODO: Implement pipeline execution
      setTimeout(() => setIsRunning(false), 3000)
    }
  }

  const handleSave = () => {
    // TODO: Implement save to YAML
    console.log('Saving pipeline...')
  }

  const handleReset = () => {
    // TODO: Implement reset
    console.log('Resetting pipeline...')
  }

  return (
    <div className="bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border rounded-lg shadow-lg p-2">
      <div className="flex items-center gap-4">
        {/* Status */}
        <div className="flex items-center gap-2">
          {isValid ? (
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          ) : (
            <AlertCircle className="h-4 w-4 text-yellow-500" />
          )}
          <span className="text-sm font-medium">
            {isValid
              ? t('pipeline.status.ready', 'Pipeline Ready')
              : t('pipeline.status.incomplete', 'Pipeline Incomplete')}
          </span>
        </div>

        {/* Node counts */}
        <div className="flex items-center gap-2">
          <Badge variant="secondary">Import: {importCount}</Badge>
          <Badge variant="secondary">Transform: {transformCount}</Badge>
          <Badge variant="secondary">Export: {exportCount}</Badge>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 ml-auto">
          <Button
            size="sm"
            variant="outline"
            onClick={handleReset}
            disabled={isRunning}
          >
            <RotateCcw className="mr-2 h-4 w-4" />
            {t('pipeline.actions.reset', 'Reset')}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={handleSave}
            disabled={isRunning}
          >
            <Save className="mr-2 h-4 w-4" />
            {t('pipeline.actions.save', 'Save')}
          </Button>
          <Button
            size="sm"
            onClick={handleRun}
            disabled={!isValid || isRunning}
          >
            <Play className="mr-2 h-4 w-4" />
            {isRunning
              ? t('pipeline.actions.running', 'Running...')
              : t('pipeline.actions.run', 'Run')}
          </Button>
        </div>
      </div>

      {/* Error messages */}
      {!isValid && errors.length > 0 && (
        <div className="mt-2 text-xs text-destructive">
          {errors[0]}
        </div>
      )}
    </div>
  )
}
