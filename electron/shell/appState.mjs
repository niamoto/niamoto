export function createShellState(paths) {
  return {
    mainWindow: null,
    paths,
    startupPromise: null,
    serverProcess: null,
    readyUrl: null,
    startupLogPath: null,
    startupSession: null,
  }
}

export function attachMainWindow(state, mainWindow) {
  state.mainWindow = mainWindow
  return state
}

export function detachMainWindow(state, mainWindow) {
  if (state.mainWindow === mainWindow) {
    state.mainWindow = null
  }

  return state
}

export function setBackendSession(state, session) {
  state.serverProcess = session.childProcess
  state.readyUrl = session.readyUrl
  state.startupLogPath = session.startupLogPath
  state.startupSession = session.startupSession
  return state
}

export function clearBackendSession(state) {
  state.serverProcess = null
  state.readyUrl = null
  state.startupLogPath = null
  state.startupSession = null
  return state
}
