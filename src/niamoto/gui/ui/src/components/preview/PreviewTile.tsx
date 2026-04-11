/**
 * Miniature de preview widget pour les grilles.
 *
 * Utilise IntersectionObserver pour le lazy loading
 * et usePreviewFrame pour le chargement via TanStack Query.
 */

import { useRef, useState, useEffect } from 'react'
import type { PreviewDescriptor } from '@/lib/preview/types'
import { usePreviewFrame } from '@/lib/preview/usePreviewFrame'
import { PreviewSkeleton } from './PreviewSkeleton'
import { PreviewError } from './PreviewError'
import { usePreviewVisibility } from './usePreviewVisibility'

interface PreviewTileProps {
  descriptor: PreviewDescriptor
  width?: number
  height?: number
  className?: string
}

export function PreviewTile({
  descriptor,
  width = 120,
  height = 90,
  className,
}: PreviewTileProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const visible = usePreviewVisibility(containerRef, { rootMargin: '120px' })

  // Stabiliser le descriptor pour éviter les re-renders
  const thumbDescriptor = { ...descriptor, mode: 'thumbnail' as const }

  // Debounce la visibilité pour éviter le strobe au scroll rapide
  const [debouncedVisible, setDebouncedVisible] = useState(false)
  useEffect(() => {
    const timeoutId = window.setTimeout(
      () => setDebouncedVisible(visible),
      visible ? 0 : 32,
    )
    return () => window.clearTimeout(timeoutId)
  }, [visible])

  const { html, loading, error } = usePreviewFrame(thumbDescriptor, debouncedVisible)

  // Nettoyage Plotly au démontage — on lit la ref au cleanup car l'iframe
  // est rendue conditionnellement et n'existe pas encore au mount.
  useEffect(() => {
    const iframe = iframeRef.current
    return () => {
      if (iframe) {
        iframe.srcdoc = ''
      }
    }
  }, [html])

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
            pointerEvents: 'none',
          }}
        />
      )}
    </div>
  )
}
