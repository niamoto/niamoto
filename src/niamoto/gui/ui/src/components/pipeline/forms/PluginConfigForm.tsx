import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Info, AlertCircle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import JsonSchemaForm from '@/components/forms/JsonSchemaForm'
import { useForm } from 'react-hook-form'

interface PluginConfigFormProps {
  pluginId: string
  pluginType?: string
  config: any
  onConfigChange: (config: any) => void
  availableFields?: string[] // For field-select widgets
}

export function PluginConfigForm({
  pluginId,
  pluginType,
  config,
  onConfigChange,
  availableFields,
}: PluginConfigFormProps) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hasParams, setHasParams] = useState(false)
  const form = useForm({
    defaultValues: config || {},
  })

  // Fetch plugin schema from API
  useEffect(() => {
    const fetchSchema = async () => {
      if (!pluginId) {
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)

      try {
        const response = await fetch(`/api/plugins/${pluginId}/schema`)
        if (!response.ok) {
          throw new Error(`Failed to fetch schema: ${response.statusText}`)
        }

        const data = await response.json()

        // Check if plugin has parameters
        if (!data.has_params || !data.schema) {
          setHasParams(false)
          setLoading(false)
          return
        }

        setHasParams(true)

        // Update form with existing config
        if (config) {
          form.reset(config)
        }
      } catch (err) {
        console.error('Error fetching plugin schema:', err)
        setError(err instanceof Error ? err.message : 'Failed to load plugin schema')
      } finally {
        setLoading(false)
      }
    }

    fetchSchema()
  }, [pluginId, config, form])

  // Handle form changes
  const handleChange = (data: any) => {
    onConfigChange(data)
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <Alert className="mt-2">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  // No parameters state
  if (!hasParams) {
    return (
      <Alert className="mt-2">
        <Info className="h-4 w-4" />
        <AlertDescription>
          {t('pipeline.config.noParams', 'This plugin does not require configuration')}
        </AlertDescription>
      </Alert>
    )
  }

  // Render JsonSchemaForm
  return (
    <div className="space-y-4">
      <JsonSchemaForm
        pluginId={pluginId}
        pluginType={pluginType}
        form={form}
        onChange={handleChange}
        availableFields={availableFields}
        showTitle={false}
      />
    </div>
  )
}
