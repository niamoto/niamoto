import type { DownloadEvent } from '@tauri-apps/plugin-updater'

export interface DownloadProgressState {
  downloadedBytes: number
  totalBytes: number
  status: 'downloading' | 'installing'
  progress?: number
  label: string
}

interface DownloadProgressOptions {
  isLinux: boolean
  isWindows: boolean
}

export function createInitialDownloadProgressState(): DownloadProgressState {
  return {
    downloadedBytes: 0,
    totalBytes: 0,
    status: 'downloading',
    progress: undefined,
    label: 'Téléchargement de la mise à jour...',
  }
}

export function reduceDownloadProgressEvent(
  state: DownloadProgressState,
  event: DownloadEvent,
  options: DownloadProgressOptions
): DownloadProgressState {
  const usePercentage = !options.isLinux && !options.isWindows

  if (event.event === 'Started') {
    const totalBytes = event.data.contentLength ?? 0
    return {
      downloadedBytes: 0,
      totalBytes,
      status: 'downloading',
      progress: usePercentage && totalBytes > 0 ? 0 : undefined,
      label:
        options.isLinux
          ? 'Préparation de la mise à jour... une authentification système peut être requise.'
          : options.isWindows
          ? 'Téléchargement de la mise à jour... le programme d’installation Windows prendra le relais.'
          : totalBytes > 0
          ? 'Téléchargement de la mise à jour... 0%'
          : 'Téléchargement de la mise à jour...',
    }
  }

  if (event.event === 'Progress') {
    const downloadedBytes = state.downloadedBytes + event.data.chunkLength

    if (usePercentage && state.totalBytes > 0) {
      const progress = Math.min(100, Math.round((downloadedBytes / state.totalBytes) * 100))
      return {
        downloadedBytes,
        totalBytes: state.totalBytes,
        status: 'downloading',
        progress,
        label: `Téléchargement de la mise à jour... ${progress}%`,
      }
    }

    return {
      downloadedBytes,
      totalBytes: state.totalBytes,
      status: 'downloading',
      progress: undefined,
      label:
        options.isLinux || options.isWindows
          ? 'Téléchargement de la mise à jour...'
          : `Téléchargement de la mise à jour... ${formatBytes(downloadedBytes)}`,
    }
  }

  return {
    downloadedBytes: state.downloadedBytes,
    totalBytes: state.totalBytes,
    status: 'installing',
    progress: usePercentage && state.totalBytes > 0 ? 100 : undefined,
    label: options.isLinux
      ? 'Téléchargement terminé. Validation système et installation en cours...'
      : options.isWindows
      ? 'Téléchargement terminé. Le programme d’installation Windows termine la mise à jour...'
      : 'Téléchargement terminé. Installation en cours...',
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
