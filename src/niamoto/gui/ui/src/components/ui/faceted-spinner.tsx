import { cn } from '@/lib/utils'

interface FacetedSpinnerProps {
  className?: string
  size?: 'sm' | 'md' | 'lg'
  color?: 'primary' | 'green' | string
}

export function FacetedSpinner({ className, size = 'md', color = 'primary' }: FacetedSpinnerProps) {
  const gridSize = 3 // 3x3 grid
  const cellCount = gridSize * gridSize

  const containerSizes = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  }

  const cellSizes = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-3 h-3'
  }

  const gaps = {
    sm: 'gap-0.5',
    md: 'gap-0.5',
    lg: 'gap-1'
  }

  const colorClasses = {
    primary: 'bg-primary',
    green: 'bg-green-500'
  }

  // Random animation delays for organic feel
  const animationDelays = [0, 0.2, 0.1, 0.3, 0.4, 0.2, 0.5, 0.3, 0.6]

  // Check if color is a hex value
  const isHexColor = color.startsWith('#')
  const bgColorClass = isHexColor ? undefined : colorClasses[color as keyof typeof colorClasses]
  const bgColorStyle = isHexColor ? { backgroundColor: color } : undefined

  return (
    <div className={cn('relative', containerSizes[size], className)}>
      {/* Add custom animation styles */}
      <style>{`
        @keyframes gridPulse {
          0% {
            transform: scale(1);
            opacity: 1;
          }
          50% {
            transform: scale(0.3);
            opacity: 0.2;
          }
          100% {
            transform: scale(1);
            opacity: 1;
          }
        }

        .grid-animate {
          animation: gridPulse 1.3s ease-in-out infinite;
        }
      `}</style>

      {/* Create a grid of squares */}
      <div className={cn('grid grid-cols-3', gaps[size], 'h-full w-full')}>
        {[...Array(cellCount)].map((_, index) => (
          <div
            key={index}
            className={cn(
              cellSizes[size],
              bgColorClass,
              'rounded-sm grid-animate'
            )}
            style={{
              animationDelay: `${animationDelays[index]}s`,
              ...bgColorStyle
            }}
          />
        ))}
      </div>
    </div>
  )
}
