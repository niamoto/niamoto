import { useEffect, useState } from 'react'

interface PreviewVisibilityOptions {
  rootMargin?: string
  threshold?: number | number[]
  freezeOnceVisible?: boolean
}

export function usePreviewVisibility(
  ref: React.RefObject<HTMLElement | null>,
  options?: PreviewVisibilityOptions,
): boolean {
  const [isVisible, setIsVisible] = useState(false)
  const rootMargin = options?.rootMargin ?? '240px'
  const threshold = options?.threshold ?? 0
  const freezeOnceVisible = options?.freezeOnceVisible ?? false

  useEffect(() => {
    const element = ref.current
    if (!element) {
      return
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) {
          if (!freezeOnceVisible) {
            setIsVisible(false)
          }
          return
        }

        setIsVisible(true)
        if (freezeOnceVisible) {
          observer.disconnect()
        }
      },
      { rootMargin, threshold },
    )

    observer.observe(element)
    return () => observer.disconnect()
  }, [freezeOnceVisible, ref, rootMargin, threshold])

  return isVisible
}
