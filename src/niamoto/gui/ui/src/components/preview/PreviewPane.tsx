/**
 * Vue complète de preview widget (mode full).
 *
 * Utilisé dans les panneaux de détail et l'éditeur.
 */

import { useRef, useEffect, useMemo } from 'react'
import type { PreviewDescriptor } from '@/lib/preview/types'
import { usePreviewFrame } from '@/lib/preview/usePreviewFrame'
import { PreviewSkeleton } from './PreviewSkeleton'
import { PreviewError } from './PreviewError'

interface PreviewPaneProps {
  descriptor: PreviewDescriptor
  className?: string
}

export function PreviewPane({ descriptor, className }: PreviewPaneProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)

  const fullDescriptor = useMemo(
    () => ({ ...descriptor, mode: 'full' as const }),
    [descriptor.templateId, descriptor.groupBy, descriptor.source, descriptor.entityId,
     descriptor.inline ? JSON.stringify(descriptor.inline, Object.keys(descriptor.inline).sort()) : null],
  )

  const { html, loading, error } = usePreviewFrame(fullDescriptor, true)

  // Nettoyage Plotly au démontage
  useEffect(() => {
    return () => {
      if (iframeRef.current) {
        iframeRef.current.srcdoc = ''
      }
    }
  }, [])

  return (
    <div className={className}>
      {loading && <PreviewSkeleton width={400} height={300} />}
      {error && <PreviewError message={error} />}
      {html && (
        <iframe
          ref={iframeRef}
          srcDoc={html}
          title="Widget preview"
          sandbox="allow-scripts"
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
