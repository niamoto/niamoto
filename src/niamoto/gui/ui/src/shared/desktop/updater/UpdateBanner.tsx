import { useAppUpdater } from './useAppUpdater'

export function UpdateBanner() {
  const { status, version, progress, error, dismissed, installUpdate, dismiss, retry } = useAppUpdater()

  if (dismissed || status === 'idle' || status === 'checking') return null

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-blue-600 text-white text-sm shrink-0">
      {status === 'available' && (
        <>
          <span className="flex-1">Version {version} disponible</span>
          <button
            onClick={installUpdate}
            className="px-3 py-1 bg-white text-blue-600 rounded font-medium hover:bg-blue-50 transition-colors"
          >
            Mettre à jour
          </button>
          <button
            onClick={dismiss}
            className="p-1 hover:bg-blue-500 rounded transition-colors"
            aria-label="Fermer"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </>
      )}

      {status === 'downloading' && (
        <>
          <span className="flex-1">Mise à jour en cours...</span>
          <div className="w-32 h-2 bg-blue-400 rounded-full overflow-hidden">
            <div
              className="h-full bg-white rounded-full transition-all"
              style={{ width: `${progress ?? 0}%` }}
            />
          </div>
          <span className="tabular-nums">{progress ?? 0}%</span>
        </>
      )}

      {status === 'error' && (
        <>
          <span className="flex-1 text-red-200">{error}</span>
          <button
            onClick={retry}
            className="px-3 py-1 bg-white text-blue-600 rounded font-medium hover:bg-blue-50 transition-colors"
          >
            Réessayer
          </button>
          <button
            onClick={dismiss}
            className="p-1 hover:bg-blue-500 rounded transition-colors"
            aria-label="Fermer"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </>
      )}
    </div>
  )
}
