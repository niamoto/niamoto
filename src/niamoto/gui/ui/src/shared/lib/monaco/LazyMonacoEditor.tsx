import { lazy, Suspense, type ReactNode } from 'react'
import type { EditorProps } from '@monaco-editor/react'
import { Loader2 } from 'lucide-react'
import { useThemeStore } from '@/stores/themeStore'

const MonacoEditor = lazy(() => import('@monaco-editor/react'))

interface LazyMonacoEditorProps extends EditorProps {
  suspenseFallback?: ReactNode
  useResolvedTheme?: boolean
}

export function LazyMonacoEditor({
  suspenseFallback,
  useResolvedTheme = true,
  height = '100%',
  theme,
  width = '100%',
  ...props
}: LazyMonacoEditorProps) {
  const resolvedMode = useThemeStore((state) => state.getResolvedMode())
  const resolvedTheme =
    theme ?? (useResolvedTheme ? (resolvedMode === 'dark' ? 'vs-dark' : 'light') : undefined)

  return (
    <Suspense
      fallback={
        suspenseFallback ?? (
          <div
            className="flex items-center justify-center text-muted-foreground"
            style={{ height, width }}
          >
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        )
      }
    >
      <MonacoEditor
        height={height}
        width={width}
        theme={resolvedTheme}
        {...props}
      />
    </Suspense>
  )
}
