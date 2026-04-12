import niamotoLogo from '@/assets/niamoto_logo.png'
import { cn } from '@/lib/utils'

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
  return (
    <div className={cn('niamoto-app-loader-shell', className)}>
      <img
        src={niamotoLogo}
        alt=""
        className={cn('niamoto-app-loader-logo', logoClassName)}
        draggable={false}
      />
      <div
        aria-hidden="true"
        className={cn('niamoto-app-loader niamoto-app-loader--pulse-ring', loaderClassName)}
      />
    </div>
  )
}
