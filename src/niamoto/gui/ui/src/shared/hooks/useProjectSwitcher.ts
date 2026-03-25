import { useState, useEffect, useCallback } from 'react';

// Tauri types (will be available when running in Tauri)
declare global {
  interface Window {
    __TAURI__?: {
      core: {
        invoke: <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;
      };
    };
  }
}

export interface ProjectEntry {
  path: string;
  name: string;
  last_accessed: string;
}

/**
 * Hook to manage project switching in desktop mode
 * Uses Tauri commands to interact with the Rust backend
 */
export function useProjectSwitcher() {
  const [currentProject, setCurrentProject] = useState<string | null>(null);
  const [recentProjects, setRecentProjects] = useState<ProjectEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check if we're in Tauri environment
  const isTauri = typeof window !== 'undefined' && window.__TAURI__ !== undefined;

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

  // Load current project and recent projects
  const loadProjects = useCallback(async () => {
    if (!isTauri) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const [current, recent] = await Promise.all([
        invoke<string | null>('get_current_project'),
        invoke<ProjectEntry[]>('get_recent_projects'),
      ]);

      setCurrentProject(current);
      setRecentProjects(recent);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      console.error('Failed to load projects:', err);
    } finally {
      setLoading(false);
    }
  }, [isTauri, invoke]);

  // Switch to a different project
  const switchProject = useCallback(
    async (projectPath: string) => {
      if (!isTauri) {
        throw new Error('Project switching only available in desktop mode');
      }

      try {
        setLoading(true);
        setError(null);

        // Step 1: Save the new project to desktop config
        await invoke('set_current_project', { path: projectPath });

        // Step 2: Tell the FastAPI server to reload from desktop config
        const response = await fetch('/api/health/reload-project', {
          method: 'POST',
        });

        if (!response.ok) {
          throw new Error('Failed to reload project on server');
        }

        // Step 3: Reload the page to refresh the UI with new project data
        window.location.reload();
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to switch project';
        setError(errorMsg);
        console.error('Failed to switch project:', err);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [isTauri, invoke]
  );

  // Remove a project from recent list
  const removeProject = useCallback(
    async (projectPath: string) => {
      if (!isTauri) {
        throw new Error('Project management only available in desktop mode');
      }

      try {
        await invoke('remove_recent_project', { path: projectPath });
        await loadProjects(); // Refresh the list
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Failed to remove project';
        setError(errorMsg);
        console.error('Failed to remove project:', err);
        throw err;
      }
    },
    [isTauri, invoke, loadProjects]
  );

  // Validate a project path
  const validateProject = useCallback(
    async (projectPath: string): Promise<boolean> => {
      if (!isTauri) {
        return false;
      }

      try {
        return await invoke<boolean>('validate_project', { path: projectPath });
      } catch (err) {
        console.error('Failed to validate project:', err);
        return false;
      }
    },
    [isTauri, invoke]
  );

  // Browse for a project folder using native dialog
  const browseProject = useCallback(async (): Promise<string | null> => {
    if (!isTauri) {
      throw new Error('Project browsing only available in desktop mode');
    }

    try {
      const path = await invoke<string | null>('browse_project_folder');
      return path;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to browse project';
      setError(errorMsg);
      console.error('Failed to browse project:', err);
      throw err;
    }
  }, [isTauri, invoke]);

  // Load projects on mount
  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  return {
    currentProject,
    recentProjects,
    loading,
    error,
    isTauri,
    switchProject,
    removeProject,
    validateProject,
    browseProject,
    reload: loadProjects,
  };
}
