/**
 * Miniature de preview widget pour les grilles.
 *
 * Utilise IntersectionObserver pour le lazy loading
 * et usePreviewFrame pour le chargement via TanStack Query.
 */

import { useRef, useState, useEffect, useMemo } from 'react'
import type { PreviewDescriptor } from '@/lib/preview/types'
import { usePreviewFrame, descriptorDeps } from '@/lib/preview/usePreviewFrame'
import { PreviewSkeleton } from './PreviewSkeleton'
import { PreviewError } from './PreviewError'

interface PreviewTileProps {
  descriptor: PreviewDescriptor
  width?: number
  height?: number
  className?: string
}

function useIntersectionObserver(
  ref: React.RefObject<HTMLElement | null>,
  options?: IntersectionObserverInit,
): boolean {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting),
      { rootMargin: '120px', ...options },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [ref, options?.rootMargin, options?.threshold])

  return visible
}

export function PreviewTile({
  descriptor,
  width = 120,
  height = 90,
  className,
}: PreviewTileProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const visible = useIntersectionObserver(containerRef)

  // Stabiliser le descriptor pour éviter les re-renders
  const thumbDescriptor = useMemo(
    () => ({ ...descriptor, mode: 'thumbnail' as const }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    descriptorDeps(descriptor),
  )

  // Debounce la visibilité pour éviter le strobe au scroll rapide
  const [debouncedVisible, setDebouncedVisible] = useState(false)
  useEffect(() => {
    if (visible) {
      setDebouncedVisible(true)
    } else {
      const t = setTimeout(() => setDebouncedVisible(false), 32)
      return () => clearTimeout(t)
    }
  }, [visible])

  const { html, loading, error } = usePreviewFrame(thumbDescriptor, debouncedVisible)

  // Nettoyage Plotly au démontage — on lit la ref au cleanup car l'iframe
  // est rendue conditionnellement et n'existe pas encore au mount.
  useEffect(() => {
    return () => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      if (iframeRef.current) {
        iframeRef.current.srcdoc = ''
      }
    }
  }, [])

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        width,
        height,
        contentVisibility: 'auto',
        containIntrinsicSize: `${width}px ${height}px`,
      }}
    >
      {loading && <PreviewSkeleton width={width} height={height} compact descriptor={thumbDescriptor} />}
      {error && !loading && <PreviewError message={error} compact />}
      {html && !loading && (
        <iframe
          ref={iframeRef}
          srcDoc={html}
          title="Widget preview"
          sandbox="allow-scripts"
          style={{
            width: 400,
            height: 300,
            transform: `scale(${width / 400})`,
            transformOrigin: '0 0',
            border: 'none',
          }}
        />
      )}
    </div>
  )
}
