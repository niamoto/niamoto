import { useState, useEffect } from 'react'

/**
 * Hook for progressive counter animation
 * @param target - Target value to count to
 * @param duration - Duration of animation in milliseconds
 * @param startOnMount - Whether to start animation on mount
 * @returns Object with current value, animation state, and start function
 */
export function useProgressiveCounter(
  target: number,
  duration: number = 2000,
  startOnMount: boolean = true
) {
  const [value, setValue] = useState(0)
  const [isAnimating, setIsAnimating] = useState(false)
  const [hasAnimated, setHasAnimated] = useState(false)

  const start = () => {
    setValue(0)
    setIsAnimating(true)
    setHasAnimated(false)
  }

  useEffect(() => {
    // Only animate once if startOnMount is true
    if (hasAnimated) return
    if (!startOnMount && !isAnimating) return

    const startTime = Date.now()
    let animationId: number

    const step = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)

      // Easing function for smooth animation
      const easeOutQuart = 1 - Math.pow(1 - progress, 4)
      const currentValue = Math.floor(target * easeOutQuart)

      setValue(currentValue)

      if (progress < 1) {
        animationId = requestAnimationFrame(step)
      } else {
        setValue(target)
        setIsAnimating(false)
        setHasAnimated(true)
      }
    }

    setIsAnimating(true)
    animationId = requestAnimationFrame(step)

    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId)
      }
    }
  }, [target, duration, startOnMount, hasAnimated])

  return { value, isAnimating, start }
}
