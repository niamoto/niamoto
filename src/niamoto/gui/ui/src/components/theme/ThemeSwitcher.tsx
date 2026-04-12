/**
 * Theme Switcher - Visual theme selection component
 *
 * A beautiful gallery-style theme picker with live previews
 * showing typography, shapes, and colors distinctive to each theme.
 */

import { Moon, Sun, Monitor, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useTheme, AVAILABLE_FONTS } from '@/stores/themeStore'
import { loadThemeFonts, type Theme, type ThemeMode } from '@/themes'
import { useEffect } from 'react'

// Mode icons and labels
const modeConfig: Record<ThemeMode, { icon: typeof Sun; label: string }> = {
  light: { icon: Sun, label: 'Light' },
  dark: { icon: Moon, label: 'Dark' },
  system: { icon: Monitor, label: 'System' },
}

// Style category icons/descriptions
const styleDescriptions: Record<Theme['style'], string> = {
  classic: 'Classic',
  scientific: 'Scientific',
  organic: 'Organic',
  natural: 'Natural',
  minimal: 'Minimal',
  vitreous: 'Vitreous',
  cartographic: 'Cartographic',
  editorial: 'Editorial',
  brand: 'Brand',
}

interface ThemeCardProps {
  theme: Theme
  isSelected: boolean
  onSelect: () => void
}

function ThemeCard({ theme, isSelected, onSelect }: ThemeCardProps) {
  // Preload fonts for preview
  useEffect(() => {
    loadThemeFonts(theme)
  }, [theme])

  return (
    <button
      onClick={onSelect}
      className={cn(
        'group relative flex flex-col overflow-hidden border-2 transition-all',
        'hover:shadow-lg hover:scale-[1.02] focus:outline-none',
        isSelected
          ? 'border-primary shadow-md'
          : 'border-border hover:border-primary/50'
      )}
      style={{ borderRadius: theme.preview.borderRadius }}
    >
      {/* Preview area - Shows theme personality */}
      <div
        className="relative h-24 w-full overflow-hidden p-3"
        style={{ backgroundColor: theme.preview.background }}
      >
        {/* Typography preview */}
        <div className="relative z-10 flex flex-col gap-1">
          <span
            className="text-base font-semibold leading-tight"
            style={{
              fontFamily: theme.preview.fontDisplay,
              color: theme.preview.primary,
            }}
          >
            {theme.name}
          </span>
          <span
            className="text-xs"
            style={{
              color: theme.preview.secondary,
              fontFamily: theme.preview.fontDisplay,
            }}
          >
            {styleDescriptions[theme.style]}
          </span>
        </div>

        {/* Shape preview - decorative elements */}
        <div className="absolute bottom-2 right-2 flex gap-1">
          {/* Primary color chip */}
          <div
            className="h-3.5 w-3.5"
            style={{
              backgroundColor: theme.preview.primary,
              borderRadius: theme.preview.borderRadius,
            }}
          />
          {/* Secondary color chip */}
          <div
            className="h-3.5 w-3.5"
            style={{
              backgroundColor: theme.preview.secondary,
              borderRadius: theme.preview.borderRadius,
            }}
          />
          {/* Accent color chip */}
          <div
            className="h-3.5 w-3.5"
            style={{
              backgroundColor: theme.preview.accent,
              borderRadius: theme.preview.borderRadius,
            }}
          />
        </div>

        {/* Selected indicator */}
        {isSelected && (
          <div
            className="absolute right-2 top-2 flex h-6 w-6 items-center justify-center shadow-md"
            style={{
              backgroundColor: theme.preview.primary,
              color: theme.preview.background,
              borderRadius: theme.preview.borderRadius === '0' ? '4px' : '9999px',
            }}
          >
            <Check className="h-4 w-4" />
          </div>
        )}
      </div>

      {/* Theme description */}
      <div
        className="flex flex-col gap-0.5 p-2.5 text-left"
        style={{ backgroundColor: theme.preview.background }}
      >
        <span
          className="text-xs line-clamp-2"
          style={{
            color: theme.preview.secondary,
          }}
        >
          {theme.description}
        </span>
      </div>
    </button>
  )
}

interface ModeSelectorProps {
  currentMode: ThemeMode
  onModeChange: (mode: ThemeMode) => void
}

function ModeSelector({ currentMode, onModeChange }: ModeSelectorProps) {
  const modes: ThemeMode[] = ['light', 'dark', 'system']

  return (
    <div className="flex gap-1 p-1 rounded-lg bg-muted">
      {modes.map((mode) => {
        const { icon: Icon, label } = modeConfig[mode]
        const isActive = currentMode === mode

        return (
          <button
            key={mode}
            onClick={() => onModeChange(mode)}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all',
              isActive
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <Icon className="h-4 w-4" />
            <span className="hidden sm:inline">{label}</span>
          </button>
        )
      })}
    </div>
  )
}

interface ThemeSwitcherProps {
  className?: string
  showModeSelector?: boolean
  columns?: 2 | 3 | 4
}

function FontSelector() {
  const { currentTheme, fontOverride, setFontOverride } = useTheme()

  // Resolve the active font: override or theme default
  const activeFont = fontOverride
    ?? currentTheme?.light.fontDisplay
    ?? AVAILABLE_FONTS[0].family

  // Find the matching font entry for the select value
  const selectedId = AVAILABLE_FONTS.find(f => activeFont.includes(f.name))?.id ?? ''

  return (
    <div className="flex items-center gap-3">
      <label className="text-sm font-medium text-muted-foreground whitespace-nowrap">
        Font
      </label>
      <select
        value={selectedId}
        onChange={(e) => {
          const font = AVAILABLE_FONTS.find(f => f.id === e.target.value)
          if (!font) return
          // If selecting the theme's default display font, clear the override
          const isDefault = currentTheme?.light.fontDisplay.includes(font.name)
          setFontOverride(isDefault ? null : font.family)
        }}
        className="flex-1 h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none"
        style={{ fontFamily: activeFont }}
      >
        <optgroup label="Sans-serif">
          {AVAILABLE_FONTS.filter(f => f.category === 'sans').map(font => (
            <option key={font.id} value={font.id} style={{ fontFamily: font.family }}>
              {font.name}{currentTheme?.light.fontDisplay.includes(font.name) ? ' (theme)' : ''}
            </option>
          ))}
        </optgroup>
        <optgroup label="Serif">
          {AVAILABLE_FONTS.filter(f => f.category === 'serif').map(font => (
            <option key={font.id} value={font.id} style={{ fontFamily: font.family }}>
              {font.name}{currentTheme?.light.fontDisplay.includes(font.name) ? ' (theme)' : ''}
            </option>
          ))}
        </optgroup>
        <optgroup label="Monospace">
          {AVAILABLE_FONTS.filter(f => f.category === 'mono').map(font => (
            <option key={font.id} value={font.id} style={{ fontFamily: font.family }}>
              {font.name}{currentTheme?.light.fontDisplay.includes(font.name) ? ' (theme)' : ''}
            </option>
          ))}
        </optgroup>
      </select>
    </div>
  )
}

export function ThemeSwitcher({
  className,
  showModeSelector = true,
  columns = 2,
}: ThemeSwitcherProps) {
  const { themes, themeId, mode, setTheme, setMode } = useTheme()

  const gridCols = {
    2: 'grid-cols-2',
    3: 'grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-2 lg:grid-cols-4',
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header with mode selector */}
      {showModeSelector && (
        <div className="flex justify-end">
          <ModeSelector currentMode={mode} onModeChange={setMode} />
        </div>
      )}

      {/* Theme grid */}
      <div className={cn('grid gap-4', gridCols[columns])}>
        {themes.map((theme) => (
          <ThemeCard
            key={theme.id}
            theme={theme}
            isSelected={themeId === theme.id}
            onSelect={() => setTheme(theme.id)}
          />
        ))}
      </div>

      {/* Font override selector */}
      <FontSelector />
    </div>
  )
}

// Compact version for toolbar/header
export function ThemeModeToggle({ className }: { className?: string }) {
  const { mode, cycleMode, resolvedMode } = useTheme()
  const Icon = resolvedMode === 'dark' ? Moon : Sun

  return (
    <button
      onClick={cycleMode}
      className={cn(
        'flex h-9 w-9 items-center justify-center rounded-md',
        'text-muted-foreground hover:text-foreground hover:bg-accent',
        'transition-colors focus:outline-none',
        className
      )}
      title={`Mode: ${modeConfig[mode].label}`}
    >
      <Icon className="h-5 w-5" />
    </button>
  )
}
