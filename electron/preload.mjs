import { contextBridge, ipcRenderer } from 'electron'

const IPC_CHANNEL = 'niamoto:desktop-command'

contextBridge.exposeInMainWorld('__NIAMOTO_ELECTRON__', {
  invoke(command, args) {
    return ipcRenderer.invoke(IPC_CHANNEL, {
      command,
      args,
    })
  },
})
