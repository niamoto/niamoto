/**
 * Theme Switcher - Visual theme selection component
 *
 * A beautiful gallery-style theme picker with live previews
 * showing typography, shapes, and colors distinctive to each theme.
 */

import { Moon, Sun, Monitor, Check, Palette } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useTheme } from '@/stores/themeStore'
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
        'hover:shadow-lg hover:scale-[1.02] focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        isSelected
          ? 'border-primary shadow-md'
          : 'border-border hover:border-primary/50'
      )}
      style={{ borderRadius: theme.preview.borderRadius }}
    >
      {/* Preview area - Shows theme personality */}
      <div
        className="relative h-28 w-full overflow-hidden p-4"
        style={{ backgroundColor: theme.preview.background }}
      >
        {/* Typography preview */}
        <div className="relative z-10 flex flex-col gap-1">
          <span
            className="text-lg font-semibold leading-tight"
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
        <div className="absolute bottom-2 right-2 flex gap-1.5">
          {/* Primary color chip */}
          <div
            className="h-4 w-4"
            style={{
              backgroundColor: theme.preview.primary,
              borderRadius: theme.preview.borderRadius,
            }}
          />
          {/* Secondary color chip */}
          <div
            className="h-4 w-4"
            style={{
              backgroundColor: theme.preview.secondary,
              borderRadius: theme.preview.borderRadius,
            }}
          />
          {/* Accent color chip */}
          <div
            className="h-4 w-4"
            style={{
              backgroundColor: theme.preview.accent,
              borderRadius: theme.preview.borderRadius,
            }}
          />
        </div>

        {/* Background decoration based on style */}
        <div className="absolute inset-0 opacity-10">
          {theme.style === 'scientific' && (
            <svg className="h-full w-full" viewBox="0 0 100 100">
              {/* Grid pattern */}
              {[...Array(10)].map((_, i) => (
                <line
                  key={`h${i}`}
                  x1="0"
                  y1={i * 10}
                  x2="100"
                  y2={i * 10}
                  stroke={theme.preview.primary}
                  strokeWidth="0.5"
                />
              ))}
              {[...Array(10)].map((_, i) => (
                <line
                  key={`v${i}`}
                  x1={i * 10}
                  y1="0"
                  x2={i * 10}
                  y2="100"
                  stroke={theme.preview.primary}
                  strokeWidth="0.5"
                />
              ))}
            </svg>
          )}
          {theme.style === 'classic' && (
            <svg className="h-full w-full" viewBox="0 0 100 100">
              {/* Botanical border hint */}
              <rect
                x="5"
                y="5"
                width="90"
                height="90"
                fill="none"
                stroke={theme.preview.primary}
                strokeWidth="1"
              />
              <rect
                x="8"
                y="8"
                width="84"
                height="84"
                fill="none"
                stroke={theme.preview.primary}
                strokeWidth="0.5"
              />
            </svg>
          )}
          {theme.style === 'organic' && (
            <svg className="h-full w-full" viewBox="0 0 100 100">
              {/* Sketch lines */}
              <path
                d="M10 80 Q 30 70, 50 75 T 90 70"
                fill="none"
                stroke={theme.preview.primary}
                strokeWidth="1"
              />
              <path
                d="M15 85 Q 35 75, 55 80 T 95 75"
                fill="none"
                stroke={theme.preview.primary}
                strokeWidth="0.5"
              />
            </svg>
          )}
          {theme.style === 'natural' && (
            <svg className="h-full w-full" viewBox="0 0 100 100">
              {/* Organic shapes */}
              <circle cx="80" cy="20" r="15" fill={theme.preview.accent} />
              <ellipse
                cx="50"
                cy="90"
                rx="40"
                ry="15"
                fill={theme.preview.primary}
              />
            </svg>
          )}
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
        className="flex flex-col gap-0.5 p-3 text-left"
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
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Palette className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Appearance</span>
          </div>
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
        'transition-colors focus:outline-none focus:ring-2 focus:ring-ring',
        className
      )}
      title={`Mode: ${modeConfig[mode].label}`}
    >
      <Icon className="h-5 w-5" />
    </button>
  )
}
