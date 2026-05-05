import { useMemo, useState } from 'react'
import { Check, ChevronsUpDown } from 'lucide-react'

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
import { cn } from '@/lib/utils'

export interface FieldSelectorOption {
  value: string
  label: string
  description?: string
  groupKey?: string
  groupLabel?: string
}

interface FieldSelectorProps {
  value?: string
  options: FieldSelectorOption[]
  onChange: (value: string) => void
  placeholder: string
  emptyLabel: string
  searchPlaceholder?: string
  disabled?: boolean
  ariaLabel?: string
}

export function FieldSelector({
  value,
  options,
  onChange,
  placeholder,
  emptyLabel,
  searchPlaceholder,
  disabled = false,
  ariaLabel,
}: FieldSelectorProps) {
  const [open, setOpen] = useState(false)
  const selected = options.find((option) => option.value === value)
  const groups = useMemo(() => groupOptions(options), [options])

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-label={ariaLabel}
          disabled={disabled}
          className="w-full justify-between"
        >
          <span className="min-w-0 truncate">
            {selected?.label ?? value ?? placeholder}
          </span>
          <ChevronsUpDown className="h-4 w-4 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0" align="start">
        <Command>
          <CommandInput placeholder={searchPlaceholder ?? placeholder} />
          <CommandList>
            <CommandEmpty>{emptyLabel}</CommandEmpty>
            {groups.map((group) => (
              <CommandGroup
                key={group.key}
                heading={group.label}
              >
                {group.options.map((option) => (
                  <CommandItem
                    key={option.value}
                    value={`${option.label} ${option.value}`}
                    keywords={[option.value, option.description ?? '']}
                    onSelect={() => {
                      onChange(option.value)
                      setOpen(false)
                    }}
                  >
                    <Check
                      className={cn(
                        'h-4 w-4',
                        option.value === value ? 'opacity-100' : 'opacity-0',
                      )}
                    />
                    <span className="flex min-w-0 flex-col items-start">
                      <span className="max-w-full truncate">{option.label}</span>
                      {option.description && (
                        <span className="max-w-full truncate font-mono text-xs text-muted-foreground">
                          {option.description}
                        </span>
                      )}
                    </span>
                  </CommandItem>
                ))}
              </CommandGroup>
            ))}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

function groupOptions(options: FieldSelectorOption[]) {
  const groups = new Map<
    string,
    { key: string; label: string; options: FieldSelectorOption[] }
  >()

  options.forEach((option) => {
    const key = option.groupKey ?? 'fields'
    const label = option.groupLabel ?? 'Fields'
    if (!groups.has(key)) {
      groups.set(key, { key, label, options: [] })
    }
    groups.get(key)?.options.push(option)
  })

  return Array.from(groups.values())
}
