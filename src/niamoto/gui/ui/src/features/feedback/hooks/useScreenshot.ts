import { useState, useCallback } from 'react'

const MAX_SIZE = 5 * 1024 * 1024 // 5MB

export function useScreenshot() {
  const [screenshot, setScreenshot] = useState<Blob | null>(null)
  const [isCapturing, setIsCapturing] = useState(false)
  const [error, setError] = useState(false)

  const capture = useCallback(async () => {
    setIsCapturing(true)
    setError(false)
    try {
      const { default: html2canvas } = await import('html2canvas')
      const canvas = await html2canvas(document.body, {
        useCORS: true,
        scale: 1, // Force 1x to avoid >5MB on Retina displays
        logging: false,
      })

      let blob = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob(resolve, 'image/jpeg', 0.7)
      )

      // Fallback: lower quality if still too large
      if (blob && blob.size > MAX_SIZE) {
        blob = await new Promise<Blob | null>((resolve) =>
          canvas.toBlob(resolve, 'image/jpeg', 0.4)
        )
      }

      // Drop if still too large
      if (blob && blob.size > MAX_SIZE) {
        setError(true)
        setScreenshot(null)
      } else {
        setScreenshot(blob)
      }
    } catch {
      setError(true)
      setScreenshot(null)
    } finally {
      setIsCapturing(false)
    }
  }, [])

  const clear = useCallback(() => {
    setScreenshot(null)
    setError(false)
  }, [])

  return { screenshot, isCapturing, error, capture, clear }
}
