import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// Build job types
export interface BuildJob {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  message: string
  startedAt: string
  completedAt?: string
  metrics?: {
    totalFiles: number
    duration: number
    targets: { name: string; files: number }[]
  }
  error?: string
}

// Deploy job types
export type DeployPlatform = 'cloudflare' | 'github' | 'netlify' | 'vercel' | 'render' | 'ssh'

export interface DeployJob {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  platform: DeployPlatform
  projectName: string
  branch?: string
  logs: string[]
  deploymentUrl?: string
  startedAt: string
  completedAt?: string
  error?: string
  buildJobId?: string // Link to the build that was deployed
}

// Platform configurations
export interface CloudflareConfig {
  projectName: string
  defaultBranch?: string
}

export interface GithubConfig {
  repo: string
  branch: string
  name?: string
  email?: string
}

export interface NetlifyConfig {
  siteId: string
}

export interface VercelConfig {
  projectName: string
}

export interface RenderConfig {
  serviceId?: string
  deployHookUrl?: string
}

export interface SshConfig {
  host: string
  path: string
  port: number
  keyPath?: string
}

export interface PlatformConfig {
  cloudflare?: CloudflareConfig
  github?: GithubConfig
  netlify?: NetlifyConfig
  vercel?: VercelConfig
  render?: RenderConfig
  ssh?: SshConfig
}

interface PublishState {
  // Current operations
  currentBuild: BuildJob | null
  currentDeploy: DeployJob | null

  // History (persisted)
  buildHistory: BuildJob[]
  deployHistory: DeployJob[]

  // Platform configurations (persisted)
  platformConfigs: PlatformConfig
  preferredPlatform: DeployPlatform | null

  // Build actions
  startBuild: () => BuildJob
  updateBuild: (updates: Partial<BuildJob>) => void
  completeBuild: (metrics?: BuildJob['metrics'], error?: string) => void
  cancelBuild: () => void

  // Deploy actions
  startDeploy: (platform: DeployPlatform, projectName: string, branch?: string) => DeployJob
  appendDeployLog: (log: string) => void
  setDeploymentUrl: (url: string) => void
  completeDeploy: (error?: string) => void
  cancelDeploy: () => void

  // Platform config actions
  savePlatformConfig: <T extends keyof PlatformConfig>(
    platform: T,
    config: PlatformConfig[T]
  ) => void
  deletePlatformConfig: (platform: DeployPlatform) => void
  setPreferredPlatform: (platform: PublishState['preferredPlatform']) => void

  // History management
  clearBuildHistory: () => void
  clearDeployHistory: () => void
  getLastSuccessfulBuild: () => BuildJob | null
  getLastSuccessfulDeploy: () => DeployJob | null

  // Cleanup
  cleanupOrphanDeploys: () => void
}

// Generate unique ID
const generateId = () => `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`

export const usePublishStore = create<PublishState>()(
  persist(
    (set, get) => ({
      // Initial state
      currentBuild: null,
      currentDeploy: null,
      buildHistory: [],
      deployHistory: [],
      platformConfigs: {},
      preferredPlatform: null,

      // Build actions
      startBuild: () => {
        const newBuild: BuildJob = {
          id: generateId(),
          status: 'running',
          progress: 0,
          message: 'Initialisation...',
          startedAt: new Date().toISOString(),
        }
        set({ currentBuild: newBuild })
        return newBuild
      },

      updateBuild: (updates) => {
        set((state) => {
          if (!state.currentBuild) return state
          return {
            currentBuild: { ...state.currentBuild, ...updates }
          }
        })
      },

      completeBuild: (metrics, error) => {
        set((state) => {
          if (!state.currentBuild) return state
          const completedBuild: BuildJob = {
            ...state.currentBuild,
            status: error ? 'failed' : 'completed',
            progress: error ? state.currentBuild.progress : 100,
            completedAt: new Date().toISOString(),
            metrics,
            error,
          }
          return {
            currentBuild: null,
            buildHistory: [completedBuild, ...state.buildHistory].slice(0, 50) // Keep last 50
          }
        })
      },

      cancelBuild: () => {
        set((state) => {
          if (!state.currentBuild) return state
          const cancelledBuild: BuildJob = {
            ...state.currentBuild,
            status: 'cancelled',
            completedAt: new Date().toISOString(),
          }
          return {
            currentBuild: null,
            buildHistory: [cancelledBuild, ...state.buildHistory].slice(0, 50)
          }
        })
      },

      // Deploy actions
      startDeploy: (platform, projectName, branch) => {
        const lastBuild = get().buildHistory.find(b => b.status === 'completed')
        const newDeploy: DeployJob = {
          id: generateId(),
          status: 'running',
          platform,
          projectName,
          branch,
          logs: [],
          startedAt: new Date().toISOString(),
          buildJobId: lastBuild?.id,
        }
        set({ currentDeploy: newDeploy })
        return newDeploy
      },

      appendDeployLog: (log) => {
        set((state) => {
          if (!state.currentDeploy) return state
          return {
            currentDeploy: {
              ...state.currentDeploy,
              logs: [...state.currentDeploy.logs, log]
            }
          }
        })
      },

      setDeploymentUrl: (url) => {
        set((state) => {
          if (!state.currentDeploy) return state
          return {
            currentDeploy: {
              ...state.currentDeploy,
              deploymentUrl: url
            }
          }
        })
      },

      completeDeploy: (error) => {
        set((state) => {
          if (!state.currentDeploy) return state
          const completedDeploy: DeployJob = {
            ...state.currentDeploy,
            status: error ? 'failed' : 'completed',
            completedAt: new Date().toISOString(),
            error,
          }
          return {
            currentDeploy: null,
            deployHistory: [completedDeploy, ...state.deployHistory].slice(0, 50)
          }
        })
      },

      cancelDeploy: () => {
        set((state) => {
          if (!state.currentDeploy) return state
          const cancelledDeploy: DeployJob = {
            ...state.currentDeploy,
            status: 'failed',
            completedAt: new Date().toISOString(),
            error: 'Cancelled by user',
          }
          return {
            currentDeploy: null,
            deployHistory: [cancelledDeploy, ...state.deployHistory].slice(0, 50)
          }
        })
      },

      // Platform config actions
      savePlatformConfig: (platform, config) => {
        set((state) => ({
          platformConfigs: {
            ...state.platformConfigs,
            [platform]: config
          }
        }))
      },

      deletePlatformConfig: (platform) => {
        set((state) => {
          const { [platform]: _, ...rest } = state.platformConfigs
          return {
            platformConfigs: rest,
            preferredPlatform: state.preferredPlatform === platform ? null : state.preferredPlatform,
          }
        })
      },

      setPreferredPlatform: (platform) => {
        set({ preferredPlatform: platform })
      },

      // History management
      clearBuildHistory: () => set({ buildHistory: [] }),
      clearDeployHistory: () => set({ deployHistory: [] }),

      getLastSuccessfulBuild: () => {
        return get().buildHistory.find(b => b.status === 'completed') || null
      },

      getLastSuccessfulDeploy: () => {
        return get().deployHistory.find(d => d.status === 'completed') || null
      },

      cleanupOrphanDeploys: () => {
        set((state) => {
          // If there's a "running" deploy with no active connection, mark as failed
          if (state.currentDeploy?.status === 'running') {
            const orphaned: DeployJob = {
              ...state.currentDeploy,
              status: 'failed',
              completedAt: new Date().toISOString(),
              error: 'Interrupted by application restart',
            }
            return {
              currentDeploy: null,
              deployHistory: [orphaned, ...state.deployHistory].slice(0, 50),
            }
          }
          return state
        })
      },
    }),
    {
      name: 'publish-storage',
      partialize: (state) => ({
        buildHistory: state.buildHistory,
        deployHistory: state.deployHistory,
        platformConfigs: state.platformConfigs,
        preferredPlatform: state.preferredPlatform,
      })
    }
  )
)

// Selectors
export const selectIsBuilding = (state: PublishState) =>
  state.currentBuild !== null && state.currentBuild.status === 'running'

export const selectIsDeploying = (state: PublishState) =>
  state.currentDeploy !== null && state.currentDeploy.status === 'running'

export const selectHasSuccessfulBuild = (state: PublishState) =>
  state.buildHistory.some(b => b.status === 'completed')

export const selectLastBuildStatus = (state: PublishState) =>
  state.buildHistory[0]?.status || null

export const selectLastDeployStatus = (state: PublishState) =>
  state.deployHistory[0]?.status || null
