/**
 * Affichage d'erreur pour les previews widgets.
 */

interface PreviewErrorProps {
  message: string
  compact?: boolean
}

export function PreviewError({ message, compact = false }: PreviewErrorProps) {
  if (compact) {
    return (
      <div className="flex items-center justify-center w-full h-full bg-red-50 rounded">
        <span className="text-red-400 text-xs" title={message}>
          Erreur
        </span>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center w-full h-full bg-red-50 rounded p-3 gap-1">
      <svg
        className="w-5 h-5 text-red-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
        />
      </svg>
      <span className="text-red-500 text-xs text-center">{message}</span>
    </div>
  )
}
