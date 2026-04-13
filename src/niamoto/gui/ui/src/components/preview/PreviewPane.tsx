/**
 * Vue complète de preview widget (mode full).
 *
 * Utilisé dans les panneaux de détail et l'éditeur.
 * Observe les changements de taille du conteneur (ex: colspan toggle)
 * et force un re-mount de l'iframe pour que Plotly se recalcule.
 */

import { useRef, useState, useEffect } from 'react'
import type { PreviewDescriptor } from '@/lib/preview/types'
import { usePreviewFrame } from '@/lib/preview/usePreviewFrame'
import { PreviewSkeleton } from './PreviewSkeleton'
import { PreviewError } from './PreviewError'
import { usePreviewVisibility } from './usePreviewVisibility'

interface PreviewPaneProps {
  descriptor: PreviewDescriptor
  className?: string
  /** Optional transform applied to the HTML before rendering in the iframe */
  transformHtml?: (html: string) => string
}

export function PreviewPane({ descriptor, className, transformHtml }: PreviewPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const shouldLoad = usePreviewVisibility(containerRef)
  const usesResponsiveResize = descriptor.mode === 'full'

  // Compteur incrémenté à chaque changement de largeur du conteneur
  // pour forcer un re-mount de l'iframe (Plotly re-render à la bonne taille).
  const [resizeKey, setResizeKey] = useState(0)
  const widthRef = useRef<number>(0)

  useEffect(() => {
    if (!usesResponsiveResize) {
      return
    }

    const el = containerRef.current
    if (!el) return

    const observer = new ResizeObserver((entries) => {
      const w = Math.round(entries[0].contentRect.width)
      const bucket = Math.round(w / 24)
      if (widthRef.current !== 0 && bucket !== widthRef.current) {
        setResizeKey((k) => k + 1)
      }
      widthRef.current = bucket
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [usesResponsiveResize])

  const { html, loading, error } = usePreviewFrame(descriptor, shouldLoad)

  // Nettoyage Plotly au démontage
  useEffect(() => {
    const iframe = iframeRef.current
    return () => {
      if (iframe) {
        iframe.srcdoc = ''
      }
    }
  }, [html, resizeKey])

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        contentVisibility: 'auto',
        containIntrinsicSize: '320px 240px',
      }}
    >
      {(!shouldLoad || loading) && (
        <PreviewSkeleton
          descriptor={descriptor}
          compact={descriptor.mode === 'thumbnail'}
        />
      )}
      {error && !loading && <PreviewError message={error} />}
      {html && !loading && (
        <iframe
          key={resizeKey}
          ref={iframeRef}
          srcDoc={transformHtml ? transformHtml(html) : html}
          title="Widget preview"
          sandbox="allow-scripts"
          loading="lazy"
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
          }}
        />
      )}
    </div>
  )
}
