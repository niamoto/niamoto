import { cn } from '@/lib/utils'
import { FacetedSpinner } from './faceted-spinner'

interface CircularProgressProps {
  value?: number
  size?: number
  strokeWidth?: number
  className?: string
  showValue?: boolean
  color?: string
  indeterminate?: boolean
}

export function CircularProgress({
  value = 0,
  size = 40,
  strokeWidth = 3,
  className,
  showValue = true,
  color = 'text-primary',
  indeterminate = false
}: CircularProgressProps) {
  // If indeterminate, show the faceted spinner
  if (indeterminate) {
    return <FacetedSpinner
      size='sm'
      color="#82a33d"
      className={className}
    />
  }
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (value / 100) * circumference

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          className="text-muted-foreground/20"
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className={cn("transition-all duration-500 ease-in-out", color)}
          strokeLinecap="round"
        />
      </svg>
      {showValue && (
        <span className="absolute text-xs font-medium">
          {Math.round(value)}%
        </span>
      )}
    </div>
  )
}
