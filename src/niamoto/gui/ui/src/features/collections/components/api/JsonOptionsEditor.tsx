import { useTranslation } from 'react-i18next'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'

type JsonOptionsValue = Record<string, unknown>

interface JsonOptionsEditorProps {
  value?: JsonOptionsValue
  onChange: (value: JsonOptionsValue) => void
}

type BooleanOptionKey = 'ensure_ascii' | 'compress' | 'minify' | 'exclude_null'
type NumberOptionKey = 'indent' | 'geometry_precision' | 'max_array_length'

function hasOption(value: JsonOptionsValue, key: string) {
  return Object.prototype.hasOwnProperty.call(value, key)
}

function numberValue(value: JsonOptionsValue, key: NumberOptionKey) {
  return typeof value[key] === 'number' ? String(value[key]) : ''
}

export function JsonOptionsEditor({ value, onChange }: JsonOptionsEditorProps) {
  const { t } = useTranslation(['sources', 'common'])
  const options = value ?? {}
  const minifyEnabled = options.minify === true

  const updateOptions = (mutate: (next: JsonOptionsValue) => void) => {
    const next = { ...options }
    mutate(next)
    onChange(next)
  }

  const setBooleanOption = (key: BooleanOptionKey, checked: boolean) => {
    updateOptions((next) => {
      next[key] = checked

      if (key === 'minify') {
        if (checked) {
          next.indent = null
        } else if (next.indent === null) {
          delete next.indent
        }
      }
    })
  }

  const setNumberOption = (key: NumberOptionKey, rawValue: string) => {
    if (rawValue === '') {
      updateOptions((next) => {
        delete next[key]
      })
      return
    }

    const parsed = Number.parseInt(rawValue, 10)
    if (Number.isNaN(parsed)) return

    updateOptions((next) => {
      next[key] = parsed

      if (key === 'indent') {
        next.minify = false
      }
    })
  }

  const clearOption = (key: BooleanOptionKey | NumberOptionKey) => {
    updateOptions((next) => {
      delete next[key]

      if (key === 'minify' && next.indent === null) {
        delete next.indent
      }
    })
  }

  const renderStatus = (key: BooleanOptionKey | NumberOptionKey) => (
    <Badge variant="secondary" className="text-[10px]">
      {hasOption(options, key)
        ? t('collectionPanel.api.jsonOptionsForm.configured')
        : t('collectionPanel.api.jsonOptionsForm.inherited')}
    </Badge>
  )

  const renderClearButton = (key: BooleanOptionKey | NumberOptionKey) =>
    hasOption(options, key) ? (
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => clearOption(key)}
      >
        {t('collectionPanel.api.jsonOptionsForm.inherit')}
      </Button>
    ) : null

  const renderBooleanOption = (key: BooleanOptionKey) => (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border p-3">
      <div className="min-w-0 flex-1 space-y-1">
        <Label>{t(`collectionPanel.api.jsonOptionsForm.${key}`)}</Label>
        <p className="text-xs text-muted-foreground">
          {t(`collectionPanel.api.jsonOptionsForm.${key}Help`)}
        </p>
      </div>
      <div className="flex items-center gap-2">
        {renderStatus(key)}
        {renderClearButton(key)}
        <Switch
          aria-label={t(`collectionPanel.api.jsonOptionsForm.${key}`)}
          checked={options[key] === true}
          onCheckedChange={(checked) => setBooleanOption(key, checked)}
        />
      </div>
    </div>
  )

  const renderNumberOption = (key: NumberOptionKey) => {
    const isIndentDisabled = key === 'indent' && minifyEnabled

    return (
      <div className="grid gap-2 rounded-md border p-3 md:grid-cols-[minmax(0,1fr)_12rem] md:items-start">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Label htmlFor={`json-option-${key}`}>
              {t(`collectionPanel.api.jsonOptionsForm.${key}`)}
            </Label>
            {renderStatus(key)}
          </div>
          <p className="text-xs text-muted-foreground">
            {isIndentDisabled
              ? t('collectionPanel.api.jsonOptionsForm.indentDisabledByMinify')
              : t(`collectionPanel.api.jsonOptionsForm.${key}Help`)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            id={`json-option-${key}`}
            name={key}
            type="number"
            min={0}
            step={1}
            value={numberValue(options, key)}
            disabled={isIndentDisabled}
            placeholder={t('collectionPanel.api.jsonOptionsForm.inherited')}
            onChange={(event) => setNumberOption(key, event.currentTarget.value)}
          />
          {!isIndentDisabled && renderClearButton(key)}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        {t('collectionPanel.api.jsonOptionsForm.help')}
      </p>
      <div className="space-y-2">
        {renderNumberOption('indent')}
        {renderBooleanOption('minify')}
        {renderBooleanOption('compress')}
        {renderBooleanOption('ensure_ascii')}
        {renderBooleanOption('exclude_null')}
        {renderNumberOption('geometry_precision')}
        {renderNumberOption('max_array_length')}
      </div>
    </div>
  )
}
