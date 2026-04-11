import { cn } from '@/lib/utils'

interface SquareCascadeLoaderProps {
  className?: string
  squareClassName?: string
}

const delays = ['0s', '0.2s', '0.6s', '0.4s'] as const

export function SquareCascadeLoader({
  className,
  squareClassName,
}: SquareCascadeLoaderProps) {
  return (
    <span
      aria-hidden="true"
      className={cn('grid h-[23px] w-[23px] grid-cols-2 gap-[3px]', className)}
    >
      {delays.map((delay, index) => (
        <span
          key={index}
          className={cn(
            'h-[10px] w-[10px] rounded-[2px] bg-current [animation:niamoto-square-cascade_1.6s_ease-in-out_infinite]',
            squareClassName
          )}
          style={{ animationDelay: delay }}
        />
      ))}
    </span>
  )
}
