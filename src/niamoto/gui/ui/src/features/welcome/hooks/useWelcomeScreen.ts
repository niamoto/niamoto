import { useState, useEffect, useCallback } from 'react';
import { useProjectSwitcher } from '@/shared/hooks/useProjectSwitcher';

// Tauri types
declare global {
  interface Window {
    __TAURI__?: {
      core: {
        invoke: <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;
      };
    };
  }
}

export interface AppSettings {
  auto_load_last_project: boolean;
}

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
    recentProjects,
    loading: projectsLoading,
    isTauri,
    switchProject,
    browseProject,
    validateProject,
    removeProject,
    reload: reloadProjects,
  } = useProjectSwitcher();

  const [state, setState] = useState<WelcomeScreenState>({
    showWelcome: false,
    loading: true,
    error: null,
    settings: { auto_load_last_project: true },
  });

  // Invoke Tauri command
  const invoke = useCallback(
    async <T,>(cmd: string, args?: Record<string, unknown>): Promise<T> => {
      if (!isTauri) {
        throw new Error('Tauri commands only available in desktop mode');
      }
      return window.__TAURI__!.core.invoke<T>(cmd, args);
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
        const settings = await invoke<AppSettings>('get_app_settings');

        let showWelcome = true;

        // Check if we should auto-load the last project
        if (settings.auto_load_last_project && recentProjects.length > 0) {
          const lastProject = recentProjects[0];
          const isValid = await validateProject(lastProject.path);

          if (isValid) {
            // Project is valid - check if already loaded
            if (currentProject === lastProject.path) {
              // Already loaded, don't show welcome
              showWelcome = false;
            } else {
              // Need to load it - switchProject will reload the page
              try {
                await switchProject(lastProject.path);
                // Page will reload, so we won't reach here
                return;
              } catch {
                // Failed to auto-load, show welcome screen
                showWelcome = true;
              }
            }
          }
          // If invalid, we'll show welcome screen
        }

        // If we have a current project, don't show welcome
        if (currentProject) {
          showWelcome = false;
        }

        setState({
          showWelcome,
          loading: false,
          error: null,
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
    invoke,
    switchProject,
    validateProject,
  ]);

  // Create a new project
  const createProject = useCallback(
    async (name: string, location: string): Promise<string> => {
      try {
        const projectPath = await invoke<string>('create_project', { name, location });

        // Reload project on server
        const response = await fetch('/api/health/reload-project', {
          method: 'POST',
        });

        if (!response.ok) {
          throw new Error('Failed to reload project on server');
        }

        // Reload the page to show the new project
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
    try {
      const path = await browseProject();
      if (path) {
        await openProject(path);
      }
      return path;
    } catch (err) {
      // Error already handled in openProject
      throw err;
    }
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
    async (settings: AppSettings) => {
      try {
        await invoke('set_app_settings', { settings });
        setState((s) => ({ ...s, settings }));
      } catch (err) {
        console.error('Failed to update settings:', err);
        throw err;
      }
    },
    [invoke]
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
