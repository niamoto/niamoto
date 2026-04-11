import { useEffect, useState } from 'react'

interface PreviewVisibilityOptions {
  rootMargin?: string
  threshold?: number | number[]
}

export function usePreviewVisibility(
  ref: React.RefObject<HTMLElement | null>,
  options?: PreviewVisibilityOptions,
): boolean {
  const [isVisible, setIsVisible] = useState(false)
  const [hasBeenVisible, setHasBeenVisible] = useState(false)
  const rootMargin = options?.rootMargin ?? '240px'
  const threshold = options?.threshold ?? 0

  useEffect(() => {
    const element = ref.current
    if (!element || hasBeenVisible) {
      return
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) {
          setIsVisible(false)
          return
        }

        setIsVisible(true)
        setHasBeenVisible(true)
        observer.disconnect()
      },
      { rootMargin, threshold },
    )

    observer.observe(element)
    return () => observer.disconnect()
  }, [hasBeenVisible, ref, rootMargin, threshold])

  return hasBeenVisible || isVisible
}
