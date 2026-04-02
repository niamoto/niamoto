export type ReloadProjectState = 'loaded' | 'welcome' | 'invalid-project'

interface ReloadProjectPayload {
  success: boolean
  state: ReloadProjectState
  project: string | null
  message: string | null
}

interface ReloadProjectOptions {
  allowStates?: ReloadProjectState[]
  expectedProject?: string
}

function isReloadProjectState(value: unknown): value is ReloadProjectState {
  return (
    value === 'loaded' ||
    value === 'welcome' ||
    value === 'invalid-project'
  )
}

function isReloadProjectPayload(value: unknown): value is ReloadProjectPayload {
  if (typeof value !== 'object' || value === null) {
    return false
  }

  const payload = value as Record<string, unknown>
  return (
    typeof payload.success === 'boolean' &&
    isReloadProjectState(payload.state) &&
    (typeof payload.project === 'string' || payload.project === null) &&
    (typeof payload.message === 'string' ||
      payload.message === null ||
      payload.message === undefined)
  )
}

export async function reloadDesktopProject(
  options: ReloadProjectOptions = {}
): Promise<ReloadProjectPayload> {
  const response = await fetch('/api/health/reload-project', {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error('Failed to reload project on server')
  }

  const payload: unknown = await response.json()
  if (!isReloadProjectPayload(payload)) {
    throw new Error('Received an invalid reload-project response')
  }

  const result: ReloadProjectPayload = {
    ...payload,
    message: payload.message ?? null,
  }

  if (options.allowStates && !options.allowStates.includes(result.state)) {
    throw new Error(
      result.message ??
        `Unexpected project reload state returned by the server: ${result.state}`
    )
  }

  if (options.expectedProject) {
    if (result.state !== 'loaded' || result.project !== options.expectedProject) {
      throw new Error(
        result.message ?? 'Server failed to load the selected project'
      )
    }
  }

  return result
}
