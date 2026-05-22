import { cn } from '@/lib/utils'
import { useTheme } from '@/stores/themeStore'
import { getNiamotoLogoSrc } from '@/shared/branding/niamotoLogo'

interface AppLoaderProps {
  className?: string
  logoClassName?: string
  loaderClassName?: string
}

export function AppLoader({
  className,
  logoClassName,
  loaderClassName,
}: AppLoaderProps) {
  const { resolvedMode } = useTheme()
  const logoSrc = getNiamotoLogoSrc(resolvedMode)

  return (
    <div className={cn('niamoto-app-loader-shell', className)}>
      <img
        src={logoSrc}
        alt=""
        className={cn(
          'niamoto-brand-logo niamoto-app-loader-logo',
          resolvedMode === 'dark' && 'niamoto-brand-logo--dark',
          logoClassName
        )}
        draggable={false}
      />
      <div
        aria-hidden="true"
        className={cn('niamoto-app-loader niamoto-app-loader--pulse-ring', loaderClassName)}
      />
    </div>
  )
}
