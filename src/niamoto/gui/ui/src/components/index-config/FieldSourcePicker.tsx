import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { resolveLocalizedString } from '@/components/ui/localized-string'
import { cn } from '@/lib/utils'
import type { SuggestedDisplayField } from './useIndexConfig'

interface FieldSourcePickerProps {
  value: string
  options: SuggestedDisplayField[]
  loading?: boolean
  onLoad?: () => void
  onSelect: (field: SuggestedDisplayField) => void
}

function getOptionLabel(field: SuggestedDisplayField, language: string): string {
  return resolveLocalizedString(field.label, language, 'fr') || field.name || field.source
}

function getSamplePreview(field: SuggestedDisplayField): string {
  return (field.sample_values || [])
    .filter(Boolean)
    .slice(0, 3)
    .join(', ')
}

export function FieldSourcePicker({
  value,
  options,
  loading = false,
  onLoad,
  onSelect,
}: FieldSourcePickerProps) {
  const { t, i18n } = useTranslation('indexConfig')
  const [open, setOpen] = useState(false)

  const selectedOption = useMemo(
    () => options.find((option) => option.source === value),
    [options, value]
  )

  const selectedLabel = selectedOption
    ? getOptionLabel(selectedOption, i18n.language)
    : value

  return (
    <Popover
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen)
        if (nextOpen) {
          onLoad?.()
        }
      }}
    >
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="h-auto min-h-11 w-full justify-between px-3 py-2 text-left font-normal"
        >
          <span className="min-w-0">
            <span className="block truncate text-sm font-medium">
              {selectedLabel || t('fieldEditor.chooseDataField')}
            </span>
            <span className="block truncate font-mono text-xs text-muted-foreground">
              {value || t('fieldEditor.noDataFieldSelected')}
            </span>
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        className="w-[var(--radix-popover-trigger-width)] p-0"
      >
        <Command>
          <CommandInput placeholder={t('fieldEditor.fieldPickerPlaceholder')} />
          <CommandList className="max-h-80">
            {loading ? (
              <div className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('fieldEditor.fieldPickerLoading')}
              </div>
            ) : (
              <CommandEmpty>{t('fieldEditor.fieldPickerEmpty')}</CommandEmpty>
            )}
            <CommandGroup heading={t('fieldEditor.detectedFields')}>
              {options.map((option) => {
                const label = getOptionLabel(option, i18n.language)
                const samplePreview = getSamplePreview(option)

                return (
                  <CommandItem
                    key={option.source}
                    value={`${label} ${option.name} ${option.source} ${samplePreview}`}
                    onSelect={() => {
                      onSelect(option)
                      setOpen(false)
                    }}
                    className="items-start gap-3 py-2"
                  >
                    <Check
                      className={cn(
                        'mt-0.5 h-4 w-4 shrink-0',
                        value === option.source ? 'opacity-100' : 'opacity-0'
                      )}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="truncate font-medium">{label}</span>
                        <Badge variant="secondary" className="h-5 shrink-0 text-[10px]">
                          {option.type}
                        </Badge>
                      </span>
                      <span className="block truncate font-mono text-xs text-muted-foreground">
                        {option.source}
                      </span>
                      {samplePreview && (
                        <span className="block truncate text-xs text-muted-foreground">
                          {t('fieldEditor.exampleValues', { values: samplePreview })}
                        </span>
                      )}
                    </span>
                  </CommandItem>
                )
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
