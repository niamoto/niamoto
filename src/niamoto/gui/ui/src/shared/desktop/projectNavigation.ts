import { markManualProjectOpen } from './projectLaunchIntent'

export function openDesktopProjectFromHome(projectPath: string): void {
  markManualProjectOpen(projectPath)
  window.location.replace('/')
}
