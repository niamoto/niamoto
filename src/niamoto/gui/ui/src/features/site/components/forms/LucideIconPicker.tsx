/**
 * LucideIconPicker - Icon selector using Lucide icons
 *
 * Provides a popover with a grid of commonly used icons
 * for ecological/data visualization contexts
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { Leaf } from 'lucide-react'
import { ICON_REGISTRY } from './lucideIconRegistry'

// Grouped icons for better organization
const ICON_GROUPS = {
  Nature: ['leaf', 'tree-pine', 'tree-deciduous', 'flower', 'sprout', 'mountain', 'waves', 'sun', 'cloud', 'droplets'],
  Faune: ['bird', 'bug', 'fish'],
  Statistiques: ['bar-chart', 'trending-up', 'pie-chart', 'activity', 'target', 'gauge'],
  Geographie: ['map', 'map-pin', 'globe', 'compass', 'navigation'],
  Donnees: ['database', 'folder', 'file-text', 'files', 'archive'],
  Recherche: ['search', 'microscope', 'flask', 'book', 'graduation'],
  Navigation: ['eye', 'info', 'help', 'home', 'link', 'external-link'],
  Divers: ['users', 'user', 'layers', 'calendar', 'clock', 'zap', 'star', 'heart', 'award'],
}

interface LucideIconPickerProps {
  value: string
  onChange: (iconName: string) => void
  className?: string
}

export function LucideIconPicker({ value, onChange, className }: LucideIconPickerProps) {
  const { t } = useTranslation('site')
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')

  // Get the icon component for the current value
  const CurrentIcon = ICON_REGISTRY[value] || Leaf

  // Filter icons based on search
  const filteredGroups = Object.entries(ICON_GROUPS).reduce(
    (acc, [group, icons]) => {
      const filtered = icons.filter((name) =>
        name.toLowerCase().includes(search.toLowerCase())
      )
      if (filtered.length > 0) {
        acc[group] = filtered
      }
      return acc
    },
    {} as Record<string, string[]>
  )

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className={cn('h-9 w-9', className)}
        >
          <CurrentIcon className="h-4 w-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-2" align="start">
        <div className="space-y-2">
          <Input
            placeholder={t('iconPicker.searchIcon')}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8"
          />
          <div className="max-h-64 overflow-auto space-y-2">
            {Object.entries(filteredGroups).map(([group, icons]) => (
              <div key={group}>
                <div className="text-xs font-medium text-muted-foreground px-1 py-1">
                  {group}
                </div>
                <div className="grid grid-cols-8 gap-1">
                  {icons.map((iconName) => {
                    const Icon = ICON_REGISTRY[iconName]
                    return (
                      <button
                        key={iconName}
                        type="button"
                        onClick={() => {
                          onChange(iconName)
                          setOpen(false)
                          setSearch('')
                        }}
                        className={cn(
                          'flex h-8 w-8 items-center justify-center rounded hover:bg-muted transition-colors',
                          value === iconName && 'bg-primary/10 text-primary'
                        )}
                        title={iconName}
                      >
                        <Icon className="h-4 w-4" />
                      </button>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}

export default LucideIconPicker
