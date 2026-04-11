import { useState, useEffect, useCallback } from 'react';
import { reloadDesktopProject } from '@/shared/desktop/projectReload';
import {
  getManualProjectOpenTarget,
  markManualProjectOpen,
} from '@/shared/desktop/projectLaunchIntent';
import {
  DEFAULT_APP_SETTINGS,
  getAppSettings,
  setAppSettings as persistAppSettings,
  type AppSettings,
} from '@/shared/desktop/appSettings';
import { invokeDesktop } from '@/shared/desktop/tauri';
import { useProjectSwitcher } from '@/shared/hooks/useProjectSwitcher';

interface WelcomeScreenState {
  showWelcome: boolean;
  loading: boolean;
  error: string | null;
  settings: AppSettings;
}

/**
 * Hook to manage the welcome screen flow in desktop mode.
 * Handles auto-loading of last project and project creation.
 */
export function useWelcomeScreen() {
  const {
    currentProject,
    hasInvalidCurrentProject,
    recentProjects,
    invalidProjects,
    loading: projectsLoading,
    isTauri,
    switchProject,
    browseProject,
    removeProject,
    reload: reloadProjects,
  } = useProjectSwitcher();

  const [state, setState] = useState<WelcomeScreenState>({
    showWelcome: false,
    loading: true,
    error: null,
    settings: DEFAULT_APP_SETTINGS,
  });

  // Invoke Tauri command
  const invoke = useCallback(
    async <T,>(cmd: string, args?: Record<string, unknown>): Promise<T> => {
      if (!isTauri) {
        throw new Error('Tauri commands only available in desktop mode');
      }
      return invokeDesktop<T>(cmd, args);
    },
    [isTauri]
  );

  // Initialize and determine if we should show welcome screen
  useEffect(() => {
    // Skip for web mode
    if (!isTauri) {
      setState((s) => ({ ...s, showWelcome: false, loading: false }));
      return;
    }

    // Wait for projects to load
    if (projectsLoading) {
      return;
    }

    const initialize = async () => {
      try {
        // Get app settings
        const settings = await getAppSettings();
        const manualProjectTarget = getManualProjectOpenTarget();
        const manualProjectOpen = manualProjectTarget !== null;
        const unavailableProjectMessage =
          'The last project you opened is no longer available. Remove it from the list or open another folder.';
        const lastProject = recentProjects[0] ?? null;
        const lastProjectInvalid = lastProject
          ? invalidProjects.has(lastProject.path)
          : false;
        const currentProjectValid = currentProject !== null;

        let showWelcome = !settings.auto_load_last_project && !manualProjectOpen;
        let error: string | null = null;

        // Check if we should auto-load the last project
        if (settings.auto_load_last_project && lastProject) {
          showWelcome = !currentProjectValid;
          if (lastProjectInvalid) {
            error = unavailableProjectMessage;
          } else if (currentProject === lastProject.path) {
            showWelcome = false;
          } else {
            try {
              await switchProject(lastProject.path);
              return;
            } catch {
              showWelcome = true;
            }
          }
        }

        if (hasInvalidCurrentProject) {
          error = unavailableProjectMessage;
          showWelcome = true;
        }

        if (manualProjectOpen && currentProjectValid) {
          showWelcome = false;
        }

        if (settings.auto_load_last_project && currentProjectValid) {
          showWelcome = false;
        }

        setState({
          showWelcome,
          loading: false,
          error,
          settings,
        });
      } catch (err) {
        console.error('Failed to initialize welcome screen:', err);
        setState((s) => ({
          ...s,
          loading: false,
          showWelcome: true, // Show welcome on error
          error: err instanceof Error ? err.message : 'Unknown error',
        }));
      }
    };

    initialize();
  }, [
    isTauri,
    projectsLoading,
    recentProjects,
    currentProject,
    hasInvalidCurrentProject,
    invalidProjects,
    invoke,
    switchProject,
  ]);

  // Create a new project
  const createProject = useCallback(
    async (name: string, location: string): Promise<string> => {
      try {
        const projectPath = await invoke<string>('create_project', { name, location });

        await reloadDesktopProject({
          allowStates: ['loaded'],
          expectedProject: projectPath,
        });

        // Reload the page to show the new project
        markManualProjectOpen(projectPath);
        window.location.reload();

        return projectPath;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to create project';
        setState((s) => ({ ...s, error: errorMsg }));
        throw err;
      }
    },
    [invoke]
  );

  // Open a project
  const openProject = useCallback(
    async (path: string) => {
      try {
        await switchProject(path);
        // Page will reload
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to open project';
        setState((s) => ({ ...s, error: errorMsg }));
        throw err;
      }
    },
    [switchProject]
  );

  // Browse and open a project
  const browseAndOpen = useCallback(async (): Promise<string | null> => {
    const path = await browseProject();
    if (path) {
      await openProject(path);
    }
    return path;
  }, [browseProject, openProject]);

  // Browse for a folder (for project location)
  const browseFolder = useCallback(async (): Promise<string | null> => {
    try {
      return await invoke<string | null>('browse_folder');
    } catch (err) {
      console.error('Failed to browse folder:', err);
      return null;
    }
  }, [invoke]);

  // Update app settings
  const updateSettings = useCallback(
    async (patch: Partial<AppSettings>) => {
      const nextSettings = { ...state.settings, ...patch };
      try {
        await persistAppSettings(nextSettings);
        setState((s) => ({ ...s, settings: nextSettings }));
      } catch (err) {
        console.error('Failed to update settings:', err);
        throw err;
      }
    },
    [state.settings]
  );

  // Dismiss welcome screen (for debugging/testing)
  const dismissWelcome = useCallback(() => {
    setState((s) => ({ ...s, showWelcome: false }));
  }, []);

  return {
    // State
    showWelcome: state.showWelcome,
    loading: state.loading || projectsLoading,
    error: state.error,
    settings: state.settings,
    recentProjects,
    invalidProjects,
    isTauri,

    // Actions
    createProject,
    openProject,
    browseAndOpen,
    browseFolder,
    removeProject,
    updateSettings,
    dismissWelcome,
    reloadProjects,
  };
}
