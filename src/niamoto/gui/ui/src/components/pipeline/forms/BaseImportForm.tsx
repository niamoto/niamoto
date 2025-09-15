import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle } from 'lucide-react'

export interface BaseImportFormProps {
  config: any
  onConfigChange: (config: any) => void
  onValidate?: () => void
  errors?: string[]
}

export function BaseImportForm({
  config,
  onConfigChange,
  onValidate,
  errors,
  children
}: BaseImportFormProps & { children?: ReactNode }) {
  const { t } = useTranslation()

  return (
    <div className="space-y-4">
      {/* Common import fields */}
      <div className="space-y-2">
        <Label htmlFor="name">
          {t('pipeline.import.name', 'Import Name')}
        </Label>
        <Input
          id="name"
          value={config?.name || ''}
          onChange={(e) => onConfigChange({ ...config, name: e.target.value })}
          placeholder={t('pipeline.import.namePlaceholder', 'Enter a name for this import')}
        />
      </div>

      {/* Specific import fields */}
      {children}

      {/* Validation errors */}
      {errors && errors.length > 0 && (
        <>
          <Separator />
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              <ul className="list-disc list-inside">
                {errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        </>
      )}

      {/* Actions */}
      {onValidate && (
        <>
          <Separator />
          <div className="flex justify-end">
            <Button onClick={onValidate}>
              {t('pipeline.import.validate', 'Validate Configuration')}
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
